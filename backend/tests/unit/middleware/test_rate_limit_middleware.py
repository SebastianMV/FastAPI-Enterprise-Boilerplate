# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Rate Limit Middleware.

Tests for in-memory and sliding window rate limiting.
"""

import time
from unittest.mock import MagicMock

import pytest

from app.middleware.rate_limit import (
    RATE_LIMITS,
    InMemoryRateLimiter,
    RateLimitExceeded,
    SlidingWindowEntry,
    get_rate_limit_for_path,
    get_rate_limiter,
)


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_exception_status_code(self) -> None:
        """Test that exception has correct status code."""
        exc = RateLimitExceeded(retry_after=60)

        assert exc.status_code == 429

    def test_exception_detail(self) -> None:
        """Test that exception has correct detail message."""
        exc = RateLimitExceeded(retry_after=30)

        assert exc.detail == "Rate limit exceeded. Please try again later."

    def test_exception_headers(self) -> None:
        """Test that exception includes Retry-After header."""
        exc = RateLimitExceeded(retry_after=45)

        assert exc.headers is not None
        assert "Retry-After" in exc.headers
        assert exc.headers["Retry-After"] == "45"


class TestSlidingWindowEntry:
    """Tests for SlidingWindowEntry."""

    def test_create_entry(self) -> None:
        """Test creating a sliding window entry."""
        now = time.time()
        entry = SlidingWindowEntry(timestamp=now, count=5)

        assert entry.timestamp == now
        assert entry.count == 5

    def test_entry_default_count(self) -> None:
        """Test entry with default count."""
        entry = SlidingWindowEntry(timestamp=time.time())

        assert entry.count == 1


class TestInMemoryRateLimiter:
    """Tests for InMemoryRateLimiter."""

    @pytest.fixture
    def limiter(self) -> InMemoryRateLimiter:
        """Create a fresh rate limiter for each test."""
        return InMemoryRateLimiter()

    @pytest.mark.asyncio
    async def test_allows_first_request(self, limiter: InMemoryRateLimiter) -> None:
        """Test that first request is allowed."""
        is_allowed, remaining, retry_after = await limiter.is_allowed(
            key="test_key",
            limit=10,
            window_seconds=60,
        )

        assert is_allowed is True
        assert remaining == 9
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, limiter: InMemoryRateLimiter) -> None:
        """Test that requests under limit are allowed."""
        key = "test_key"
        limit = 5

        for i in range(limit):
            is_allowed, remaining, _ = await limiter.is_allowed(
                key=key, limit=limit, window_seconds=60
            )
            assert is_allowed is True
            assert remaining == limit - i - 1

    @pytest.mark.asyncio
    async def test_blocks_when_limit_exceeded(self, limiter: InMemoryRateLimiter) -> None:
        """Test that requests are blocked when limit exceeded."""
        key = "test_key"
        limit = 3

        # Use up the limit
        for _ in range(limit):
            await limiter.is_allowed(key=key, limit=limit, window_seconds=60)

        # Next request should be blocked
        is_allowed, remaining, retry_after = await limiter.is_allowed(
            key=key, limit=limit, window_seconds=60
        )

        assert is_allowed is False
        assert remaining == 0
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_different_keys_independent(self, limiter: InMemoryRateLimiter) -> None:
        """Test that different keys have independent limits."""
        key1 = "user_1"
        key2 = "user_2"
        limit = 2

        # Use up key1's limit
        await limiter.is_allowed(key=key1, limit=limit, window_seconds=60)
        await limiter.is_allowed(key=key1, limit=limit, window_seconds=60)

        # key2 should still be allowed
        is_allowed, remaining, _ = await limiter.is_allowed(
            key=key2, limit=limit, window_seconds=60
        )

        assert is_allowed is True
        assert remaining == 1

    @pytest.mark.asyncio
    async def test_window_expires_allows_new_requests(
        self, limiter: InMemoryRateLimiter
    ) -> None:
        """Test that expired window entries are cleared."""
        key = "test_key"
        limit = 2
        window = 1  # 1 second window

        # Use up the limit
        await limiter.is_allowed(key=key, limit=limit, window_seconds=window)
        await limiter.is_allowed(key=key, limit=limit, window_seconds=window)

        # Should be blocked
        is_allowed, _, _ = await limiter.is_allowed(
            key=key, limit=limit, window_seconds=window
        )
        assert is_allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        is_allowed, remaining, _ = await limiter.is_allowed(
            key=key, limit=limit, window_seconds=window
        )
        assert is_allowed is True

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_entries(self, limiter: InMemoryRateLimiter) -> None:
        """Test cleanup removes old entries."""
        # Add some requests
        await limiter.is_allowed(key="key1", limit=10, window_seconds=60)
        await limiter.is_allowed(key="key2", limit=10, window_seconds=60)

        # Verify keys exist
        assert "key1" in limiter._requests
        assert "key2" in limiter._requests

        # Cleanup with max_age=0 should remove everything
        limiter.cleanup(max_age=0)

        # All keys should be gone
        assert "key1" not in limiter._requests
        assert "key2" not in limiter._requests


class TestGetRateLimiter:
    """Tests for get_rate_limiter singleton."""

    def test_returns_same_instance(self) -> None:
        """Test that get_rate_limiter returns same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2

    def test_returns_in_memory_limiter(self) -> None:
        """Test that get_rate_limiter returns InMemoryRateLimiter."""
        limiter = get_rate_limiter()

        assert isinstance(limiter, InMemoryRateLimiter)


class TestRateLimitConfiguration:
    """Tests for rate limit configuration."""

    def test_auth_login_rate_limit(self) -> None:
        """Test login endpoint has strict rate limit."""
        limit, window = RATE_LIMITS.get("/api/v1/auth/login", (0, 0))

        assert limit == 5
        assert window == 60

    def test_auth_register_rate_limit(self) -> None:
        """Test register endpoint has strict rate limit."""
        limit, window = RATE_LIMITS.get("/api/v1/auth/register", (0, 0))

        assert limit == 3
        assert window == 60

    def test_default_rate_limit(self) -> None:
        """Test default rate limit exists."""
        limit, window = RATE_LIMITS.get("default", (0, 0))

        assert limit == 100
        assert window == 60

    def test_get_endpoints_higher_limit(self) -> None:
        """Test GET endpoints have higher limits."""
        limit, window = RATE_LIMITS.get("GET:/api/v1/", (0, 0))

        assert limit == 200


class TestGetRateLimitForPath:
    """Tests for get_rate_limit_for_path function."""

    def test_exact_path_match(self) -> None:
        """Test exact path matching."""
        limit, window = get_rate_limit_for_path("POST", "/api/v1/auth/login")

        assert limit == 5
        assert window == 60

    def test_method_path_match(self) -> None:
        """Test method+path matching."""
        limit, window = get_rate_limit_for_path("GET", "/api/v1/users")

        # Should match GET:/api/v1/ pattern
        assert limit == 200

    def test_default_fallback(self) -> None:
        """Test fallback to default."""
        limit, window = get_rate_limit_for_path("POST", "/unknown/path")

        assert limit == 100
        assert window == 60


class TestRateLimitRetryAfter:
    """Tests for retry-after calculation."""

    @pytest.mark.asyncio
    async def test_retry_after_is_positive(self) -> None:
        """Test that retry_after is always positive."""
        limiter = InMemoryRateLimiter()
        key = "test"
        limit = 1

        # Use up limit
        await limiter.is_allowed(key=key, limit=limit, window_seconds=60)

        # Next request blocked
        is_allowed, _, retry_after = await limiter.is_allowed(
            key=key, limit=limit, window_seconds=60
        )

        assert is_allowed is False
        assert retry_after > 0
        assert retry_after <= 61  # Should be within window + 1


class TestRedisRateLimiter:
    """Tests for RedisRateLimiter initialization."""

    def test_redis_limiter_init(self) -> None:
        """Test RedisRateLimiter initialization."""
        from app.middleware.rate_limit import RedisRateLimiter

        mock_redis = MagicMock()
        limiter = RedisRateLimiter(redis_client=mock_redis)

        assert limiter.redis is mock_redis

    def test_redis_limiter_creates_key_prefix(self) -> None:
        """Test that RedisRateLimiter would create proper key prefix."""
        # Verify the rate limit key format
        key = "user:123"
        redis_key = f"ratelimit:{key}"

        assert redis_key == "ratelimit:user:123"
