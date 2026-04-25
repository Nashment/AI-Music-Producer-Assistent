"""Compatibility module for Celery app import path.

Preferred Celery app path: worker.celery_app:celery_app
Legacy path still supported: app.worker:app
"""

from worker.celery_app import celery_app

# Backward-compatible alias used by existing docs/commands.
app = celery_app
