# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Rate limiting middleware using Redis.

Implements sliding window rate limiting with support for
different limits per endpoint, user tier, and API key.
"""

import ipaddress
import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, status
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

# In-memory rate limiter housekeeping constants
_CLEANUP_INTERVAL_SECONDS = 300  # run cleanup every 5 minutes
_CLEANUP_MAX_AGE_SECONDS = 3600  # discard entries older than 1 hour

# Trusted proxy networks — module-level constant to avoid re-creation per request
_TRUSTED_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),  # localhost
    ipaddress.ip_network("::1/128"),  # localhost IPv6
    ipaddress.ip_network("10.0.0.0/8"),  # Docker default
    ipaddress.ip_network("172.16.0.0/12"),  # Docker bridge
    ipaddress.ip_network("192.168.0.0/16"),  # Docker host
)


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
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

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}
        self._last_cleanup: float = time.time()
        self._cleanup_interval: int = _CLEANUP_INTERVAL_SECONDS

    async def is_allowed(
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

        # Periodic cleanup to prevent unbounded memory growth
        if now - self._last_cleanup > self._cleanup_interval:
            self.cleanup()
            self._last_cleanup = now

        # Get and filter requests in window
        requests = self._requests.get(key, [])
        requests = [ts for ts in requests if ts > window_start]

        # Check limit
        # NOTE: No await between check and append — safe in cpython's
        # single-threaded asyncio event loop (no preemption possible).
        if len(requests) >= limit:
            oldest = min(requests)
            retry_after = int(oldest + window_seconds - now) + 1
            return False, 0, retry_after

        # Add new request
        requests.append(now)
        self._requests[key] = requests

        remaining = limit - len(requests)
        return True, remaining, 0

    def cleanup(self, max_age: int = _CLEANUP_MAX_AGE_SECONDS) -> None:
        """Remove old entries to prevent memory growth."""
        now = time.time()
        cutoff = now - max_age

        for key in list(self._requests.keys()):
            self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]
            if not self._requests[key]:
                del self._requests[key]


class RedisRateLimiter:
    """
    Redis-based rate limiter for production.

    Uses sliding window algorithm with Redis sorted sets.
    Suitable for distributed deployments.
    """

    def __init__(self, redis_client: Any) -> None:
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
_rate_limiter: InMemoryRateLimiter | RedisRateLimiter | None = None
_rate_limiter_fallback_time: float | None = None
_RATE_LIMITER_RETRY_INTERVAL = 60  # seconds


def get_rate_limiter() -> InMemoryRateLimiter | RedisRateLimiter:
    """Get the rate limiter instance.

    Uses Redis in production/staging for distributed rate limiting.
    Falls back to in-memory for development or if Redis is unavailable.
    Periodically retries Redis if currently using in-memory fallback.
    """
    global _rate_limiter, _rate_limiter_fallback_time

    if _rate_limiter is not None:
        # If using in-memory fallback, retry Redis periodically
        if _rate_limiter_fallback_time is not None:
            import time

            if (
                time.monotonic() - _rate_limiter_fallback_time
                > _RATE_LIMITER_RETRY_INTERVAL
            ):
                _rate_limiter = None
                _rate_limiter_fallback_time = None
            else:
                return _rate_limiter
        else:
            return _rate_limiter

    from app.config import settings

    if settings.ENVIRONMENT in ("production", "staging"):
        try:
            from app.infrastructure.cache import get_cache

            cache = get_cache()
            _rate_limiter = RedisRateLimiter(cache.get_redis_client())
            _rate_limiter_fallback_time = None
        except Exception:
            import time

            logger.warning(
                "redis_rate_limit_fallback",
                exc_info=True,
            )
            _rate_limiter = InMemoryRateLimiter()
            _rate_limiter_fallback_time = time.monotonic()
    else:
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


# Rate limit configurations by path pattern
RATE_LIMITS = {
    # Auth endpoints - stricter limits
    "/api/v1/auth/login": (5, 60),  # 5 per minute
    "/api/v1/auth/register": (3, 60),  # 3 per minute
    "/api/v1/auth/refresh": (10, 60),  # 10 per minute
    "/api/v1/auth/forgot-password": (3, 60),  # 3 per minute
    "/api/v1/auth/reset-password": (5, 60),  # 5 per minute
    # Default for other endpoints
    "default": (100, 60),  # 100 per minute
    # Higher limits for read operations
    "GET:/api/v1/": (200, 60),  # 200 per minute for GET
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
    for pattern, limits in RATE_LIMITS.items():
        if pattern.startswith(method) and path.startswith(pattern.split(":", 1)[-1]):
            return limits

    # Default
    return RATE_LIMITS["default"]


class RateLimitMiddleware:
    """
    Pure ASGI Rate limiting middleware.

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

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface - apply rate limiting to HTTP requests."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip if disabled
        if not settings.RATE_LIMIT_ENABLED:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")

        # Skip exempt paths
        if path in self.EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        # Get rate limit key
        key = self._get_rate_limit_key(scope)

        # Get limits for this endpoint
        limit, window = get_rate_limit_for_path(method, path)

        # Check rate limit
        limiter = get_rate_limiter()
        is_allowed, remaining, retry_after = await limiter.is_allowed(
            key, limit, window
        )

        if not is_allowed:
            logger.warning(
                "rate_limit_exceeded",
                key=key,
                path=path,
            )
            # Send 429 response
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return

        # Add rate limit headers to response
        async def send_with_rate_limit_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-ratelimit-limit", str(limit).encode()),
                        (b"x-ratelimit-remaining", str(remaining).encode()),
                        (b"x-ratelimit-reset", str(int(time.time()) + window).encode()),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_rate_limit_headers)

    def _get_rate_limit_key(self, scope: Scope) -> str:
        """
        Get the rate limit key for a request.

        Priority:
        1. API Key prefix (if using API key auth)
        2. User ID (if authenticated)
        3. Client IP address
        """
        headers = dict(scope.get("headers", []))

        # Check for API key
        auth_header = headers.get(b"authorization", b"").decode()
        if auth_header.startswith("Bearer krs_"):
            # Use a longer prefix (16 chars) to avoid bucket collisions
            # between different API keys that share a short prefix.
            key = auth_header[7:23]  # 16-char prefix after "Bearer "
            return f"apikey:{key}"

        # Fall back to IP address
        client_ip = self._get_client_ip(scope, headers)
        return f"ip:{client_ip}"

    def _get_client_ip(self, scope: Scope, headers: dict[bytes, bytes]) -> str:
        """Get client IP address, handling proxies."""
        # Direct client IP
        client = scope.get("client")
        direct_ip = client[0] if client else "unknown"

        # Only trust proxy headers if the direct connection is from a trusted proxy
        if self._is_trusted_proxy(direct_ip):
            # Check X-Forwarded-For header (from reverse proxy)
            forwarded = headers.get(b"x-forwarded-for", b"").decode()
            if forwarded:
                # Take first IP in chain (original client)
                return forwarded.split(",")[0].strip()

            # Check X-Real-IP header
            real_ip = headers.get(b"x-real-ip", b"").decode()
            if real_ip:
                return real_ip

        return direct_ip

    @staticmethod
    def _is_trusted_proxy(ip: str) -> bool:
        """Check if IP belongs to a trusted proxy (Docker networks, localhost)."""
        try:
            addr = ipaddress.ip_address(ip)
            return any(addr in net for net in _TRUSTED_NETWORKS)
        except ValueError:
            return False


def rate_limit(
    limit: int = 100,
    window_seconds: int = 60,
    key_func: Callable[[Request], str] | None = None,
) -> Callable[..., Any]:
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

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        from functools import wraps

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if request:
                # Generate key — include per-user/IP context to avoid
                # one user exhausting the limit for all users (B9).
                if key_func:
                    key = key_func(request)
                else:
                    # Build a per-client key from user or IP
                    client_id = "anon"
                    # Try to get user_id from request state (set by auth middleware)
                    if hasattr(request.state, "user_id") and request.state.user_id:
                        client_id = f"user:{request.state.user_id}"
                    elif request.client:
                        client_id = f"ip:{request.client.host}"
                    key = f"endpoint:{func.__name__}:{client_id}"

                # Check limit
                limiter = get_rate_limiter()
                is_allowed, remaining, retry_after = await limiter.is_allowed(
                    key, limit, window_seconds
                )

                if not is_allowed:
                    raise RateLimitExceeded(retry_after=retry_after)

            return await func(*args, **kwargs)

        return wrapper

    return decorator
