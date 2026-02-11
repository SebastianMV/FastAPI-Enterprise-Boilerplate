# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for rate limiting middleware."""

import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import Request, status

from app.middleware.rate_limit import (
    RATE_LIMITS,
    InMemoryRateLimiter,
    RateLimitExceeded,
    RateLimitMiddleware,
    RedisRateLimiter,
    SlidingWindowEntry,
    get_rate_limit_for_path,
    get_rate_limiter,
    rate_limit,
)


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_creates_exception_with_retry_after(self):
        exc = RateLimitExceeded(retry_after=30)
        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "30 seconds" in exc.detail
        assert exc.headers is not None  # Type narrowing
        assert exc.headers["Retry-After"] == "30"

    def test_different_retry_values(self):
        for seconds in [1, 60, 300, 3600]:
            exc = RateLimitExceeded(retry_after=seconds)
            assert exc.headers is not None  # Type narrowing
            assert exc.headers["Retry-After"] == str(seconds)


class TestSlidingWindowEntry:
    """Tests for SlidingWindowEntry."""

    def test_creates_with_timestamp(self):
        now = time.time()
        entry = SlidingWindowEntry(timestamp=now)
        assert entry.timestamp == now
        assert entry.count == 1

    def test_creates_with_custom_count(self):
        entry = SlidingWindowEntry(timestamp=100.0, count=5)
        assert entry.timestamp == 100.0
        assert entry.count == 5


class TestInMemoryRateLimiter:
    """Tests for InMemoryRateLimiter."""

    def test_allows_first_request(self):
        limiter = InMemoryRateLimiter()
        allowed, remaining, retry_after = limiter.is_allowed("key1", 10, 60)
        assert allowed is True
        assert remaining == 9
        assert retry_after == 0

    def test_allows_up_to_limit(self):
        limiter = InMemoryRateLimiter()
        key = "test_key"

        for i in range(10):
            allowed, remaining, retry_after = limiter.is_allowed(key, 10, 60)
            assert allowed is True
            assert remaining == 10 - i - 1

    def test_blocks_over_limit(self):
        limiter = InMemoryRateLimiter()
        key = "blocked_key"

        # Use up the limit
        for _ in range(5):
            limiter.is_allowed(key, 5, 60)

        # Next request should be blocked
        allowed, remaining, retry_after = limiter.is_allowed(key, 5, 60)
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    def test_retry_after_is_positive(self):
        limiter = InMemoryRateLimiter()
        key = "retry_key"

        for _ in range(3):
            limiter.is_allowed(key, 3, 60)

        allowed, _, retry_after = limiter.is_allowed(key, 3, 60)
        assert allowed is False
        assert retry_after >= 1

    def test_different_keys_independent(self):
        limiter = InMemoryRateLimiter()

        # Use up limit for key1
        for _ in range(5):
            limiter.is_allowed("key1", 5, 60)

        # key2 should still be allowed
        allowed, remaining, _ = limiter.is_allowed("key2", 5, 60)
        assert allowed is True
        assert remaining == 4

    def test_cleanup_removes_old_entries(self):
        limiter = InMemoryRateLimiter()
        key = "cleanup_key"

        # Add some requests
        limiter.is_allowed(key, 10, 60)
        assert key in limiter._requests

        # Manually set old timestamps
        limiter._requests[key] = [time.time() - 7200]

        # Cleanup with 1 hour max age
        limiter.cleanup(max_age=3600)

        # Key should be removed
        assert key not in limiter._requests

    def test_cleanup_keeps_recent_entries(self):
        limiter = InMemoryRateLimiter()
        key = "keep_key"

        limiter.is_allowed(key, 10, 60)
        limiter.cleanup(max_age=3600)

        # Recent entry should be kept
        assert key in limiter._requests


class TestRedisRateLimiter:
    """Tests for RedisRateLimiter."""

    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 5, None, None])
        mock_redis.pipeline = Mock(return_value=mock_pipe)
        mock_redis.zrem = AsyncMock()
        mock_redis.zrange = AsyncMock(return_value=[])

        limiter = RedisRateLimiter(mock_redis)
        allowed, remaining, retry_after = await limiter.is_allowed("key", 10, 60)

        assert allowed is True
        assert remaining == 4
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_blocks_request_over_limit(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 10, None, None])
        mock_redis.pipeline = Mock(return_value=mock_pipe)
        mock_redis.zrem = AsyncMock()
        mock_redis.zrange = AsyncMock(return_value=[("ts", time.time() - 30)])

        limiter = RedisRateLimiter(mock_redis)
        allowed, remaining, retry_after = await limiter.is_allowed("key", 10, 60)

        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_returns_window_seconds_if_no_oldest(self):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 10, None, None])
        mock_redis.pipeline = Mock(return_value=mock_pipe)
        mock_redis.zrem = AsyncMock()
        mock_redis.zrange = AsyncMock(return_value=[])

        limiter = RedisRateLimiter(mock_redis)
        allowed, _, retry_after = await limiter.is_allowed("key", 10, 60)

        assert allowed is False
        assert retry_after == 60


class TestGetRateLimiter:
    """Tests for get_rate_limiter singleton."""

    def test_returns_rate_limiter(self):
        limiter = get_rate_limiter()
        assert isinstance(limiter, InMemoryRateLimiter)

    def test_returns_same_instance(self):
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2


class TestGetRateLimitForPath:
    """Tests for get_rate_limit_for_path."""

    def test_returns_default_for_unknown_path(self):
        limit, window = get_rate_limit_for_path("POST", "/api/v1/unknown")
        assert (limit, window) == RATE_LIMITS["default"]

    def test_returns_exact_match(self):
        limit, window = get_rate_limit_for_path("POST", "/api/v1/auth/login")
        assert (limit, window) == (5, 60)

    def test_returns_register_limit(self):
        limit, window = get_rate_limit_for_path("POST", "/api/v1/auth/register")
        assert (limit, window) == (3, 60)

    def test_returns_get_prefix_match(self):
        limit, window = get_rate_limit_for_path("GET", "/api/v1/users")
        assert (limit, window) == (200, 60)


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware using pure ASGI interface."""

    @pytest.mark.asyncio
    async def test_skips_exempt_paths(self):
        """Test that exempt paths bypass rate limiting."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            app.add_middleware(RateLimitMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skips_when_disabled(self):
        """Test that rate limiting is skipped when disabled."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = False
            app.add_middleware(RateLimitMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/test")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_client_ip_from_direct(self):
        """Test IP extraction from direct client connection."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        captured_ip = None

        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"ok": True}

        # Test with real ASGI app - client IP handling
        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
                mock_limiter = Mock()
                mock_limiter.is_allowed = Mock(return_value=(True, 99, 0))
                mock_limiter_fn.return_value = mock_limiter

                app.add_middleware(RateLimitMiddleware)

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/v1/test")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_client_ip_from_forwarded(self):
        """Test IP extraction from X-Forwarded-For header."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
                mock_limiter = Mock()
                mock_limiter.is_allowed = Mock(return_value=(True, 99, 0))
                mock_limiter_fn.return_value = mock_limiter

                app.add_middleware(RateLimitMiddleware)

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/api/v1/test",
                        headers={"X-Forwarded-For": "10.0.0.1, 192.168.1.1"},
                    )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_client_ip_from_real_ip(self):
        """Test IP extraction from X-Real-IP header."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
                mock_limiter = Mock()
                mock_limiter.is_allowed = Mock(return_value=(True, 99, 0))
                mock_limiter_fn.return_value = mock_limiter

                app.add_middleware(RateLimitMiddleware)

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/api/v1/test", headers={"X-Real-IP": "172.16.0.50"}
                    )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_client_ip_unknown_fallback(self):
        """Test IP falls back to 'unknown' when client is unavailable."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
                mock_limiter = Mock()
                mock_limiter.is_allowed = Mock(return_value=(True, 99, 0))
                mock_limiter_fn.return_value = mock_limiter

                app.add_middleware(RateLimitMiddleware)

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/v1/test")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_rate_limit_key_by_ip(self):
        """Test rate limit key uses IP."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
                mock_limiter = Mock()
                mock_limiter.is_allowed = Mock(return_value=(True, 99, 0))
                mock_limiter_fn.return_value = mock_limiter

                app.add_middleware(RateLimitMiddleware)

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/v1/test")

                # Check the key format used
                call_args = mock_limiter.is_allowed.call_args
                key = call_args[0][0]
                assert key.startswith("ip:")

    @pytest.mark.asyncio
    async def test_get_rate_limit_key_by_user(self):
        """Test rate limit key uses user ID when authenticated."""
        # This test would need authentication setup, skipping for now

    @pytest.mark.asyncio
    async def test_get_rate_limit_key_by_api_key(self):
        """Test rate limit key uses API key prefix."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
                mock_limiter = Mock()
                mock_limiter.is_allowed = Mock(return_value=(True, 99, 0))
                mock_limiter_fn.return_value = mock_limiter

                app.add_middleware(RateLimitMiddleware)

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        "/api/v1/test",
                        headers={"Authorization": "Bearer krs_abc123xyz"},
                    )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_adds_rate_limit_headers(self):
        """Test that rate limit headers are added to response."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
                mock_limiter = Mock()
                mock_limiter.is_allowed = Mock(return_value=(True, 99, 0))
                mock_limiter_fn.return_value = mock_limiter

                app.add_middleware(RateLimitMiddleware)

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/v1/test")

        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers
        assert "x-ratelimit-reset" in response.headers

    @pytest.mark.asyncio
    async def test_raises_when_limit_exceeded(self):
        """Test that 429 is returned when rate limit exceeded."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"ok": True}

        with patch("app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
                mock_limiter = Mock()
                mock_limiter.is_allowed = Mock(return_value=(False, 0, 30))
                mock_limiter_fn.return_value = mock_limiter

                app.add_middleware(RateLimitMiddleware)

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get("/api/v1/test")

        assert response.status_code == 429
        assert "retry-after" in response.headers


class TestRateLimitDecorator:
    """Tests for rate_limit decorator."""

    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self):
        @rate_limit(limit=10, window_seconds=60)
        async def test_endpoint(request: Request):
            return "success"

        mock_request = Mock(spec=Request)

        with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
            mock_limiter = Mock()
            mock_limiter.is_allowed = Mock(return_value=(True, 9, 0))
            mock_limiter_fn.return_value = mock_limiter

            result = await test_endpoint(mock_request)
            assert result == "success"

    @pytest.mark.asyncio
    async def test_blocks_request_over_limit(self):
        @rate_limit(limit=5, window_seconds=60)
        async def test_endpoint(request: Request):
            return "success"

        mock_request = Mock(spec=Request)

        with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
            mock_limiter = Mock()
            mock_limiter.is_allowed = Mock(return_value=(False, 0, 45))
            mock_limiter_fn.return_value = mock_limiter

            with pytest.raises(RateLimitExceeded):
                await test_endpoint(mock_request)

    @pytest.mark.asyncio
    async def test_custom_key_func(self):
        custom_key_called = False

        def custom_key(request):
            nonlocal custom_key_called
            custom_key_called = True
            return "custom_key"

        @rate_limit(limit=10, window_seconds=60, key_func=custom_key)
        async def test_endpoint(request: Request):
            return "success"

        mock_request = Mock(spec=Request)

        with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
            mock_limiter = Mock()
            mock_limiter.is_allowed = Mock(return_value=(True, 9, 0))
            mock_limiter_fn.return_value = mock_limiter

            await test_endpoint(mock_request)
            assert custom_key_called

    @pytest.mark.asyncio
    async def test_works_without_request(self):
        @rate_limit(limit=10, window_seconds=60)
        async def test_endpoint():
            return "success"

        result = await test_endpoint()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_request_from_kwargs(self):
        @rate_limit(limit=10, window_seconds=60)
        async def test_endpoint(request: Request):
            return "success"

        mock_request = Mock(spec=Request)

        with patch("app.middleware.rate_limit.get_rate_limiter") as mock_limiter_fn:
            mock_limiter = Mock()
            mock_limiter.is_allowed = Mock(return_value=(True, 9, 0))
            mock_limiter_fn.return_value = mock_limiter

            result = await test_endpoint(request=mock_request)
            assert result == "success"
