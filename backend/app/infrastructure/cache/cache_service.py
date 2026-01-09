# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Advanced Cache Service with decorators and async support.

Provides:
- Decorator-based caching for async functions
- Automatic key generation with prefixes
- TTL configuration per cache entry
- Cache invalidation patterns
- Graceful degradation when Redis is unavailable
"""

import functools
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Callable, TypeVar, ParamSpec
from uuid import UUID

import redis.asyncio as redis

from app.config import settings


logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class CacheKeyBuilder:
    """Utility class for building consistent cache keys."""
    
    @staticmethod
    def build(prefix: str, *args: Any, **kwargs: Any) -> str:
        """
        Build a cache key from prefix and arguments.
        
        Args:
            prefix: Cache key prefix (e.g., 'user', 'role', 'tenant')
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            Consistent cache key string
        """
        key_parts = [prefix]
        
        # Add positional args
        for arg in args:
            if isinstance(arg, UUID):
                key_parts.append(str(arg))
            elif arg is not None:
                key_parts.append(str(arg))
        
        # Add sorted kwargs for consistency
        for k, v in sorted(kwargs.items()):
            if v is not None:
                if isinstance(v, UUID):
                    key_parts.append(f"{k}:{v}")
                else:
                    key_parts.append(f"{k}:{v}")
        
        return ":".join(key_parts)
    
    @staticmethod
    def build_hash(prefix: str, data: Any) -> str:
        """
        Build a cache key using hash for complex data.
        
        Useful for query results with many parameters.
        """
        serialized = json.dumps(data, sort_keys=True, default=str)
        hash_value = hashlib.md5(serialized.encode()).hexdigest()[:12]
        return f"{prefix}:hash:{hash_value}"


class CacheSerializer:
    """JSON serializer with support for common types."""
    
    @staticmethod
    def serialize(value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=CacheSerializer._default_encoder)
    
    @staticmethod
    def deserialize(data: str) -> Any:
        """Deserialize JSON string to value."""
        return json.loads(data)
    
    @staticmethod
    def _default_encoder(obj: Any) -> Any:
        """Handle non-JSON-serializable types."""
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):  # Pydantic models
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class CacheService:
    """
    Advanced async cache service with Redis backend.
    
    Features:
    - Async get/set/delete operations
    - TTL support
    - Key prefixing
    - Graceful degradation
    - Cache statistics
    """
    
    # Default TTL values (in seconds)
    TTL_SHORT = 60  # 1 minute
    TTL_MEDIUM = 300  # 5 minutes
    TTL_LONG = 3600  # 1 hour
    TTL_VERY_LONG = 86400  # 24 hours
    
    def __init__(self, client: redis.Redis | None = None) -> None:
        self._client = client
        self._enabled = settings.CACHE_ENABLED
        self._prefix = settings.CACHE_PREFIX
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
    
    @property
    def is_enabled(self) -> bool:
        """Check if cache is enabled and available."""
        return self._enabled and self._client is not None
    
    def _make_key(self, key: str) -> str:
        """Add prefix to cache key."""
        return f"{self._prefix}:{key}"
    
    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.
        
        Returns None if key doesn't exist or cache is unavailable.
        """
        if not self.is_enabled:
            return None
        
        try:
            full_key = self._make_key(key)
            data = await self._client.get(full_key)  # type: ignore
            
            if data:
                self._stats["hits"] += 1
                return CacheSerializer.deserialize(data)
            
            self._stats["misses"] += 1
            return None
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache get error for '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled:
            return False
        
        try:
            full_key = self._make_key(key)
            data = CacheSerializer.serialize(value)
            
            cache_ttl = ttl or settings.CACHE_DEFAULT_TTL
            await self._client.setex(full_key, cache_ttl, data)  # type: ignore
            return True
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache set error for '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a single key from cache."""
        if not self.is_enabled:
            return False
        
        try:
            full_key = self._make_key(key)
            await self._client.delete(full_key)  # type: ignore
            return True
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache delete error for '{key}': {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Useful for invalidating related cache entries.
        Example: delete_pattern("user:*") deletes all user cache entries.
        
        Returns:
            Number of keys deleted
        """
        if not self.is_enabled:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            keys = []
            
            # Use SCAN to find matching keys (memory-safe)
            async for key in self._client.scan_iter(match=full_pattern):  # type: ignore
                keys.append(key)
            
            if keys:
                await self._client.delete(*keys)  # type: ignore
                logger.debug(f"Deleted {len(keys)} cache keys matching '{pattern}'")
                return len(keys)
            
            return 0
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache delete_pattern error for '{pattern}': {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.is_enabled:
            return False
        
        try:
            full_key = self._make_key(key)
            return bool(await self._client.exists(full_key))  # type: ignore
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache exists error for '{key}': {e}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: int | None = None,
    ) -> Any:
        """
        Get value from cache, or compute and cache it if missing.
        
        This is the recommended pattern for caching expensive operations.
        
        Args:
            key: Cache key
            factory: Async function to compute value if cache miss
            ttl: Time to live in seconds
            
        Returns:
            Cached or computed value
        """
        # Try cache first
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # Compute value
        import asyncio
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        # Cache it
        await self.set(key, value, ttl)
        
        return value
    
    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return self._stats.copy()
    
    async def clear_all(self) -> bool:
        """
        Clear all cache entries with our prefix.
        
        WARNING: Use with caution in production.
        """
        if not self.is_enabled:
            return False
        
        try:
            deleted = await self.delete_pattern("*")
            logger.info(f"Cleared {deleted} cache entries")
            return True
            
        except Exception as e:
            logger.error(f"Cache clear_all error: {e}")
            return False


# Global cache service instance
_cache_service: CacheService | None = None


async def get_cache_service() -> CacheService:
    """
    Get the global cache service instance.
    
    Creates Redis connection on first call.
    """
    global _cache_service
    
    if _cache_service is None:
        client = None
        
        if settings.CACHE_ENABLED:
            try:
                client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                # Test connection
                await client.ping()
                logger.info("Cache service connected to Redis")
                
            except Exception as e:
                logger.warning(f"Redis connection failed, cache disabled: {e}")
                client = None
        
        _cache_service = CacheService(client)
    
    return _cache_service


def cached(
    key_prefix: str,
    ttl: int | None = None,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator for caching async function results.
    
    Usage:
        @cached("user", ttl=300)
        async def get_user(user_id: UUID) -> User:
            ...
            
        @cached("roles", key_builder=lambda tenant_id, **kw: f"tenant:{tenant_id}")
        async def list_roles(tenant_id: UUID, skip: int, limit: int) -> list[Role]:
            ...
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
        key_builder: Optional custom key builder function
        
    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Get cache service
            cache = await get_cache_service()
            
            if not cache.is_enabled:
                return await func(*args, **kwargs)  # type: ignore
            
            # Build cache key
            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            else:
                cache_key = CacheKeyBuilder.build(key_prefix, *args, **kwargs)
            
            # Try cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value  # type: ignore
            
            # Execute function
            result = await func(*args, **kwargs)  # type: ignore
            
            # Cache result
            if result is not None:
                await cache.set(cache_key, result, ttl)
                logger.debug(f"Cache set: {cache_key}")
            
            return result  # type: ignore
        
        return wrapper  # type: ignore
    
    return decorator


def invalidate_cache(pattern: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to invalidate cache after function execution.
    
    Usage:
        @invalidate_cache("user:*")
        async def update_user(user_id: UUID, data: UserUpdate) -> User:
            ...
    
    Args:
        pattern: Cache key pattern to invalidate (supports *)
        
    Returns:
        Decorated function that invalidates cache after execution
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Execute function first
            result = await func(*args, **kwargs)  # type: ignore
            
            # Invalidate cache
            cache = await get_cache_service()
            if cache.is_enabled:
                await cache.delete_pattern(pattern)
                logger.debug(f"Cache invalidated: {pattern}")
            
            return result  # type: ignore
        
        return wrapper  # type: ignore
    
    return decorator


__all__ = [
    "CacheService",
    "CacheKeyBuilder",
    "CacheSerializer",
    "get_cache_service",
    "cached",
    "invalidate_cache",
]
