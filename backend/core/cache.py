"""Async Redis cache helpers with graceful degradation for backend services."""

import logging
from typing import Any

import orjson
import redis.asyncio as redis

from backend.core.config import settings

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Return a shared Redis client, initializing it lazily on first use."""
    global _redis

    if _redis is not None:
        return _redis

    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=False)
        await client.ping()
        _redis = client
        return _redis
    except Exception as exc:
        logger.warning("Redis unavailable; continuing without cache: %s", exc)
        _redis = None
        return None


async def cache_get(key: str) -> Any | None:
    """Get and deserialize a cached JSON value by key."""
    client = await get_redis()
    if client is None:
        return None

    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return orjson.loads(raw)
    except Exception as exc:
        logger.warning("Cache get failed for key '%s': %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    """Serialize and store a value in Redis with an optional TTL."""
    client = await get_redis()
    if client is None:
        return

    ttl_seconds = settings.REDIS_CACHE_TTL if ttl is None else ttl

    try:
        payload = orjson.dumps(value)
        await client.set(key, payload, ex=ttl_seconds)
    except Exception as exc:
        logger.warning("Cache set failed for key '%s': %s", key, exc)


async def cache_delete(key: str) -> None:
    """Delete a cached key if Redis is available."""
    client = await get_redis()
    if client is None:
        return

    try:
        await client.delete(key)
    except Exception as exc:
        logger.warning("Cache delete failed for key '%s': %s", key, exc)


async def close_redis() -> None:
    """Close the shared Redis connection and clear the module cache."""
    global _redis

    if _redis is None:
        return

    try:
        await _redis.aclose()
    except Exception as exc:
        logger.warning("Failed to close Redis connection cleanly: %s", exc)
    finally:
        _redis = None
