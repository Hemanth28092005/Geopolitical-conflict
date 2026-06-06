import httpx
import csv
import io
import zipfile
from datetime import datetime, timezone
from backend.m1_ingestion.celery_app import celery_app
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import TradeEvent, Country
from backend.core.logger import logger

GDELT_LASTUPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

# Verified correct column indices from actual GDELT data
COL_ACTOR1_COUNTRYCODE = 7   # 3-letter ISO e.g. "GBR", "USA" (sometimes empty)
COL_ACTOR2_COUNTRYCODE = 17  # fallback if col7 empty
COL_GOLDSTEIN          = 30  # float e.g. -5.0
COL_GEO_FULLNAME       = 36  # e.g. "Hampshire, Hampshire, United Kingdom"
COL_GEO_COUNTRYCODE    = 37  # 2-letter e.g. "UK", "US"
COL_SOURCE_URL         = 60  # full article URL ✅

# 3-letter ISO codes GDELT uses directly in col7
GDELT_ISO_SET = {
    "USA", "GBR", "CHN", "RUS", "DEU", "IND", "SAU", "JPN", "FRA", "BRA",
    "IRQ", "ARE", "KOR", "BGD", "IDN", "EGY", "AUS", "CHL", "VNM"
}

# 2-letter → 3-letter fallback for col37
TWO_LETTER_MAP = {
    "US": "USA", "UK": "GBR", "CN": "CHN",
    "RS": "RUS", "GM": "DEU", "IN": "IND",
    "SA": "SAU", "JA": "JPN", "FR": "FRA",
    "BR": "BRA"
}

# Geo full name keywords → ISO fallback for col36
GEO_NAME_MAP = {
    "united states": "USA", "united kingdom": "GBR",
    "china": "CHN", "russia": "RUS", "germany": "DEU",
    "india": "IND", "saudi arabia": "SAU", "japan": "JPN",
    "france": "FRA", "brazil": "BRA"
}


def resolve_iso(row: list) -> str | None:
    """
    Try to resolve a 3-letter ISO code from the row using 3 fallback strategies:
    1. col7 direct 3-letter ISO
    2. col37 2-letter code mapped to 3-letter
    3. col36 geo full name keyword match
    """
    # Strategy 1: col7 direct ISO
    try:
        iso = row[COL_ACTOR1_COUNTRYCODE].strip().upper()
        if iso in GDELT_ISO_SET:
            return iso
    except IndexError:
        pass

    # Strategy 2: col37 two-letter code
    try:
        two = row[COL_GEO_COUNTRYCODE].strip().upper()
        if two in TWO_LETTER_MAP:
            return TWO_LETTER_MAP[two]
    except IndexError:
        pass

    # Strategy 3: col36 geo full name
    try:
        geo = row[COL_GEO_FULLNAME].lower()
        for keyword, iso in GEO_NAME_MAP.items():
            if keyword in geo:
                return iso
    except IndexError:
        pass

    return None


def get_export_url() -> str | None:
    """Parse lastupdate.txt and return the export CSV zip URL."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(GDELT_LASTUPDATE_URL)
        resp.raise_for_status()
    first_line = resp.text.strip().split("\n")[0]
    parts = first_line.strip().split(" ")
    if len(parts) == 3 and parts[2].endswith(".zip"):
        return parts[2]
    return None


@celery_app.task(name="backend.m1_ingestion.workers.stream_worker.fetch_gdelt_news")
def fetch_gdelt_news():
    """Fetch latest GDELT export chunk and store conflict/tension events."""
    logger.info("Starting GDELT fetch...")

    try:
        export_url = get_export_url()
        if not export_url:
            logger.warning("Could not parse GDELT export URL")
            return {"status": "error", "reason": "no export url"}

        logger.info(f"Fetching: {export_url}")

        with httpx.Client(timeout=60) as client:
            resp = client.get(export_url)
            resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            with z.open(z.namelist()[0]) as f:
                content = f.read().decode("utf-8", errors="ignore")

        reader = csv.reader(io.StringIO(content), delimiter="\t")
        db = SyncSessionLocal()
        events_stored = 0
        skipped_no_country = 0

        try:
            for row in reader:
                if len(row) < 61:
                    continue

                # Only negative Goldstein = conflict/tension
                try:
                    goldstein = float(row[COL_GOLDSTEIN]) if row[COL_GOLDSTEIN] else 0.0
                except ValueError:
                    continue

                if goldstein >= 0:
                    continue

                # Resolve country
                iso = resolve_iso(row)
                if not iso:
                    skipped_no_country += 1
                    continue

                country = db.query(Country).filter(Country.iso_code == iso).first()
                if not country:
                    continue

                # Source URL
                source_url = row[COL_SOURCE_URL][:500] if row[COL_SOURCE_URL] else None

                severity = min(abs(goldstein) / 10.0, 1.0)

                db.add(TradeEvent(
                    time=datetime.now(timezone.utc),
                    country_id=country.id,
                    event_type="GDELT_CONFLICT",
                    description=f"Goldstein={goldstein} | geo={row[COL_GEO_FULLNAME][:100]}",
                    severity=severity,
                    source_url=source_url
                ))
                events_stored += 1

                if events_stored >= 100:
                    break

            db.commit()
            logger.info(
                f"GDELT fetch complete — stored {events_stored} events "
                f"(skipped {skipped_no_country} no-country rows)"
            )
            return {"status": "ok", "events_stored": events_stored, "skipped": skipped_no_country}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"GDELT fetch failed: {e}")
        return {"status": "error", "reason": str(e)}