# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Rate limiting middleware using Redis (Pure ASGI).

Implements token bucket algorithm for API rate limiting.
"""

from datetime import UTC, datetime

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings


class RateLimitMiddleware:
    """
    Pure ASGI Rate limiting middleware.

    Uses Redis to track request counts per client.
    Implements sliding window rate limiting.
    """

    def __init__(
        self,
        app: ASGIApp,
        redis_client=None,
        requests_per_minute: int | None = None,
        burst_size: int | None = None,
    ) -> None:
        """Initialize rate limiter."""
        self.app = app
        self.redis = redis_client
        self.requests_per_minute = (
            requests_per_minute or settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        )
        self.burst_size = burst_size or settings.RATE_LIMIT_BURST_SIZE
        self.window_seconds = 60

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface - apply rate limiting."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip rate limiting if Redis not configured
        if not self.redis:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip rate limiting for health checks
        if path in ["/api/v1/health", "/health"]:
            await self.app(scope, receive, send)
            return

        # Get client identifier
        client_id = self._get_client_id(scope)
        key = f"rate_limit:{client_id}"

        # Check rate limit
        is_allowed, remaining, retry_after = await self._check_rate_limit(key)

        if not is_allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "limit": self.requests_per_minute,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )
            await response(scope, receive, send)
            return

        # Add rate limit headers to response
        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-ratelimit-limit", str(self.requests_per_minute).encode()),
                        (b"x-ratelimit-remaining", str(remaining).encode()),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)

    def _get_client_id(self, scope: Scope) -> str:
        """Get unique client identifier."""
        headers = dict(scope.get("headers", []))

        # Check for API key
        api_key = headers.get(b"x-api-key", b"").decode()
        if api_key:
            return f"api:{api_key[:16]}"

        # Fall back to IP — only trust X-Forwarded-For from trusted proxies
        client = scope.get("client")
        direct_ip = client[0] if client else "unknown"

        forwarded = headers.get(b"x-forwarded-for", b"").decode()
        if forwarded and self._is_trusted_proxy(direct_ip):
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = direct_ip

        return f"ip:{client_ip}"

    @staticmethod
    def _is_trusted_proxy(ip: str) -> bool:
        """Check if the direct connection comes from a trusted proxy (private network)."""
        import ipaddress

        try:
            addr = ipaddress.ip_address(ip)
            return addr.is_private or addr.is_loopback
        except ValueError:
            return False

    async def _check_rate_limit(
        self,
        key: str,
    ) -> tuple[bool, int, int]:
        """Check if request is within rate limit."""
        if self.redis is None:
            return True, self.requests_per_minute, 0

        now = datetime.now(UTC).timestamp()
        window_start = now - self.window_seconds

        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, self.window_seconds)

        results = await pipe.execute()
        request_count = results[1]

        max_requests = self.requests_per_minute + self.burst_size
        remaining = max(0, max_requests - request_count - 1)

        if request_count >= max_requests:
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] + self.window_seconds - now) + 1
            else:
                retry_after = self.window_seconds

            return False, 0, retry_after

        return True, remaining, 0
