from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import SimulationRun
from backend.m5_simulation.whatif_engine import run_whatif

router = APIRouter()

def get_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


class ShockInput(BaseModel):
    from_country: str
    to_country:   str
    commodity:    str
    closure_pct:  float


class SimulationInput(BaseModel):
    name:   str
    shocks: list[ShockInput]


@router.post("/simulate")
def run_simulation(payload: SimulationInput):
    scenario = {
        "name": payload.name,
        "shocks": [
            {
                "from":        s.from_country,
                "to":          s.to_country,
                "commodity":   s.commodity,
                "closure_pct": s.closure_pct,
            }
            for s in payload.shocks
        ]
    }
    result = run_whatif(scenario, save_to_db=True)
    return result


@router.get("/simulations")
def get_simulations(db: Session = Depends(get_db)):
    runs = db.query(SimulationRun).order_by(
        SimulationRun.created_at.desc()
    ).limit(20).all()
    return [
        {
            "id":                   str(r.id),
            "name":                 r.name,
            "affected_countries":   r.affected_countries,
            "affected_commodities": r.affected_commodities,
            "total_impact_usd":     r.total_impact_usd,
            "created_at":           r.created_at.isoformat(),
            "scenario":             r.scenario,
            "results":              r.results,
        }
        for r in runs
    ]