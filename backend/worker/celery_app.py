"""Celery application configuration for background queue processing."""

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "music_ai_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Lisbon",  # também podes aproveitar e corrigir o timezone
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=False,
    worker_prefetch_multiplier=1,
    worker_pool="solo",  # evita fork + asyncpg conflict
)

# Ensure task modules are imported by Celery workers.
celery_app.autodiscover_tasks(["worker.tasks"])
