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

# Scheduled tasks
celery_app.conf.beat_schedule = {
    # GDELT stream every 15 minutes
    "gdelt-stream-every-15-min": {
        "task": "backend.m1_ingestion.workers.stream_worker.fetch_gdelt_news",
        "schedule": crontab(minute="*/15"),
    },
    # Comtrade batch once a day
    "comtrade-batch-daily": {
        "task": "backend.m1_ingestion.workers.batch_worker.fetch_comtrade_data",
        "schedule": crontab(hour=2, minute=0),
    },
    # Graph rebuild every hour
    "graph-rebuild-hourly": {
        "task": "backend.m1_ingestion.workers.graph_builder.build_trade_graph",
        "schedule": crontab(minute=0),
    },
}