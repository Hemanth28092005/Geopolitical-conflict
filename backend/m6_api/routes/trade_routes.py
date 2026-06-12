from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import TradeRoute

router = APIRouter()

def get_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/trade-routes")
def get_trade_routes(
    country: str = Query(None, description="Filter by country ISO"),
    db: Session = Depends(get_db)
):
    query = db.query(TradeRoute)
    if country:
        from backend.m2_storage.models.models import Country
        c = db.query(Country).filter(Country.iso_code == country.upper()).first()
        if c:
            query = query.filter(
                (TradeRoute.from_country_id == c.id) |
                (TradeRoute.to_country_id == c.id)
            )

    routes = query.all()
    return [
        {
            "id":               str(r.id),
            "from_country":     r.from_country.iso_code,
            "to_country":       r.to_country.iso_code,
            "commodity":        r.commodity.code if r.commodity else None,
            "commodity_name":   r.commodity.name if r.commodity else None,
            "annual_value_usd": r.annual_value_usd,
            "is_critical":      r.is_critical,
        }
        for r in routes
    ]