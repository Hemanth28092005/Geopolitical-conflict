import json
import redis as redis_client
from backend.m1_ingestion.celery_app import celery_app
from backend.m1_ingestion.utils.text_preprocessor import fetch_article_text, detect_language
from backend.m3_sentiment.models.roberta_scorer import score_text
from backend.m3_sentiment.models.score_aggregator import aggregate_and_store
from backend.m3_sentiment.models.anomaly_detector import detect_anomalies
from backend.core.config import get_settings
from backend.core.logger import logger

settings = get_settings()


def process_pending_articles(batch_size: int = 20) -> dict:
    """
    Main sentiment pipeline:
    1. Pop article URLs from Redis queue
    2. Fetch article text
    3. Score with RoBERTa
    4. Aggregate into country-pair hostility scores
    5. Run anomaly detection
    """
    r = redis_client.from_url(settings.redis_url)
    queue_length = r.llen("pending_articles")
    logger.info(f"Sentiment engine starting — {queue_length} articles in queue")

    if queue_length == 0:
        logger.info("No articles to process")
        return {"processed": 0, "scored": 0, "stored": 0}

    scored_events = []
    processed = 0
    failed = 0

    # Pop up to batch_size articles from queue
    for _ in range(min(batch_size, queue_length)):
        raw = r.lpop("pending_articles")
        if not raw:
            break

        try:
            item = json.loads(raw)
            url        = item.get("url")
            country_id = item.get("country_id")

            if not url or not country_id:
                continue

            # Step 1: Fetch article text
            text = fetch_article_text(url)
            if not text:
                failed += 1
                # Use URL as fallback signal — still score with minimal text
                text = url.replace("-", " ").replace("/", " ")

            # Step 2: Detect language (translate if needed — skipping for now,
            # most GDELT articles are in English)
            lang = detect_language(text)

            # Step 3: Score with RoBERTa
            score_result = score_text(text)

            # Resolve ISO from stored country_id
            from backend.m2_storage.database import SyncSessionLocal
            from backend.m2_storage.models.models import Country
            db = SyncSessionLocal()
            try:
                country = db.query(Country).filter(
                    Country.id == country_id
                ).first()
                iso = country.iso_code if country else None
            finally:
                db.close()

            if iso:
                scored_events.append({
                    "country_iso": iso,
                    "hostility":   score_result["hostility"],
                    "label":       score_result["label"],
                    "confidence":  score_result["confidence"],
                    "source_url":  url,
                    "language":    lang
                })
                processed += 1

        except Exception as e:
            logger.warning(f"Article processing failed: {e}")
            failed += 1
            continue

    logger.info(f"Scored {processed} articles ({failed} failed/paywalled)")

    # Step 4: Aggregate into country-pair scores
    agg_result = aggregate_and_store(scored_events)

    # Step 5: Run anomaly detection
    anomaly_result = detect_anomalies()

    return {
        "processed":   processed,
        "failed":      failed,
        "scored":      len(scored_events),
        "stored":      agg_result.get("stored", 0),
        "anomalies":   anomaly_result.get("flagged", 0)
    }


@celery_app.task(name="backend.m3_sentiment.sentiment_engine.run_sentiment_pipeline")
def run_sentiment_pipeline():
    """Celery task — runs every 15 minutes via beat schedule."""
    return process_pending_articles(batch_size=20)