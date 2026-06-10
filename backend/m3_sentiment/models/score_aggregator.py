from collections import defaultdict
from datetime import datetime, timezone
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import HostilityScore, Country
from backend.core.logger import logger


def aggregate_and_store(scored_events: list[dict]) -> dict:
    """
    Aggregate per-article scores into per-country-pair scores
    and store in TimescaleDB hostility_scores hypertable.

    scored_events format:
    [
        {
            "country_iso": "IND",
            "hostility": 72.5,
            "label": "negative",
            "confidence": 0.91,
            "source_url": "https://..."
        },
        ...
    ]
    """
    if not scored_events:
        logger.warning("No scored events to aggregate")
        return {"stored": 0}

    db = SyncSessionLocal()
    stored = 0

    try:
        # Group scores by country
        country_scores = defaultdict(list)
        for event in scored_events:
            iso = event.get("country_iso")
            if iso:
                country_scores[iso].append(event)

        now = datetime.now(timezone.utc)

        # Get India's ID (anchor country for all pairs)
        india = db.query(Country).filter(Country.iso_code == "IND").first()
        if not india:
            logger.error("India not found in DB")
            return {"stored": 0}

        for iso, events in country_scores.items():
            if iso == "IND":
                continue  # skip self-pairs

            partner = db.query(Country).filter(Country.iso_code == iso).first()
            if not partner:
                continue

            # Aggregate: weighted average by confidence
            scores     = [e["hostility"] for e in events]
            confidences = [e["confidence"] for e in events]
            raw_scores = [{"hostility": e["hostility"], "label": e["label"]} for e in events]

            if sum(confidences) > 0:
                weighted_avg = sum(
                    s * c for s, c in zip(scores, confidences)
                ) / sum(confidences)
            else:
                weighted_avg = sum(scores) / len(scores)

            db.add(HostilityScore(
                time=now,
                country_a_id=india.id,
                country_b_id=partner.id,
                score=round(weighted_avg, 2),
                is_anomaly=False,           # LSTM will update this
                source_count=len(events),
                raw_scores=raw_scores
            ))
            stored += 1

        db.commit()
        logger.info(f"Aggregated {stored} country-pair hostility scores")
        return {"stored": stored}

    except Exception as e:
        logger.error(f"Aggregation failed: {e}")
        db.rollback()
        return {"stored": 0, "error": str(e)}

    finally:
        db.close()