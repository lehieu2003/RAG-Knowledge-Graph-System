"""
Celery application for async job processing
Production-ready with retries and monitoring
"""
from celery import Celery
from celery.signals import setup_logging

from app.core.config import get_settings
from app.core.logging import setup_logging as setup_app_logging

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "rag_kg_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.infra.queue.tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # 24 hours
)


@setup_logging.connect
def setup_celery_logging(**kwargs):
    """Setup logging for Celery workers"""
    setup_app_logging()
