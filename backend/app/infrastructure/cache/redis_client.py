# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Redis client singleton for CLI and application use."""

import redis.asyncio as redis

from app.config import settings


# Global Redis client instance
_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance.
    
    Uses singleton pattern to reuse connection.
    
    Returns:
        Redis client instance
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    
    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client
    
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
