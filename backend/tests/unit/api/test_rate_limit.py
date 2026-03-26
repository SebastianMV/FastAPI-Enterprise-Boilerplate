# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for Rate Limiting Middleware.

Tests for the RateLimitMiddleware class.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from app.api.middleware.rate_limit import RateLimitMiddleware


class TestRateLimitMiddlewareInit:
    """Tests for RateLimitMiddleware initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default values."""
        from app.api.middleware.rate_limit import RateLimitMiddleware

        mock_app = MagicMock()

        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10

            middleware = RateLimitMiddleware(app=mock_app)

            assert middleware.redis is None
            assert middleware.requests_per_minute == 60
            assert middleware.burst_size == 10
            assert middleware.window_seconds == 60

    def test_init_with_custom_values(self) -> None:
        """Test initialization with custom values."""
        from app.api.middleware.rate_limit import RateLimitMiddleware

        mock_app = MagicMock()
        mock_redis = MagicMock()

        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10

            middleware = RateLimitMiddleware(
                app=mock_app,
                redis_client=mock_redis,
                requests_per_minute=100,
                burst_size=20,
            )

            assert middleware.redis == mock_redis
            assert middleware.requests_per_minute == 100
            assert middleware.burst_size == 20


class TestRateLimitMiddlewareGetClientId:
    """Tests for _get_client_id method."""

    @pytest.fixture
    def middleware(self) -> RateLimitMiddleware:
        """Create middleware instance."""
        from app.api.middleware.rate_limit import RateLimitMiddleware

        mock_app = MagicMock()
        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            return RateLimitMiddleware(app=mock_app)

    def test_get_client_id_from_user(self, middleware) -> None:
        """Test getting client ID from authenticated user (not supported in pure ASGI)."""
        # In pure ASGI, we cannot access request.state, so API key or IP is used
        scope = {
            "headers": [(b"x-api-key", b"user-key-12345678")],
            "client": ("127.0.0.1", 8000),
        }

        result = middleware._get_client_id(scope)

        # First 16 characters: user-key-1234567
        assert result == "api:user-key-1234567"

    def test_get_client_id_from_api_key(self, middleware) -> None:
        """Test getting client ID from API key header."""
        scope = {
            "headers": [(b"x-api-key", b"abcd1234567890abcd1234567890")],
            "client": ("127.0.0.1", 8000),
        }

        result = middleware._get_client_id(scope)

        assert result == "api:abcd1234567890ab"

    def test_get_client_id_from_ip(self, middleware) -> None:
        """Test getting client ID from IP address."""
        scope = {
            "headers": [],
            "client": ("192.168.1.1", 8000),
        }

        result = middleware._get_client_id(scope)

        assert result == "ip:192.168.1.1"

    def test_get_client_id_from_forwarded_ip(self, middleware) -> None:
        """Test getting client ID from X-Forwarded-For header."""
        scope = {
            "headers": [(b"x-forwarded-for", b"10.0.0.1, 192.168.1.1")],
            "client": ("127.0.0.1", 8000),
        }

        result = middleware._get_client_id(scope)

        assert result == "ip:10.0.0.1"

    def test_get_client_id_unknown(self, middleware) -> None:
        """Test getting client ID when no client info available."""
        scope = {
            "headers": [],
            "client": None,
        }

        result = middleware._get_client_id(scope)

        assert result == "ip:unknown"


class TestRateLimitMiddlewareCheckRateLimit:
    """Tests for _check_rate_limit method."""

    @pytest.fixture
    def middleware(self) -> RateLimitMiddleware:
        """Create middleware instance."""
        from app.api.middleware.rate_limit import RateLimitMiddleware

        mock_app = MagicMock()
        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            return RateLimitMiddleware(
                app=mock_app, requests_per_minute=60, burst_size=10
            )

    @pytest.mark.asyncio
    async def test_check_rate_limit_no_redis(self, middleware) -> None:
        """Test rate limit check with no Redis - always allows."""
        middleware.redis = None

        is_allowed, remaining, retry_after = await middleware._check_rate_limit("key")

        assert is_allowed is True
        assert remaining == 60
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, middleware) -> None:
        """Test rate limit check when request is allowed."""
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.zadd = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 10, None, None])
        mock_redis.pipeline.return_value = mock_pipe

        middleware.redis = mock_redis

        is_allowed, remaining, retry_after = await middleware._check_rate_limit("key")

        assert is_allowed is True
        assert remaining == 59  # 60 + 10 - 10 - 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, middleware) -> None:
        """Test rate limit check when limit is exceeded."""
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.zadd = MagicMock()
        mock_pipe.expire = MagicMock()
        # Request count exceeds max
        mock_pipe.execute = AsyncMock(return_value=[None, 100, None, None])
        mock_redis.pipeline.return_value = mock_pipe
        mock_redis.zrange = AsyncMock(
            return_value=[(b"ts", datetime.now(UTC).timestamp() - 30)]
        )

        middleware.redis = mock_redis

        is_allowed, remaining, retry_after = await middleware._check_rate_limit("key")

        assert is_allowed is False
        assert remaining == 0
        assert retry_after > 0


class TestRateLimitMiddlewareDispatch:
    """Tests for ASGI __call__ method using real HTTP client."""

    @pytest.fixture
    def middleware(self) -> RateLimitMiddleware:
        """Create middleware instance."""
        from app.api.middleware.rate_limit import RateLimitMiddleware

        mock_app = MagicMock()
        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            return RateLimitMiddleware(app=mock_app)

    @pytest.mark.asyncio
    async def test_dispatch_skips_without_redis(self, middleware) -> None:
        """Test dispatch skips rate limiting without Redis."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.api.middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            return {"ok": True}

        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            app.add_middleware(RateLimitMiddleware, redis_client=None)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/users")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_skips_health_check(self, middleware) -> None:
        """Test dispatch skips rate limiting for health checks."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.api.middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()

        @app.get("/api/v1/health")
        async def health():
            return {"status": "ok"}

        mock_redis = MagicMock()

        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_adds_headers(self, middleware) -> None:
        """Test dispatch adds rate limit headers to response."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.api.middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            return {"ok": True}

        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.zadd = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 5, None, None])
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/users")

        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_rate_limit_exceeded(self, middleware) -> None:
        """Test dispatch returns 429 when rate limit exceeded."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.api.middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            return {"ok": True}

        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.zadd = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 100, None, None])
        mock_redis.pipeline.return_value = mock_pipe
        mock_redis.zrange = AsyncMock(return_value=[(b"ts", 1700000000.0)])

        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            app.add_middleware(RateLimitMiddleware, redis_client=mock_redis)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/users")

        assert response.status_code == 429
        assert "retry-after" in response.headers


class TestRateLimitConstants:
    """Tests for rate limit constants and keys."""

    def test_middleware_constants(self) -> None:
        """Test middleware uses correct window size."""
        from app.api.middleware.rate_limit import RateLimitMiddleware

        mock_app = MagicMock()
        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            middleware = RateLimitMiddleware(app=mock_app)

        assert middleware.window_seconds == 60
