# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for Redis client wrapper (delegates to centralized cache)."""

from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.cache.redis_client import (
    close_redis_client,
    get_redis_client,
)


class TestGetRedisClient:
    """Test Redis client retrieval via centralized cache."""

    @pytest.mark.asyncio
    async def test_returns_redis_client_from_cache(self):
        """Test that get_redis_client returns client from get_cache()."""
        mock_redis = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get_redis_client.return_value = mock_redis

        with patch(
            "app.infrastructure.cache.redis_client.get_cache",
            return_value=mock_cache,
        ):
            client = await get_redis_client()

            assert client is mock_redis
            mock_cache.get_redis_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_get_cache(self):
        """Test that get_redis_client calls get_cache()."""
        mock_cache = MagicMock()
        mock_cache.get_redis_client.return_value = MagicMock()

        with patch(
            "app.infrastructure.cache.redis_client.get_cache",
            return_value=mock_cache,
        ) as mock_get_cache:
            await get_redis_client()

            mock_get_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_same_client_on_multiple_calls(self):
        """Test that multiple calls return consistent client from cache."""
        mock_redis = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get_redis_client.return_value = mock_redis

        with patch(
            "app.infrastructure.cache.redis_client.get_cache",
            return_value=mock_cache,
        ):
            client1 = await get_redis_client()
            client2 = await get_redis_client()

            assert client1 is mock_redis
            assert client2 is mock_redis


class TestCloseRedisClient:
    """Test Redis client close (no-op — lifecycle managed by cache singleton)."""

    @pytest.mark.asyncio
    async def test_close_does_not_raise(self):
        """Test that close_redis_client completes without error."""
        # close_redis_client is a no-op; just verify it doesn't raise
        await close_redis_client()

    @pytest.mark.asyncio
    async def test_get_client_works_after_close(self):
        """Test that get_redis_client works after close (since close is no-op)."""
        mock_redis = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get_redis_client.return_value = mock_redis

        await close_redis_client()

        with patch(
            "app.infrastructure.cache.redis_client.get_cache",
            return_value=mock_cache,
        ):
            client = await get_redis_client()
            assert client is mock_redis
