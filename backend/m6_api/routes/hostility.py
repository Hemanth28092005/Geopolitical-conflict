from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import HostilityScore, Country

router = APIRouter()

def get_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/hostility-scores")
def get_hostility_scores(
    country: str = Query(None),
    limit:   int = Query(100),
    db: Session = Depends(get_db)
):
    query = db.query(HostilityScore).order_by(desc(HostilityScore.time))

    if country:
        c = db.query(Country).filter(Country.iso_code == country.upper()).first()
        if c:
            query = query.filter(
                (HostilityScore.country_a_id == c.id) |
                (HostilityScore.country_b_id == c.id)
            )

    scores = query.limit(limit).all()
    return [
        {
            "time":        s.time.isoformat(),
            "country_a":   s.country_a.iso_code if s.country_a else None,
            "country_b":   s.country_b.iso_code if s.country_b else None,
            "score":       s.score,
            "is_anomaly":  s.is_anomaly,
            "source_count": s.source_count,
        }
        for s in scores
    ]

@router.get("/hostility-scores/latest")
def get_latest_hostility(db: Session = Depends(get_db)):
    """Get latest score per country pair — used by frontend map."""
    from sqlalchemy import func
    subq = db.query(
        HostilityScore.country_a_id,
        HostilityScore.country_b_id,
        func.max(HostilityScore.time).label("max_time")
    ).group_by(
        HostilityScore.country_a_id,
        HostilityScore.country_b_id
    ).subquery()

    scores = db.query(HostilityScore).join(
        subq,
        (HostilityScore.country_a_id == subq.c.country_a_id) &
        (HostilityScore.country_b_id == subq.c.country_b_id) &
        (HostilityScore.time == subq.c.max_time)
    ).all()

    return [
        {
            "country_a": s.country_a.iso_code,
            "country_b": s.country_b.iso_code,
            "score":     s.score,
            "is_anomaly": s.is_anomaly,
            "time":      s.time.isoformat(),
        }
        for s in scores
    ]