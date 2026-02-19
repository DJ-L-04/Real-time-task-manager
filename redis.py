# app/db/redis.py
#
# Redis serves TWO purposes in this project:
# 1. Pub/Sub broker — publishing task update events to WebSocket clients
# 2. Celery message broker — queuing background jobs (email notifications)
#
# We use two separate clients:
# - redis_client: for Pub/Sub (synchronous redis-py)
# - async_redis: for async operations inside FastAPI endpoints

import redis
import redis.asyncio as aioredis
from app.core.config import settings

# Synchronous client — used by Celery workers (which are sync)
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Async client — used inside FastAPI async endpoints and WebSocket handlers
async_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis():
    """Dependency for sync redis (used in non-async contexts)."""
    return redis_client


async def get_async_redis():
    """Dependency for async redis (used in FastAPI async endpoints)."""
    return async_redis
