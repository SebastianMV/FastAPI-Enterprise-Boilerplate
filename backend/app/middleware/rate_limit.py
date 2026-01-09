# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Rate limiting middleware using Redis.

Implements sliding window rate limiting with support for
different limits per endpoint, user tier, and API key.
"""

import time
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


class SlidingWindowEntry:
    """
    Represents an entry in the sliding window.
    
    Used for tracking request timestamps.
    """
    
    def __init__(self, timestamp: float, count: int = 1):
        self.timestamp = timestamp
        self.count = count


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter for development.
    
    Uses a sliding window algorithm.
    Not suitable for production with multiple instances.
    """
    
    def __init__(self):
        self._requests: dict[str, list[float]] = {}
    
    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier (IP, user ID, API key)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, remaining, retry_after)
        """
        now = time.time()
        window_start = now - window_seconds
        
        # Get and filter requests in window
        requests = self._requests.get(key, [])
        requests = [ts for ts in requests if ts > window_start]
        
        # Check limit
        if len(requests) >= limit:
            oldest = min(requests)
            retry_after = int(oldest + window_seconds - now) + 1
            return False, 0, retry_after
        
        # Add new request
        requests.append(now)
        self._requests[key] = requests
        
        remaining = limit - len(requests)
        return True, remaining, 0
    
    def cleanup(self, max_age: int = 3600) -> None:
        """Remove old entries to prevent memory growth."""
        now = time.time()
        cutoff = now - max_age
        
        for key in list(self._requests.keys()):
            self._requests[key] = [
                ts for ts in self._requests[key] if ts > cutoff
            ]
            if not self._requests[key]:
                del self._requests[key]


class RedisRateLimiter:
    """
    Redis-based rate limiter for production.
    
    Uses sliding window algorithm with Redis sorted sets.
    Suitable for distributed deployments.
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.
        
        Uses Redis MULTI/EXEC for atomic operations.
        """
        import time
        
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"
        
        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(redis_key, 0, window_start)
        
        # Count current requests
        pipe.zcard(redis_key)
        
        # Add new request (will be removed if over limit)
        pipe.zadd(redis_key, {str(now): now})
        
        # Set expiry
        pipe.expire(redis_key, window_seconds + 1)
        
        results = await pipe.execute()
        current_count = results[1]
        
        if current_count >= limit:
            # Over limit - remove the request we just added
            await self.redis.zrem(redis_key, str(now))
            
            # Get oldest request to calculate retry time
            oldest = await self.redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] + window_seconds - now) + 1
            else:
                retry_after = window_seconds
            
            return False, 0, max(retry_after, 1)
        
        remaining = limit - current_count - 1
        return True, max(remaining, 0), 0


# Global rate limiter instance
_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


# Rate limit configurations by path pattern
RATE_LIMITS = {
    # Auth endpoints - stricter limits
    "/api/v1/auth/login": (5, 60),       # 5 per minute
    "/api/v1/auth/register": (3, 60),    # 3 per minute
    "/api/v1/auth/refresh": (10, 60),    # 10 per minute
    
    # Default for other endpoints
    "default": (100, 60),                 # 100 per minute
    
    # Higher limits for read operations
    "GET:/api/v1/": (200, 60),           # 200 per minute for GET
}


def get_rate_limit_for_path(method: str, path: str) -> tuple[int, int]:
    """
    Get rate limit configuration for a path.
    
    Returns:
        Tuple of (limit, window_seconds)
    """
    # Check exact path match
    if path in RATE_LIMITS:
        return RATE_LIMITS[path]
    
    # Check method + path prefix
    method_path = f"{method}:{path}"
    for pattern, limits in RATE_LIMITS.items():
        if pattern.startswith(method) and path.startswith(pattern.split(":", 1)[-1]):
            return limits
    
    # Default
    return RATE_LIMITS["default"]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    
    Applies rate limits based on:
    1. Client IP address (for unauthenticated requests)
    2. User ID (for authenticated requests)
    3. API Key (for API key authenticated requests)
    """
    
    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/health",
        "/health/live",
        "/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Apply rate limiting to request."""
        
        # Skip if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Skip exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Get rate limit key
        key = self._get_rate_limit_key(request)
        
        # Get limits for this endpoint
        limit, window = get_rate_limit_for_path(
            request.method,
            request.url.path,
        )
        
        # Check rate limit
        limiter = get_rate_limiter()
        is_allowed, remaining, retry_after = limiter.is_allowed(key, limit, window)
        
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded: key={key}, path={request.url.path}",
                extra_fields={"key": key, "path": request.url.path},
            )
            raise RateLimitExceeded(retry_after=retry_after)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)
        
        return response
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Get the rate limit key for a request.
        
        Priority:
        1. API Key prefix (if using API key auth)
        2. User ID (if authenticated)
        3. Client IP address
        """
        # Check for API key
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer krs_"):
            # API key authentication
            key = auth_header[7:15]  # prefix
            return f"apikey:{key}"
        
        # Check for user ID in request state
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, handling proxies."""
        # Check X-Forwarded-For header (from reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"


def rate_limit(
    limit: int = 100,
    window_seconds: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
):
    """
    Decorator for applying custom rate limits to specific endpoints.
    
    Usage:
        @router.get("/expensive-operation")
        @rate_limit(limit=10, window_seconds=60)
        async def expensive_operation():
            ...
    
    Args:
        limit: Maximum requests allowed
        window_seconds: Time window
        key_func: Custom function to generate rate limit key
    """
    def decorator(func: Callable) -> Callable:
        from functools import wraps
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")
            
            if request:
                # Generate key
                if key_func:
                    key = key_func(request)
                else:
                    key = f"endpoint:{func.__name__}"
                
                # Check limit
                limiter = get_rate_limiter()
                is_allowed, remaining, retry_after = limiter.is_allowed(
                    key, limit, window_seconds
                )
                
                if not is_allowed:
                    raise RateLimitExceeded(retry_after=retry_after)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
