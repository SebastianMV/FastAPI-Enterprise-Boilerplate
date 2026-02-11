# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for Redis client singleton."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.cache.redis_client import (
    close_redis_client,
    get_redis_client,
)


@pytest.fixture(autouse=True)
def reset_redis_client():
    """Reset Redis client singleton between tests."""
    import app.infrastructure.cache.redis_client as redis_client_module

    redis_client_module._redis_client = None
    yield
    redis_client_module._redis_client = None


class TestGetRedisClient:
    """Test Redis client initialization."""

    @pytest.mark.asyncio
    async def test_creates_new_client_if_none_exists(self):
        """Test that get_redis_client creates a new client if none exists."""
        mock_redis = MagicMock()

        with patch("redis.asyncio.Redis", return_value=mock_redis) as mock_redis_class:
            client = await get_redis_client()

            assert client == mock_redis
            mock_redis_class.assert_called_once()
            # Verify it was called with proper settings
            call_kwargs = mock_redis_class.call_args.kwargs
            assert "host" in call_kwargs
            assert "port" in call_kwargs
            assert "db" in call_kwargs
            assert call_kwargs["decode_responses"] is True

    @pytest.mark.asyncio
    async def test_returns_existing_client_if_already_exists(self):
        """Test that get_redis_client returns the existing client (singleton)."""
        mock_redis = MagicMock()

        with patch("redis.asyncio.Redis", return_value=mock_redis) as mock_redis_class:
            # First call creates client
            client1 = await get_redis_client()
            # Second call should return the same instance
            client2 = await get_redis_client()

            assert client1 is client2
            # Redis should only be instantiated once
            assert mock_redis_class.call_count == 1

    @pytest.mark.asyncio
    async def test_uses_settings_from_config(self):
        """Test that Redis client uses settings from app config."""
        from app.config import settings

        mock_redis = MagicMock()

        with patch("redis.asyncio.Redis", return_value=mock_redis) as mock_redis_class:
            await get_redis_client()

            mock_redis_class.assert_called_once_with(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
            )


class TestCloseRedisClient:
    """Test Redis client cleanup."""

    @pytest.mark.asyncio
    async def test_closes_existing_client(self):
        """Test that close_redis_client closes and clears the client."""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()

        with patch("redis.asyncio.Redis", return_value=mock_redis):
            # Create a client
            await get_redis_client()

            # Close it
            await close_redis_client()

            # Verify close was called
            mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_nothing_if_no_client_exists(self):
        """Test that close_redis_client does nothing if client is None."""
        # This should not raise an exception
        await close_redis_client()

    @pytest.mark.asyncio
    async def test_resets_singleton_after_close(self):
        """Test that closing client allows creating a new one."""
        mock_redis1 = AsyncMock()
        mock_redis1.close = AsyncMock()
        mock_redis2 = AsyncMock()
        mock_redis2.close = AsyncMock()

        with patch("redis.asyncio.Redis", side_effect=[mock_redis1, mock_redis2]):
            # Create first client
            client1 = await get_redis_client()
            assert client1 is mock_redis1

            # Close it
            await close_redis_client()

            # Create new client (should be different instance)
            client2 = await get_redis_client()
            assert client2 is mock_redis2
            assert client1 is not client2
