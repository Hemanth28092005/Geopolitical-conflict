from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import ForecastResult

router = APIRouter()

def get_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/forecast-results")
def get_forecasts(
    model:  str = Query(None),
    limit:  int = Query(50),
    db: Session = Depends(get_db)
):
    query = db.query(ForecastResult).order_by(desc(ForecastResult.time))
    if model:
        query = query.filter(ForecastResult.model_name == model)

    results = query.limit(limit).all()
    return [
        {
            "time":           r.time.isoformat(),
            "route":          f"{r.trade_route.from_country.iso_code}→{r.trade_route.to_country.iso_code}",
            "from_country":   r.trade_route.from_country.iso_code,
            "to_country":     r.trade_route.to_country.iso_code,
            "commodity":      r.trade_route.commodity.code if r.trade_route.commodity else None,
            "model_name":     r.model_name,
            "forecast_value": r.forecast_value,
            "lower_bound":    r.lower_bound,
            "upper_bound":    r.upper_bound,
            "horizon_days":   r.horizon_days,
        }
        for r in results
    ]