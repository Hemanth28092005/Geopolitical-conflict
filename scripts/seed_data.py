import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import Country, Commodity
from backend.core.logger import logger

COUNTRIES = [
    {"iso_code": "USA", "name": "United States",   "region": "North America", "gdp_usd": 25.46e12},
    {"iso_code": "CHN", "name": "China",            "region": "Asia",          "gdp_usd": 17.96e12},
    {"iso_code": "RUS", "name": "Russia",           "region": "Europe/Asia",   "gdp_usd": 2.24e12},
    {"iso_code": "DEU", "name": "Germany",          "region": "Europe",        "gdp_usd": 4.07e12},
    {"iso_code": "IND", "name": "India",            "region": "Asia",          "gdp_usd": 3.39e12},
    {"iso_code": "SAU", "name": "Saudi Arabia",     "region": "Middle East",   "gdp_usd": 1.06e12},
    {"iso_code": "JPN", "name": "Japan",            "region": "Asia",          "gdp_usd": 4.23e12},
    {"iso_code": "GBR", "name": "United Kingdom",   "region": "Europe",        "gdp_usd": 3.07e12},
    {"iso_code": "FRA", "name": "France",           "region": "Europe",        "gdp_usd": 2.78e12},
    {"iso_code": "BRA", "name": "Brazil",           "region": "South America", "gdp_usd": 1.92e12},
]

COMMODITIES = [
    {"code": "CRUDE_OIL",      "name": "Crude Oil",          "category": "Energy",        "unit": "barrels"},
    {"code": "NATURAL_GAS",    "name": "Natural Gas",        "category": "Energy",        "unit": "mmBtu"},
    {"code": "WHEAT",          "name": "Wheat",              "category": "Agriculture",   "unit": "tonnes"},
    {"code": "SEMICONDUCTORS", "name": "Semiconductors",     "category": "Technology",    "unit": "units"},
    {"code": "STEEL",          "name": "Steel",              "category": "Metals",        "unit": "tonnes"},
    {"code": "RARE_EARTH",     "name": "Rare Earth Metals",  "category": "Metals",        "unit": "tonnes"},
    {"code": "CORN",           "name": "Corn",               "category": "Agriculture",   "unit": "tonnes"},
    {"code": "LITHIUM",        "name": "Lithium",            "category": "Metals",        "unit": "tonnes"},
]

def seed():
    db = SyncSessionLocal()
    try:
        # Seed countries
        existing = db.query(Country).count()
        if existing == 0:
            for c in COUNTRIES:
                db.add(Country(**c))
            db.commit()
            logger.info(f"Seeded {len(COUNTRIES)} countries")
        else:
            logger.info("Countries already seeded, skipping")

        # Seed commodities
        existing = db.query(Commodity).count()
        if existing == 0:
            for c in COMMODITIES:
                db.add(Commodity(**c))
            db.commit()
            logger.info(f"Seeded {len(COMMODITIES)} commodities")
        else:
            logger.info("Commodities already seeded, skipping")

        logger.info("Seed complete.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()