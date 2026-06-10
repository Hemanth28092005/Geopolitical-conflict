from datetime import datetime, timezone
from backend.m1_ingestion.celery_app import celery_app
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import TradeRoute, ForecastResult
from backend.m4_trade.utils.feature_engineer import build_route_features, build_training_dataset
from backend.m4_trade.models.route_risk_model import train as train_risk, predict_risk
from backend.m4_trade.models.demand_forecaster import train as train_demand, predict_demand_delta
from backend.core.logger import logger


def run_trade_intelligence() -> dict:
    """
    Main M4 pipeline:
    1. Build features from DB
    2. Train/load XGBoost + LightGBM
    3. Score all trade routes
    4. Store forecast results
    """
    logger.info("Running trade intelligence pipeline...")
    db = SyncSessionLocal()

    try:
        # Step 1: Build training dataset
        df = build_training_dataset(db)
        if df.empty:
            logger.warning("No training data available")
            return {"status": "no_data"}

        # Step 2: Train models
        risk_model   = train_risk(df)
        demand_model = train_demand(df)

        # Step 3: Score all routes and store forecasts
        routes  = db.query(TradeRoute).all()
        stored  = 0
        results = []

        for route in routes:
            try:
                features = build_route_features(db, route)

                # XGBoost route risk
                risk = predict_risk(features)

                # LightGBM demand delta
                demand = predict_demand_delta(features)

                # Store in forecast_results hypertable
                db.add(ForecastResult(
                    time=datetime.now(timezone.utc),
                    trade_route_id=route.id,
                    model_name="xgboost_route_risk",
                    forecast_value=risk["p_close"],
                    lower_bound=max(0, risk["p_close"] - 0.1),
                    upper_bound=min(1, risk["p_close"] + 0.1),
                    horizon_days=7
                ))

                db.add(ForecastResult(
                    time=datetime.now(timezone.utc),
                    trade_route_id=route.id,
                    model_name="lgbm_demand_delta",
                    forecast_value=demand["demand_delta_pct"],
                    lower_bound=demand["demand_delta_pct"] - 5,
                    upper_bound=demand["demand_delta_pct"] + 5,
                    horizon_days=30
                ))

                results.append({
                    "route":         f"{route.from_country.iso_code}→{route.to_country.iso_code}",
                    "commodity":     route.commodity.code if route.commodity else "?",
                    "p_close":       risk["p_close"],
                    "risk_label":    risk["risk_label"],
                    "demand_delta":  demand["demand_delta_pct"],
                    "direction":     demand["direction"]
                })
                stored += 1

            except Exception as e:
                logger.warning(f"Route scoring failed: {e}")
                continue

        db.commit()

        # Print summary table
        print("\n── Trade Intelligence Results ────────────────────────────────")
        print(f"{'Route':<12} {'Commodity':<15} {'P(close)':<10} {'Risk':<8} {'Demand Δ%':<10} {'Direction'}")
        print("─" * 70)
        for r in sorted(results, key=lambda x: x["p_close"], reverse=True):
            print(
                f"{r['route']:<12} {r['commodity']:<15} "
                f"{r['p_close']:<10.3f} {r['risk_label']:<8} "
                f"{r['demand_delta']:<10.1f} {r['direction']}"
            )
        print("─" * 70)

        logger.info(f"Trade intelligence complete — {stored} routes scored")
        return {"status": "ok", "routes_scored": stored, "results": results}

    except Exception as e:
        logger.error(f"Trade intelligence failed: {e}")
        db.rollback()
        return {"status": "error", "reason": str(e)}

    finally:
        db.close()


@celery_app.task(name="backend.m4_trade.trade_intelligence.run_trade_intelligence_task")
def run_trade_intelligence_task():
    """Celery task — runs daily."""
    return run_trade_intelligence()