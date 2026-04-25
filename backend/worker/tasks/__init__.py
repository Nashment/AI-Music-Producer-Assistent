"""Celery task modules."""

from .generation_tasks import process_generation_task

__all__ = ["process_generation_task"]
