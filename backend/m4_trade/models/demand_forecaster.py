import os
import pickle
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from backend.core.logger import logger

MODEL_PATH = "data/processed/demand_forecaster.pkl"
FEATURE_COLS = [
    "hostility_mean", "hostility_max", "hostility_std",
    "hostility_trend", "anomaly_count", "trade_value_bn",
    "is_critical", "is_export", "commodity_risk",
    "cat_energy", "cat_technology", "cat_metals", "cat_agriculture"
]

os.makedirs("data/processed", exist_ok=True)


def build_demand_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create synthetic demand change targets (delta%) based on hostility.
    Formula: higher hostility → more negative demand delta
    """
    df = df.copy()
    noise = np.random.normal(0, 5, len(df))
    # Higher hostility = negative trade delta
    df["demand_delta_pct"] = (
        -((df["hostility_mean"] - 50) / 50) * 30 +  # hostility effect
        df["is_critical"] * -5 +                      # critical routes more volatile
        df["commodity_risk"] * -10 +                  # risky commodities
        noise                                          # random noise
    ).round(2)
    return df


def train(df: pd.DataFrame) -> LGBMRegressor | None:
    """Train LightGBM demand forecaster."""
    if len(df) < 5:
        logger.warning("Not enough data to train demand forecaster")
        return None

    df = build_demand_targets(df)
    X  = df[FEATURE_COLS].fillna(0)
    y  = df["demand_delta_pct"]

    if len(df) >= 10:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y

    model = LGBMRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        verbose=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    r2     = r2_score(y_test, y_pred)
    logger.info(f"Demand Forecaster trained — MAE: {mae:.2f}, R²: {r2:.3f}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Demand forecaster saved to {MODEL_PATH}")

    return model


def load() -> LGBMRegressor | None:
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_demand_delta(features: dict) -> dict:
    """
    Predict % change in trade demand for a route.
    Negative = demand will fall, Positive = demand will rise.
    """
    model = load()
    if model is None:
        # Rule-based fallback
        hostility = features.get("hostility_mean", 50)
        delta = -((hostility - 50) / 50) * 20
        return {
            "demand_delta_pct": round(delta, 2),
            "direction":        "decrease" if delta < 0 else "increase",
            "model":            "rule_based_fallback"
        }

    X     = pd.DataFrame([features])[FEATURE_COLS].fillna(0)
    delta = float(model.predict(X)[0])

    return {
        "demand_delta_pct": round(delta, 2),
        "direction":        "decrease" if delta < 0 else "increase",
        "model":            "lightgbm"
    }