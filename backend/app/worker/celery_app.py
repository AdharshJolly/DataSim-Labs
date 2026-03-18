import ssl
from urllib.parse import urlparse

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
    broker_connection_retry_on_startup=True,
)

if urlparse(settings.celery_broker_url).scheme == "rediss":
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

if urlparse(settings.celery_result_backend).scheme == "rediss":
    celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

celery_app.autodiscover_tasks(["app.worker"])
