import httpx
from datetime import datetime, timezone
from backend.m1_ingestion.celery_app import celery_app
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import Country, Commodity, TradeRoute
from backend.core.logger import logger

COMTRADE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

COUNTRY_UN_CODES = {
    "842": "USA", "156": "CHN", "643": "RUS",
    "276": "DEU", "356": "IND", "682": "SAU",
    "392": "JPN", "826": "GBR", "251": "FRA",
    "076": "BRA"
}

COMMODITY_HS_CODES = {
    "2709": "CRUDE_OIL",
    "2711": "NATURAL_GAS",
    "1001": "WHEAT",
    "8542": "SEMICONDUCTORS",
    "7206": "STEEL",
    "2805": "RARE_EARTH",
    "1005": "CORN",
    "2825": "LITHIUM"
}


def fetch_single_route(reporter_code, reporter_iso, hs_code, commodity_code, db) -> int:
    """Fetch one reporter+commodity combination from Comtrade. Returns routes updated."""
    try:
        params = {
            "reporterCode": reporter_code,
            "period": "2023",
            "cmdCode": hs_code,
            "flowCode": "X",
            "partnerCode": "0",
            "maxRecords": "20",
        }

        with httpx.Client(timeout=30) as client:
            resp = client.get(COMTRADE_URL, params=params)

        if resp.status_code == 429:
            logger.warning(f"Comtrade rate limit hit for {reporter_iso}/{hs_code}")
            return 0

        if resp.status_code != 200:
            logger.warning(f"Comtrade {resp.status_code} for {reporter_iso}/{hs_code}")
            return 0

        data = resp.json()
        records = data.get("data", [])

        if not records:
            logger.debug(f"No Comtrade data for {reporter_iso}/{hs_code}")
            return 0

        routes_updated = 0
        for record in records:
            partner_code = str(record.get("partnerCode", ""))
            partner_iso = COUNTRY_UN_CODES.get(partner_code)
            if not partner_iso or partner_iso == reporter_iso:
                continue

            trade_value = float(record.get("primaryValue", 0) or 0)
            if trade_value <= 0:
                continue

            from_country = db.query(Country).filter(Country.iso_code == reporter_iso).first()
            to_country   = db.query(Country).filter(Country.iso_code == partner_iso).first()
            commodity    = db.query(Commodity).filter(Commodity.code == commodity_code).first()

            if not all([from_country, to_country, commodity]):
                continue

            # Upsert
            route = db.query(TradeRoute).filter(
                TradeRoute.from_country_id == from_country.id,
                TradeRoute.to_country_id   == to_country.id,
                TradeRoute.commodity_id    == commodity.id
            ).first()

            if route:
                route.annual_value_usd = trade_value
                route.is_critical = trade_value > 1e9
            else:
                db.add(TradeRoute(
                    from_country_id=from_country.id,
                    to_country_id=to_country.id,
                    commodity_id=commodity.id,
                    annual_value_usd=trade_value,
                    is_critical=trade_value > 1e9
                ))

            routes_updated += 1

        return routes_updated

    except Exception as e:
        logger.warning(f"fetch_single_route error {reporter_iso}/{hs_code}: {e}")
        return 0


@celery_app.task(name="backend.m1_ingestion.workers.batch_worker.fetch_comtrade_data")
def fetch_comtrade_data():
    """Fetch UN Comtrade bilateral trade data and upsert trade routes."""
    logger.info("Starting Comtrade batch fetch...")
    db = SyncSessionLocal()
    total_updated = 0

    try:
        for reporter_code, reporter_iso in COUNTRY_UN_CODES.items():
            for hs_code, commodity_code in COMMODITY_HS_CODES.items():
                count = fetch_single_route(
                    reporter_code, reporter_iso,
                    hs_code, commodity_code, db
                )
                total_updated += count

        db.commit()
        logger.info(f"Comtrade batch complete — {total_updated} routes updated")
        return {"status": "ok", "routes_updated": total_updated}

    except Exception as e:
        logger.error(f"Comtrade batch failed: {e}")
        db.rollback()
        return {"status": "error", "reason": str(e)}

    finally:
        db.close()