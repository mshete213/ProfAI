from celery import Celery
from celery.schedules import crontab

from config import get_settings

settings = get_settings()

celery_app = Celery(
    "edtech",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["core.tasks"],
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

# Beat schedule — Canvas re-sync every 6 hours (polling-mode courses)
celery_app.conf.beat_schedule = {
    "canvas-resync-every-6h": {
        "task": "core.tasks.sync_all_canvas_courses",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}
