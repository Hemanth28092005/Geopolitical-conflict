import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.m2_storage.database import engine, Base
from backend.m2_storage.models.models import (
    Country, Commodity, TradeRoute, Alliance,
    HostilityScore, TradeEvent, ForecastResult, SimulationRun
)
from backend.core.logger import logger

def init_db():
    logger.info("Creating all tables...")
    
    # Create all standard tables
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully")

    # Convert time-series tables to TimescaleDB hypertables
    with engine.connect() as conn:
        hypertables = [
            ("hostility_scores", "time"),
            ("trade_events", "time"),
            ("forecast_results", "time"),
        ]
        for table, time_col in hypertables:
            try:
                conn.execute(text(
                    f"SELECT create_hypertable('{table}', '{time_col}', if_not_exists => TRUE);"
                ))
                conn.commit()
                logger.info(f"Hypertable created: {table}")
            except Exception as e:
                logger.warning(f"Hypertable {table} skipped: {e}")

    logger.info("Database initialised. Phase 2 complete.")

if __name__ == "__main__":
    init_db()