# app/worker/celery_app.py
#
# Celery is a distributed task queue.
# Instead of blocking an API request to send an email (which could take seconds),
# we hand the job to Celery and return the response immediately.
#
# Celery needs:
# 1. A broker (Redis) — where tasks are queued
# 2. A backend (Redis) — where results are stored (optional but useful)
#
# To run the worker: celery -A app.worker.celery_app.celery_app worker --loglevel=info

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "taskmanager",
    broker=settings.REDIS_URL,       # Redis as the message broker
    backend=settings.REDIS_URL,       # Redis also stores task results
    include=["app.worker.tasks"]      # where to find task definitions
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry failed tasks up to 3 times with exponential backoff
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
