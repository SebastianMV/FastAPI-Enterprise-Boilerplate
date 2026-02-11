# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Infrastructure cache package."""

import json
from typing import Any

import redis.asyncio as redis

from app.config import settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

# Global cache instance
_cache_client: redis.Redis | None = None


class RedisCache:
    """
    Simple Redis cache wrapper.

    Provides get/set/delete operations with JSON serialization.

    Note: For advanced caching with decorators, use CacheService from
    app.infrastructure.cache.cache_service instead.
    """

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def get_redis_client(self) -> redis.Redis:
        """Return the underlying Redis client for advanced operations.

        Use this instead of accessing ``_client`` directly.
        """
        return self._client

    async def get(self, key: str) -> Any:
        """Get value from cache."""
        try:
            data = await self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("Cache get error: %s", e)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache with optional TTL."""
        try:
            data = json.dumps(value)
            if ttl:
                await self._client.setex(key, ttl, data)
            else:
                await self._client.set(key, data)
            return True
        except Exception as e:
            logger.warning("Cache set error: %s", e)
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete error: %s", e)
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(await self._client.exists(key))
        except Exception as e:
            logger.warning("Cache exists error: %s", e)
            return False


def get_cache() -> RedisCache:
    """
    Get Redis cache instance.

    Uses singleton pattern to reuse connection.
    """
    global _cache_client

    if _cache_client is None:
        _cache_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

    return RedisCache(_cache_client)


async def close_cache() -> None:
    """Close Redis cache connection gracefully."""
    global _cache_client
    if _cache_client is not None:
        try:
            await _cache_client.aclose()
            logger.info("Redis cache connection closed")
        except Exception as e:
            logger.warning("Error closing Redis cache: %s", e)
        finally:
            _cache_client = None


# Re-export advanced cache service
from app.infrastructure.cache.cache_service import (
    CacheKeyBuilder,
    CacheService,
    cached,
    get_cache_service,
    invalidate_cache,
)

__all__ = [
    "RedisCache",
    "get_cache",
    "close_cache",
    "CacheService",
    "CacheKeyBuilder",
    "get_cache_service",
    "cached",
    "invalidate_cache",
]
