# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Redis client wrapper — delegates to the centralized cache singleton."""

from __future__ import annotations

import redis.asyncio as redis

from app.infrastructure.cache import get_cache
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


async def get_redis_client() -> redis.Redis:
    """Return the Redis client from the centralized cache singleton."""
    cache = get_cache()
    return cache.get_redis_client()


async def close_redis_client() -> None:
    """Close Redis client connection (no-op — lifecycle managed by cache singleton)."""
    # Connection lifecycle is managed by close_cache() in __init__.py
    pass
