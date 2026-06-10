import numpy as np
from datetime import datetime, timezone, timedelta
from backend.m2_storage.database import SyncSessionLocal
from backend.m2_storage.models.models import HostilityScore, Country
from backend.core.logger import logger


def detect_anomalies(window_hours: int = 24, threshold_sigma: float = 2.0) -> dict:
    """
    Detect anomalous hostility spikes using a rolling z-score approach.
    Flags scores that are more than `threshold_sigma` standard deviations
    above the rolling mean as anomalies.

    This is a statistical anomaly detector — the LSTM upgrade comes in Phase 6
    when we have enough historical data to train on.
    """
    db = SyncSessionLocal()
    flagged = 0

    try:
        # Look back window_hours to get recent scores
        since = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Get all country pairs that have scores
        pairs = db.query(
            HostilityScore.country_a_id,
            HostilityScore.country_b_id
        ).distinct().all()

        for country_a_id, country_b_id in pairs:
            # Get scores for this pair in the window
            scores = db.query(HostilityScore).filter(
                HostilityScore.country_a_id == country_a_id,
                HostilityScore.country_b_id == country_b_id,
                HostilityScore.time >= since
            ).order_by(HostilityScore.time.asc()).all()

            if len(scores) < 3:
                continue  # not enough data for z-score

            score_values = np.array([s.score for s in scores])
            mean  = np.mean(score_values)
            std   = np.std(score_values)

            if std == 0:
                continue

            # Flag latest score if it's a spike
            latest = scores[-1]
            z_score = (latest.score - mean) / std

            if z_score > threshold_sigma:
                latest.is_anomaly = True
                flagged += 1
                logger.warning(
                    f"Anomaly detected! z={z_score:.2f} "
                    f"score={latest.score} mean={mean:.1f} std={std:.1f}"
                )

        db.commit()
        logger.info(f"Anomaly detection complete — {flagged} spikes flagged")
        return {"flagged": flagged}

    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        db.rollback()
        return {"flagged": 0, "error": str(e)}

    finally:
        db.close()