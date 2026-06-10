from celery import Celery
from celery.schedules import crontab
from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "geoint",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "backend.m1_ingestion.workers.stream_worker",
        "backend.m1_ingestion.workers.batch_worker",
        "backend.m1_ingestion.workers.graph_builder",
        "backend.m3_sentiment.sentiment_engine",
        "backend.m4_trade.trade_intelligence",        # ← add this
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "gdelt-stream-every-15-min": {
        "task": "backend.m1_ingestion.workers.stream_worker.fetch_gdelt_news",
        "schedule": crontab(minute="*/15"),
    },
    "sentiment-pipeline-every-15-min": {       # ← add this
        "task": "backend.m3_sentiment.sentiment_engine.run_sentiment_pipeline",
        "schedule": crontab(minute="*/15"),
    },
    "comtrade-batch-daily": {
        "task": "backend.m1_ingestion.workers.batch_worker.fetch_comtrade_data",
        "schedule": crontab(hour=2, minute=0),
    },
    "trade-intelligence-daily": {               # ← add this
        "task": "backend.m4_trade.trade_intelligence.run_trade_intelligence_task",
        "schedule": crontab(hour=3, minute=0),
    },
    "graph-rebuild-hourly": {
        "task": "backend.m1_ingestion.workers.graph_builder.build_trade_graph",
        "schedule": crontab(minute=0),
    },
}