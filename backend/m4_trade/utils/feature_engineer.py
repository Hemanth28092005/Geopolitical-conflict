import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import (
    TradeRoute, HostilityScore, Country, Commodity
)
from backend.core.logger import logger


def get_hostility_features(db, country_a_id, country_b_id, lookback_hours=72) -> dict:
    """
    Get aggregated hostility features for a country pair
    over the last lookback_hours.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    scores = db.query(HostilityScore).filter(
        HostilityScore.country_a_id == country_a_id,
        HostilityScore.country_b_id == country_b_id,
        HostilityScore.time >= since
    ).all()

    if not scores:
        return {
            "hostility_mean":   50.0,
            "hostility_max":    50.0,
            "hostility_std":    0.0,
            "hostility_trend":  0.0,
            "anomaly_count":    0,
            "score_count":      0,
        }

    values = [s.score for s in scores]
    times  = list(range(len(values)))

    # Trend = slope of linear fit
    if len(values) > 1:
        trend = float(np.polyfit(times, values, 1)[0])
    else:
        trend = 0.0

    return {
        "hostility_mean":  round(float(np.mean(values)), 2),
        "hostility_max":   round(float(np.max(values)), 2),
        "hostility_std":   round(float(np.std(values)), 2),
        "hostility_trend": round(trend, 4),
        "anomaly_count":   sum(1 for s in scores if s.is_anomaly),
        "score_count":     len(scores),
    }


def build_route_features(db, route: TradeRoute) -> dict:
    """
    Build full feature vector for a single trade route.
    Used by both XGBoost and LightGBM.
    """
    # Get India's id (anchor)
    india = db.query(Country).filter(Country.iso_code == "IND").first()

    # Determine which country is the partner
    if str(route.from_country_id) == str(india.id):
        partner_id = route.to_country_id
    else:
        partner_id = route.from_country_id

    # Hostility features
    hostility = get_hostility_features(db, india.id, partner_id)

    # Route features
    trade_value = route.annual_value_usd or 0
    is_export   = str(route.from_country_id) == str(india.id)

    # Commodity category risk weights
    commodity_risk = {
        "CRUDE_OIL":      0.9,
        "NATURAL_GAS":    0.85,
        "SEMICONDUCTORS": 0.8,
        "RARE_EARTH":     0.85,
        "LITHIUM":        0.75,
        "STEEL":          0.5,
        "WHEAT":          0.4,
        "CORN":           0.35,
    }
    comm_code   = route.commodity.code if route.commodity else "UNKNOWN"
    comm_risk   = commodity_risk.get(comm_code, 0.5)
    comm_cat    = route.commodity.category if route.commodity else "Unknown"

    return {
        # Hostility features
        "hostility_mean":   hostility["hostility_mean"],
        "hostility_max":    hostility["hostility_max"],
        "hostility_std":    hostility["hostility_std"],
        "hostility_trend":  hostility["hostility_trend"],
        "anomaly_count":    hostility["anomaly_count"],
        # Route features
        "trade_value_bn":   round(trade_value / 1e9, 2),
        "is_critical":      int(route.is_critical or False),
        "is_export":        int(is_export),
        "commodity_risk":   comm_risk,
        # Encoded commodity category
        "cat_energy":       int(comm_cat == "Energy"),
        "cat_technology":   int(comm_cat == "Technology"),
        "cat_metals":       int(comm_cat == "Metals"),
        "cat_agriculture":  int(comm_cat == "Agriculture"),
    }


def build_training_dataset(db) -> pd.DataFrame:
    """
    Build a training dataset from existing routes and hostility scores.
    Uses synthetic labels since we don't have historical closure data.
    Label = 1 if route is high risk (hostility > 65 OR anomaly detected)
    """
    routes = db.query(TradeRoute).all()
    rows   = []

    for route in routes:
        try:
            features = build_route_features(db, route)
            # Synthetic label based on hostility threshold
            label = int(
                features["hostility_mean"] > 65 or
                features["anomaly_count"] > 0 or
                features["hostility_max"] > 80
            )
            features["label"]    = label
            features["route_id"] = str(route.id)
            rows.append(features)
        except Exception as e:
            logger.warning(f"Feature build failed for route {route.id}: {e}")
            continue

    df = pd.DataFrame(rows)
    logger.info(f"Built training dataset: {len(df)} routes, {df['label'].sum()} high-risk")
    return df