# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for rate limiting middleware."""

import time

import pytest

from app.middleware.rate_limit import (
    InMemoryRateLimiter,
    SlidingWindowEntry,
    get_rate_limit_for_path,
)


class TestInMemoryRateLimiter:
    """Tests for in-memory rate limiter."""

    @pytest.fixture
    def limiter(self):
        """Create a fresh rate limiter for each test."""
        return InMemoryRateLimiter()

    def test_allows_requests_under_limit(self, limiter):
        """Should allow requests under the limit."""
        key = "test_user"
        limit = 10
        window = 60

        for i in range(limit):
            allowed, remaining, retry_after = limiter.is_allowed(key, limit, window)
            assert allowed is True, f"Request {i + 1} should be allowed"

    def test_blocks_requests_over_limit(self, limiter):
        """Should block requests over the limit."""
        key = "test_user"
        limit = 5
        window = 60

        # Exhaust the limit
        for _ in range(limit):
            limiter.is_allowed(key, limit, window)

        # Next request should be blocked
        allowed, remaining, retry_after = limiter.is_allowed(key, limit, window)
        assert allowed is False

    def test_reset_after_window(self, limiter):
        """Should reset counter after window expires."""
        key = "test_user"
        limit = 5
        window = 1  # 1 second window

        # Exhaust the limit
        for _ in range(limit):
            limiter.is_allowed(key, limit, window)

        # Should be blocked
        allowed, _, _ = limiter.is_allowed(key, limit, window)
        assert allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        allowed, _, _ = limiter.is_allowed(key, limit, window)
        assert allowed is True

    def test_returns_remaining_count(self, limiter):
        """Should return correct remaining count."""
        key = "test_user"
        limit = 10
        window = 60

        # Use 3 requests
        for _ in range(3):
            limiter.is_allowed(key, limit, window)

        allowed, remaining, _ = limiter.is_allowed(key, limit, window)
        assert allowed is True
        assert remaining == limit - 4  # 10 - 4 = 6

    def test_returns_retry_after_when_blocked(self, limiter):
        """Should return retry_after when blocked."""
        key = "test_user"
        limit = 5
        window = 60

        # Exhaust the limit
        for _ in range(limit):
            limiter.is_allowed(key, limit, window)

        # Check retry_after
        allowed, remaining, retry_after = limiter.is_allowed(key, limit, window)
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    def test_different_keys_independent(self, limiter):
        """Different keys should have independent limits."""
        limit = 5
        window = 60

        # Exhaust limit for user1
        for _ in range(limit):
            limiter.is_allowed("user1", limit, window)

        # user1 blocked
        allowed, _, _ = limiter.is_allowed("user1", limit, window)
        assert allowed is False

        # user2 should still be allowed
        allowed, _, _ = limiter.is_allowed("user2", limit, window)
        assert allowed is True

    def test_cleanup_removes_old_entries(self, limiter):
        """Should cleanup old entries to prevent memory leak."""
        key = "test_user"
        limit = 10
        window = 1  # 1 second window

        # Add entries
        limiter.is_allowed(key, limit, window)
        assert key in limiter._requests

        # Wait for entries to expire
        time.sleep(1.5)

        # Trigger cleanup
        limiter.cleanup(max_age=1)

        # Old entries should be cleaned up
        assert key not in limiter._requests


class TestSlidingWindowEntry:
    """Tests for sliding window entry."""

    def test_create_entry(self):
        """Should create entry with timestamp and count."""
        current = time.time()
        entry = SlidingWindowEntry(timestamp=current, count=1)

        assert entry.timestamp == current
        assert entry.count == 1

    def test_create_entry_with_count(self):
        """Should create entry with custom count."""
        current = time.time()
        entry = SlidingWindowEntry(timestamp=current, count=5)

        assert entry.count == 5


class TestRateLimitPath:
    """Tests for rate limit path matching."""

    def test_auth_path_has_lower_limit(self):
        """Auth endpoints should have lower limits."""
        limit, window = get_rate_limit_for_path("POST", "/api/v1/auth/login")
        # Auth has specific limit in RATE_LIMITS
        assert limit > 0
        assert window == 60

    def test_default_limit(self):
        """Should return default for unknown paths."""
        # POST to unknown path should get default limit
        limit, window = get_rate_limit_for_path("POST", "/unknown/path")
        assert limit == 100  # Default from RATE_LIMITS["default"]
        assert window == 60

    def test_get_path_has_higher_limit(self):
        """GET requests to /api/v1/ should have higher limits."""
        limit, window = get_rate_limit_for_path("GET", "/api/v1/users")
        # GET:/api/v1/ pattern has 200 limit
        assert limit == 200
        assert window == 60
