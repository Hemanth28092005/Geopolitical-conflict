import os
import pickle
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from backend.core.logger import logger

# Save model to disk
MODEL_PATH = "data/processed/route_risk_model.pkl"
FEATURE_COLS = [
    "hostility_mean", "hostility_max", "hostility_std",
    "hostility_trend", "anomaly_count", "trade_value_bn",
    "is_critical", "is_export", "commodity_risk",
    "cat_energy", "cat_technology", "cat_metals", "cat_agriculture"
]

os.makedirs("data/processed", exist_ok=True)


def train(df: pd.DataFrame) -> XGBClassifier:
    """Train XGBoost route risk classifier."""
    if len(df) < 5:
        logger.warning("Not enough data to train — need at least 5 routes")
        return None

    X = df[FEATURE_COLS].fillna(0)
    y = df["label"]

    # If all labels are the same, can't train properly
    if y.nunique() < 2:
        logger.warning("Only one class in labels — using synthetic variation")
        # Add slight variation for demo purposes
        y = y.copy()
        y.iloc[:max(1, len(y)//4)] = 1 - y.iloc[0]

    # Split — use all data if too small for split
    if len(df) >= 10:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y

    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    logger.info(f"Route Risk Model trained:\n{classification_report(y_test, y_pred, zero_division=0)}")

    # Save
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Model saved to {MODEL_PATH}")

    return model


def load() -> XGBClassifier | None:
    """Load saved model from disk."""
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_risk(features: dict) -> dict:
    """
    Predict closure probability for a single route.
    Returns probability 0.0–1.0 and risk label.
    """
    model = load()
    if model is None:
        # Fallback: rule-based risk score
        hostility = features.get("hostility_mean", 50)
        risk = min((hostility - 40) / 60, 1.0) if hostility > 40 else 0.0
        return {
            "p_close":    round(max(risk, 0.0), 3),
            "risk_label": "high" if risk > 0.6 else "medium" if risk > 0.3 else "low",
            "model":      "rule_based_fallback"
        }

    X = pd.DataFrame([features])[FEATURE_COLS].fillna(0)
    prob = float(model.predict_proba(X)[0][1])

    return {
        "p_close":    round(prob, 3),
        "risk_label": "high" if prob > 0.6 else "medium" if prob > 0.3 else "low",
        "model":      "xgboost"
    }