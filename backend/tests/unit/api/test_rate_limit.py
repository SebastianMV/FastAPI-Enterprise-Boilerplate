# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Rate Limiting Middleware.

Tests for the RateLimitMiddleware class.
"""

from __future__ import annotations

from datetime import datetime, UTC
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
    def middleware(self) -> "RateLimitMiddleware":
        """Create middleware instance."""
        from app.api.middleware.rate_limit import RateLimitMiddleware

        mock_app = MagicMock()
        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            return RateLimitMiddleware(app=mock_app)

    def test_get_client_id_from_user(self, middleware) -> None:
        """Test getting client ID from authenticated user."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user-123"

        result = middleware._get_client_id(mock_request)

        assert result == "user:user-123"

    def test_get_client_id_from_api_key(self, middleware) -> None:
        """Test getting client ID from API key header."""
        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # No user_id
        mock_request.headers = {"X-API-Key": "abcd1234567890abcd1234567890"}

        result = middleware._get_client_id(mock_request)

        assert result == "api:abcd1234567890ab"

    def test_get_client_id_from_ip(self, middleware) -> None:
        """Test getting client ID from IP address."""
        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # No user_id
        mock_request.headers = {}  # No API key
        mock_request.client.host = "192.168.1.1"

        result = middleware._get_client_id(mock_request)

        assert result == "ip:192.168.1.1"

    def test_get_client_id_from_forwarded_ip(self, middleware) -> None:
        """Test getting client ID from X-Forwarded-For header."""
        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # No user_id
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        mock_request.client.host = "127.0.0.1"

        result = middleware._get_client_id(mock_request)

        assert result == "ip:10.0.0.1"

    def test_get_client_id_unknown(self, middleware) -> None:
        """Test getting client ID when no client info available."""
        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # No user_id
        mock_request.headers = {}  # No API key, no forwarded
        mock_request.client = None

        result = middleware._get_client_id(mock_request)

        assert result == "ip:unknown"


class TestRateLimitMiddlewareCheckRateLimit:
    """Tests for _check_rate_limit method."""

    @pytest.fixture
    def middleware(self) -> "RateLimitMiddleware":
        """Create middleware instance."""
        from app.api.middleware.rate_limit import RateLimitMiddleware

        mock_app = MagicMock()
        with patch("app.api.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_REQUESTS_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_BURST_SIZE = 10
            return RateLimitMiddleware(app=mock_app, requests_per_minute=60, burst_size=10)

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
        mock_redis.zrange = AsyncMock(return_value=[(b"ts", datetime.now(UTC).timestamp() - 30)])

        middleware.redis = mock_redis

        is_allowed, remaining, retry_after = await middleware._check_rate_limit("key")

        assert is_allowed is False
        assert remaining == 0
        assert retry_after > 0


class TestRateLimitMiddlewareDispatch:
    """Tests for dispatch method."""

    @pytest.fixture
    def middleware(self) -> "RateLimitMiddleware":
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
        middleware.redis = None

        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result == mock_response
        mock_call_next.assert_awaited_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_skips_health_check(self, middleware) -> None:
        """Test dispatch skips rate limiting for health checks."""
        mock_redis = AsyncMock()
        middleware.redis = mock_redis

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/health"
        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result == mock_response
        mock_call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_adds_headers(self, middleware) -> None:
        """Test dispatch adds rate limit headers to response."""
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.zadd = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 5, None, None])
        mock_redis.pipeline.return_value = mock_pipe
        middleware.redis = mock_redis

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/users"
        mock_request.state = MagicMock(spec=[])
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"

        mock_response = MagicMock()
        mock_response.headers = {}
        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert "X-RateLimit-Limit" in result.headers
        assert "X-RateLimit-Remaining" in result.headers

    @pytest.mark.asyncio
    async def test_dispatch_rate_limit_exceeded(self, middleware) -> None:
        """Test dispatch raises HTTPException when rate limit exceeded."""
        from fastapi import HTTPException

        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.zadd = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 100, None, None])
        mock_redis.pipeline.return_value = mock_pipe
        mock_redis.zrange = AsyncMock(return_value=[(b"ts", datetime.now(UTC).timestamp() - 30)])
        middleware.redis = mock_redis

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/users"
        mock_request.state = MagicMock(spec=[])
        mock_request.headers = {}
        mock_request.client.host = "127.0.0.1"

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value.detail)


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
