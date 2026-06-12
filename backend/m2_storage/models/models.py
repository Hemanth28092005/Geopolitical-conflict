from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from backend.m2_storage.database import Base


class Country(Base):
    __tablename__ = "countries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    iso_code = Column(String(3), unique=True, nullable=False)   # e.g. "USA"
    name = Column(String(100), nullable=False)                  # e.g. "United States"
    region = Column(String(50))                                 # e.g. "North America"
    gdp_usd = Column(Float)
    population = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    trade_routes_from = relationship("TradeRoute", foreign_keys="TradeRoute.from_country_id", back_populates="from_country")
    trade_routes_to = relationship("TradeRoute", foreign_keys="TradeRoute.to_country_id", back_populates="to_country")


class Commodity(Base):
    __tablename__ = "commodities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False)      # e.g. "CRUDE_OIL"
    name = Column(String(100), nullable=False)                  # e.g. "Crude Oil"
    category = Column(String(50))                               # e.g. "Energy"
    unit = Column(String(20))                                   # e.g. "barrels"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TradeRoute(Base):
    __tablename__ = "trade_routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_country_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    to_country_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey("commodities.id"))
    annual_value_usd = Column(Float)                            # trade value in USD
    volume_tonnes = Column(Float)
    is_critical = Column(Boolean, default=False)                # flagged as strategically critical
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    from_country = relationship("Country", foreign_keys=[from_country_id], back_populates="trade_routes_from")
    to_country = relationship("Country", foreign_keys=[to_country_id], back_populates="trade_routes_to")
    commodity = relationship("Commodity")


class Alliance(Base):
    __tablename__ = "alliances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_a_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    country_b_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    alliance_type = Column(String(50))                          # e.g. "NATO", "BRICS", "bilateral"
    strength = Column(Float)                                    # 0.0 to 1.0
    formed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── TIME-SERIES TABLES (will become TimescaleDB hypertables) ──────────────────

class HostilityScore(Base):
    __tablename__ = "hostility_scores"

    time         = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_a_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    country_b_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    score        = Column(Float, nullable=False)
    is_anomaly   = Column(Boolean, default=False)
    source_count = Column(Integer)
    raw_scores   = Column(JSON)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    country_a = relationship("Country", foreign_keys=[country_a_id])
    country_b = relationship("Country", foreign_keys=[country_b_id])


class TradeEvent(Base):
    __tablename__ = "trade_events"

    time       = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_id = Column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=False)
    event_type = Column(String(50))
    description = Column(Text)
    severity   = Column(Float)
    source_url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    country = relationship("Country", foreign_keys=[country_id])


class ForecastResult(Base):
    __tablename__ = "forecast_results"

    time           = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_route_id = Column(UUID(as_uuid=True), ForeignKey("trade_routes.id"), nullable=False)
    model_name     = Column(String(50))
    forecast_value = Column(Float)
    lower_bound    = Column(Float)
    upper_bound    = Column(Float)
    horizon_days   = Column(Integer)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    trade_route = relationship("TradeRoute", foreign_keys=[trade_route_id])

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100))
    scenario = Column(JSON)                                     # what-if parameters
    results = Column(JSON)                                      # cascade output
    affected_countries = Column(Integer)
    affected_commodities = Column(Integer)
    total_impact_usd = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())