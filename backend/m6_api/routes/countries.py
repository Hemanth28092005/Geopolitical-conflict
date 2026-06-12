from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import Country

router = APIRouter()

def get_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/countries")
def get_countries(db: Session = Depends(get_db)):
    countries = db.query(Country).filter(Country.is_active == True).all()
    return [
        {
            "iso_code": c.iso_code,
            "name":     c.name,
            "region":   c.region,
            "gdp_usd":  c.gdp_usd,
        }
        for c in countries
    ]