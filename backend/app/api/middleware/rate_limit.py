# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Rate limiting middleware using Redis.

Implements token bucket algorithm for API rate limiting.
"""

from datetime import datetime, UTC
from typing import Callable

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    
    Uses Redis to track request counts per client.
    Implements sliding window rate limiting.
    
    Configuration:
        - RATE_LIMIT_REQUESTS_PER_MINUTE: Max requests per minute
        - RATE_LIMIT_BURST_SIZE: Allowed burst above limit
    """
    
    def __init__(
        self,
        app,
        redis_client=None,
        requests_per_minute: int | None = None,
        burst_size: int | None = None,
    ) -> None:
        """
        Initialize rate limiter.
        
        Args:
            app: FastAPI application
            redis_client: Redis client instance
            requests_per_minute: Override default limit
            burst_size: Override default burst size
        """
        super().__init__(app)
        self.redis = redis_client
        self.requests_per_minute = (
            requests_per_minute or settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        )
        self.burst_size = burst_size or settings.RATE_LIMIT_BURST_SIZE
        self.window_seconds = 60
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/route handler
            
        Returns:
            Response from downstream handler
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Skip rate limiting if Redis not configured
        if not self.redis:
            return await call_next(request)
        
        # Skip rate limiting for health checks
        if request.url.path in ["/api/v1/health", "/health"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        key = f"rate_limit:{client_id}"
        
        # Check rate limit
        is_allowed, remaining, retry_after = await self._check_rate_limit(key)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
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
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier.
        
        Uses:
        1. Authenticated user ID (if available)
        2. API key (if present)
        3. Client IP address (fallback)
        """
        # Check for user ID from auth
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{api_key[:16]}"
        
        # Fall back to IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    async def _check_rate_limit(
        self,
        key: str,
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.
        
        Args:
            key: Rate limit key for client
            
        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        # If Redis is not configured, allow all requests
        if self.redis is None:
            return True, self.requests_per_minute, 0
        
        now = datetime.now(UTC).timestamp()
        window_start = now - self.window_seconds
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove old entries outside window
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiry
        pipe.expire(key, self.window_seconds)
        
        results = await pipe.execute()
        request_count = results[1]
        
        # Calculate remaining
        max_requests = self.requests_per_minute + self.burst_size
        remaining = max(0, max_requests - request_count - 1)
        
        if request_count >= max_requests:
            # Calculate retry after
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] + self.window_seconds - now) + 1
            else:
                retry_after = self.window_seconds
            
            return False, 0, retry_after
        
        return True, remaining, 0
