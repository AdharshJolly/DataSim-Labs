from celery import Celery  # pyright: ignore[reportMissingImports]

from app.core.config import settings


celery_app = Celery(
    "datasim_lab",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_time_limit=60 * 60,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.worker"])
