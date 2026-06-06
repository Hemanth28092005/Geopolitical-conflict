import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import Country, Commodity, TradeRoute
from backend.core.logger import logger

# ── INDIA-CENTRIC TRADE ROUTES ─────────────────────────────────────────────
# Source: UN Comtrade 2023 approximate figures
# Format: (from_iso, to_iso, commodity, annual_usd, is_critical)
# EXPORT = India → partner
# IMPORT = partner → India

INDIA_TRADE_ROUTES = [

    # ── CRUDE OIL IMPORTS (India is world's 3rd largest oil importer) ──────
    ("SAU", "IND", "CRUDE_OIL",    40e9,  True),   # Saudi is top supplier
    ("RUS", "IND", "CRUDE_OIL",    46e9,  True),   # Russia became #1 after 2022
    ("USA", "IND", "CRUDE_OIL",    12e9,  True),
    ("IRQ", "IND", "CRUDE_OIL",    22e9,  True),   # Iraq
    ("ARE", "IND", "CRUDE_OIL",    10e9,  False),  # UAE

    # ── NATURAL GAS IMPORTS ─────────────────────────────────────────────────
    ("SAU", "IND", "NATURAL_GAS",   8e9,  False),
    ("USA", "IND", "NATURAL_GAS",   6e9,  False),  # LNG imports growing

    # ── SEMICONDUCTOR / ELECTRONICS IMPORTS ────────────────────────────────
    ("CHN", "IND", "SEMICONDUCTORS", 25e9, True),  # India heavily dependent on China
    ("JPN", "IND", "SEMICONDUCTORS", 10e9, True),
    ("USA", "IND", "SEMICONDUCTORS",  8e9, True),
    ("KOR", "IND", "SEMICONDUCTORS", 12e9, True),  # South Korea

    # ── STEEL ───────────────────────────────────────────────────────────────
    ("CHN", "IND", "STEEL",          6e9,  False), # China dumps cheap steel
    ("IND", "USA", "STEEL",          3e9,  False), # India exports steel too
    ("IND", "DEU", "STEEL",          2e9,  False),

    # ── WHEAT ───────────────────────────────────────────────────────────────
    ("IND", "BGD", "WHEAT",          2e9,  False), # Bangladesh
    ("IND", "IDN", "WHEAT",          1e9,  False), # Indonesia
    ("IND", "EGY", "WHEAT",          1e9,  False), # Egypt
    ("USA", "IND", "WHEAT",          1e9,  False), # some imports

    # ── RARE EARTH / CRITICAL MINERALS ─────────────────────────────────────
    ("CHN", "IND", "RARE_EARTH",    15e9,  True),  # India very dependent on China
    ("AUS", "IND", "RARE_EARTH",     4e9,  False), # Australia alternative

    # ── LITHIUM (EV battery push) ───────────────────────────────────────────
    ("AUS", "IND", "LITHIUM",        3e9,  True),
    ("CHL", "IND", "LITHIUM",        2e9,  True),  # Chile

    # ── CORN ────────────────────────────────────────────────────────────────
    ("IND", "BGD", "CORN",           1e9,  False),
    ("IND", "VNM", "CORN",           1e9,  False), # Vietnam
    ("USA", "IND", "CORN",           2e9,  False),

    # ── INDIA EXPORTS (non-agricultural) ───────────────────────────────────
    ("IND", "USA", "SEMICONDUCTORS", 5e9,  False), # IT hardware growing
    ("IND", "GBR", "STEEL",          2e9,  False),
    ("IND", "JPN", "STEEL",          2e9,  False),
    ("IND", "CHN", "RARE_EARTH",     1e9,  False), # some mineral exports
]

# Additional countries we need in DB that aren't in the original seed
ADDITIONAL_COUNTRIES = [
    {"iso_code": "IRQ", "name": "Iraq",         "region": "Middle East",   "gdp_usd": 0.25e12},
    {"iso_code": "ARE", "name": "UAE",           "region": "Middle East",   "gdp_usd": 0.50e12},
    {"iso_code": "KOR", "name": "South Korea",  "region": "Asia",          "gdp_usd": 1.67e12},
    {"iso_code": "BGD", "name": "Bangladesh",   "region": "Asia",          "gdp_usd": 0.46e12},
    {"iso_code": "IDN", "name": "Indonesia",    "region": "Asia",          "gdp_usd": 1.32e12},
    {"iso_code": "EGY", "name": "Egypt",        "region": "Africa",        "gdp_usd": 0.39e12},
    {"iso_code": "AUS", "name": "Australia",    "region": "Oceania",       "gdp_usd": 1.69e12},
    {"iso_code": "CHL", "name": "Chile",        "region": "South America", "gdp_usd": 0.30e12},
    {"iso_code": "VNM", "name": "Vietnam",      "region": "Asia",          "gdp_usd": 0.41e12},
]


def seed_routes():
    db = SyncSessionLocal()
    try:
        # 1. Add additional countries not in original seed
        added_countries = 0
        for c in ADDITIONAL_COUNTRIES:
            exists = db.query(Country).filter(Country.iso_code == c["iso_code"]).first()
            if not exists:
                db.add(Country(**c))
                added_countries += 1
        db.commit()
        logger.info(f"Added {added_countries} new countries")

        # 2. Seed trade routes (skip if already exists)
        existing = db.query(TradeRoute).count()
        if existing > 0:
            logger.info(f"Trade routes already seeded ({existing} exist) — dropping and reseeding")
            db.query(TradeRoute).delete()
            db.commit()

        added = 0
        skipped = 0
        for from_iso, to_iso, commodity_code, value, critical in INDIA_TRADE_ROUTES:
            from_c = db.query(Country).filter(Country.iso_code == from_iso).first()
            to_c   = db.query(Country).filter(Country.iso_code == to_iso).first()
            comm   = db.query(Commodity).filter(Commodity.code == commodity_code).first()

            if not all([from_c, to_c, comm]):
                logger.warning(f"Skipping {from_iso}→{to_iso} {commodity_code} — not found in DB")
                skipped += 1
                continue

            db.add(TradeRoute(
                from_country_id=from_c.id,
                to_country_id=to_c.id,
                commodity_id=comm.id,
                annual_value_usd=value,
                is_critical=critical
            ))
            added += 1

        db.commit()
        logger.info(f"Seeded {added} India-centric trade routes ({skipped} skipped)")

        # 3. Print summary
        print("\n── India Trade Summary ───────────────────────────────")
        imports = [(f,t,c,v) for f,t,c,v,_ in INDIA_TRADE_ROUTES if t == "IND"]
        exports = [(f,t,c,v) for f,t,c,v,_ in INDIA_TRADE_ROUTES if f == "IND"]
        print(f"  Imports into India : {len(imports)} routes")
        print(f"  Exports from India : {len(exports)} routes")
        print(f"  Total partners     : {len(set([f for f,t,c,v,_ in INDIA_TRADE_ROUTES] + [t for f,t,c,v,_ in INDIA_TRADE_ROUTES]) - {'IND'})} countries")
        print(f"  Total routes       : {added}")
        print("─────────────────────────────────────────────────────\n")

    finally:
        db.close()


if __name__ == "__main__":
    seed_routes()