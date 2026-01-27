# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Cache infrastructure.

Tests for Redis cache wrapper.
"""

from unittest.mock import AsyncMock, MagicMock
import json

import pytest

from app.infrastructure.cache import RedisCache


class TestRedisCache:
    """Tests for RedisCache."""

    @pytest.fixture
    def mock_redis_client(self) -> AsyncMock:
        """Create mock Redis client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def cache(self, mock_redis_client: AsyncMock) -> RedisCache:
        """Create cache with mock client."""
        return RedisCache(client=mock_redis_client)

    @pytest.mark.asyncio
    async def test_get_existing_key(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test getting an existing key."""
        data = {"user_id": "123", "name": "Test"}
        mock_redis_client.get.return_value = json.dumps(data)
        
        result = await cache.get("test_key")
        
        assert result == data
        mock_redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_missing_key(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test getting a non-existent key."""
        mock_redis_client.get.return_value = None
        
        result = await cache.get("missing_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_handles_error(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test get handles Redis errors gracefully."""
        mock_redis_client.get.side_effect = Exception("Connection error")
        
        result = await cache.get("test_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_set_value(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test setting a value."""
        data = {"count": 42}
        
        result = await cache.set("test_key", data)
        
        assert result is True
        mock_redis_client.set.assert_called_once_with("test_key", json.dumps(data))

    @pytest.mark.asyncio
    async def test_set_with_ttl(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test setting a value with TTL."""
        data = {"session": "abc123"}
        ttl = 3600
        
        result = await cache.set("session_key", data, ttl=ttl)
        
        assert result is True
        mock_redis_client.setex.assert_called_once_with("session_key", ttl, json.dumps(data))

    @pytest.mark.asyncio
    async def test_set_handles_error(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test set handles Redis errors gracefully."""
        mock_redis_client.set.side_effect = Exception("Write error")
        
        result = await cache.set("test_key", {"data": "value"})
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_key(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test deleting a key."""
        result = await cache.delete("test_key")
        
        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_handles_error(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test delete handles Redis errors gracefully."""
        mock_redis_client.delete.side_effect = Exception("Delete error")
        
        result = await cache.delete("test_key")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test exists returns True for existing key."""
        mock_redis_client.exists.return_value = 1
        
        result = await cache.exists("existing_key")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test exists returns False for missing key."""
        mock_redis_client.exists.return_value = 0
        
        result = await cache.exists("missing_key")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_handles_error(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test exists handles Redis errors gracefully."""
        mock_redis_client.exists.side_effect = Exception("Connection error")
        
        result = await cache.exists("test_key")
        
        assert result is False


class TestCacheDataTypes:
    """Tests for different data types in cache."""

    @pytest.fixture
    def mock_redis_client(self) -> AsyncMock:
        """Create mock Redis client."""
        return AsyncMock()

    @pytest.fixture
    def cache(self, mock_redis_client: AsyncMock) -> RedisCache:
        """Create cache with mock client."""
        return RedisCache(client=mock_redis_client)

    @pytest.mark.asyncio
    async def test_cache_string(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test caching a string."""
        mock_redis_client.get.return_value = json.dumps("hello")
        
        result = await cache.get("string_key")
        
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_cache_number(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test caching a number."""
        mock_redis_client.get.return_value = json.dumps(42)
        
        result = await cache.get("number_key")
        
        assert result == 42

    @pytest.mark.asyncio
    async def test_cache_list(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test caching a list."""
        data = [1, 2, 3, "four"]
        mock_redis_client.get.return_value = json.dumps(data)
        
        result = await cache.get("list_key")
        
        assert result == data

    @pytest.mark.asyncio
    async def test_cache_nested_dict(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test caching a nested dictionary."""
        data = {
            "user": {
                "id": 123,
                "preferences": {
                    "theme": "dark",
                    "notifications": True,
                },
            }
        }
        mock_redis_client.get.return_value = json.dumps(data)
        
        result = await cache.get("nested_key")
        
        assert result == data
        assert result["user"]["preferences"]["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_cache_null_value(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test caching a null value."""
        mock_redis_client.get.return_value = json.dumps(None)
        
        result = await cache.get("null_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_boolean(
        self, cache: RedisCache, mock_redis_client: AsyncMock
    ) -> None:
        """Test caching boolean values."""
        mock_redis_client.get.return_value = json.dumps(True)
        
        result = await cache.get("bool_key")
        
        assert result is True


class TestCacheService:
    """Tests for advanced CacheService."""

    @pytest.fixture
    def mock_redis_client(self) -> AsyncMock:
        """Create mock Redis client."""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def cache_service(self, mock_redis_client: AsyncMock):
        """Create CacheService with mock client."""
        from app.infrastructure.cache.cache_service import CacheService
        return CacheService(client=mock_redis_client)

    @pytest.mark.asyncio
    async def test_cache_service_get_hit(
        self, cache_service, mock_redis_client: AsyncMock
    ) -> None:
        """Test cache hit increments stats."""
        data = {"id": "123", "name": "Test"}
        mock_redis_client.get.return_value = json.dumps(data)
        
        result = await cache_service.get("test_key")
        
        assert result == data
        stats = cache_service.get_stats()
        assert stats["hits"] == 1

    @pytest.mark.asyncio
    async def test_cache_service_get_miss(
        self, cache_service, mock_redis_client: AsyncMock
    ) -> None:
        """Test cache miss increments stats."""
        mock_redis_client.get.return_value = None
        
        result = await cache_service.get("missing_key")
        
        assert result is None
        stats = cache_service.get_stats()
        assert stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_cache_service_set_with_default_ttl(
        self, cache_service, mock_redis_client: AsyncMock
    ) -> None:
        """Test set uses default TTL from settings."""
        data = {"count": 42}
        
        result = await cache_service.set("test_key", data)
        
        assert result is True
        mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_service_delete_pattern(
        self, cache_service, mock_redis_client: AsyncMock
    ) -> None:
        """Test deleting keys by pattern."""
        # Mock scan_iter to return matching keys
        async def mock_scan_iter(match=None):
            for key in ["fastapi_cache:role:1", "fastapi_cache:role:2"]:
                yield key
        
        mock_redis_client.scan_iter = mock_scan_iter
        mock_redis_client.delete = AsyncMock()
        
        deleted = await cache_service.delete_pattern("role:*")
        
        assert deleted == 2
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_service_get_or_set_cache_hit(
        self, cache_service, mock_redis_client: AsyncMock
    ) -> None:
        """Test get_or_set returns cached value."""
        cached_data = {"cached": True}
        mock_redis_client.get.return_value = json.dumps(cached_data)
        
        factory_called = False
        async def factory():
            nonlocal factory_called
            factory_called = True
            return {"cached": False}
        
        result = await cache_service.get_or_set("key", factory)
        
        assert result == cached_data
        assert not factory_called

    @pytest.mark.asyncio
    async def test_cache_service_get_or_set_cache_miss(
        self, cache_service, mock_redis_client: AsyncMock
    ) -> None:
        """Test get_or_set calls factory on cache miss."""
        mock_redis_client.get.return_value = None
        
        async def factory():
            return {"generated": True}
        
        result = await cache_service.get_or_set("key", factory)
        
        assert result == {"generated": True}
        mock_redis_client.setex.assert_called_once()


class TestCacheKeyBuilder:
    """Tests for CacheKeyBuilder."""

    def test_build_simple_key(self) -> None:
        """Test building a simple cache key."""
        from app.infrastructure.cache.cache_service import CacheKeyBuilder
        
        key = CacheKeyBuilder.build("user", "123")
        
        assert key == "user:123"

    def test_build_key_with_kwargs(self) -> None:
        """Test building a key with keyword arguments."""
        from app.infrastructure.cache.cache_service import CacheKeyBuilder
        from uuid import UUID
        
        tenant_id = UUID("12345678-1234-1234-1234-123456789abc")
        key = CacheKeyBuilder.build("role", "list", tenant_id, skip=0, limit=100)
        
        assert "role:list:" in key
        assert "skip:0" in key
        assert "limit:100" in key

    def test_build_hash_key(self) -> None:
        """Test building a hash-based key for complex data."""
        from app.infrastructure.cache.cache_service import CacheKeyBuilder
        
        data = {"filters": {"active": True, "role": "admin"}}
        key = CacheKeyBuilder.build_hash("query", data)
        
        assert key.startswith("query:hash:")
        assert len(key) > len("query:hash:")
    def test_build_key_with_uuid(self) -> None:
        """Test building key with UUID argument."""
        from app.infrastructure.cache.cache_service import CacheKeyBuilder
        from uuid import UUID
        
        user_id = UUID("12345678-1234-1234-1234-123456789abc")
        key = CacheKeyBuilder.build("user", user_id)
        
        assert "user:12345678-1234-1234-1234-123456789abc" == key

    def test_build_key_with_none_args(self) -> None:
        """Test building key ignores None arguments."""
        from app.infrastructure.cache.cache_service import CacheKeyBuilder
        
        key = CacheKeyBuilder.build("entity", None, "valid")
        
        assert key == "entity:valid"

    def test_build_hash_consistent(self) -> None:
        """Test hash key is consistent for same data."""
        from app.infrastructure.cache.cache_service import CacheKeyBuilder
        
        data = {"a": 1, "b": 2}
        key1 = CacheKeyBuilder.build_hash("prefix", data)
        key2 = CacheKeyBuilder.build_hash("prefix", data)
        
        assert key1 == key2


class TestCacheSerializer:
    """Tests for CacheSerializer."""

    def test_serialize_dict(self) -> None:
        """Test serializing a dictionary."""
        from app.infrastructure.cache.cache_service import CacheSerializer
        
        data = {"key": "value", "number": 42}
        serialized = CacheSerializer.serialize(data)
        
        assert '"key": "value"' in serialized
        assert '"number": 42' in serialized

    def test_deserialize_dict(self) -> None:
        """Test deserializing back to dictionary."""
        from app.infrastructure.cache.cache_service import CacheSerializer
        
        data = {"key": "value"}
        serialized = CacheSerializer.serialize(data)
        deserialized = CacheSerializer.deserialize(serialized)
        
        assert deserialized == data

    def test_serialize_uuid(self) -> None:
        """Test serializing UUID."""
        from app.infrastructure.cache.cache_service import CacheSerializer
        from uuid import UUID
        
        uuid_val = UUID("12345678-1234-1234-1234-123456789abc")
        data = {"id": uuid_val}
        serialized = CacheSerializer.serialize(data)
        
        assert "12345678-1234-1234-1234-123456789abc" in serialized

    def test_serialize_datetime(self) -> None:
        """Test serializing datetime."""
        from app.infrastructure.cache.cache_service import CacheSerializer
        from datetime import datetime, timezone
        
        dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        data = {"timestamp": dt}
        serialized = CacheSerializer.serialize(data)
        
        assert "2025-01-15" in serialized

    def test_serialize_list(self) -> None:
        """Test serializing list."""
        from app.infrastructure.cache.cache_service import CacheSerializer
        
        data = [1, 2, 3, "four"]
        serialized = CacheSerializer.serialize(data)
        deserialized = CacheSerializer.deserialize(serialized)
        
        assert deserialized == data

    def test_serialize_none(self) -> None:
        """Test serializing None."""
        from app.infrastructure.cache.cache_service import CacheSerializer
        
        serialized = CacheSerializer.serialize(None)
        deserialized = CacheSerializer.deserialize(serialized)
        
        assert deserialized is None


class TestCacheServiceTTL:
    """Tests for CacheService TTL constants."""

    def test_ttl_short(self) -> None:
        """Test TTL_SHORT value."""
        from app.infrastructure.cache.cache_service import CacheService
        
        assert CacheService.TTL_SHORT == 60

    def test_ttl_medium(self) -> None:
        """Test TTL_MEDIUM value."""
        from app.infrastructure.cache.cache_service import CacheService
        
        assert CacheService.TTL_MEDIUM == 300

    def test_ttl_long(self) -> None:
        """Test TTL_LONG value."""
        from app.infrastructure.cache.cache_service import CacheService
        
        assert CacheService.TTL_LONG == 3600

    def test_ttl_very_long(self) -> None:
        """Test TTL_VERY_LONG value."""
        from app.infrastructure.cache.cache_service import CacheService
        
        assert CacheService.TTL_VERY_LONG == 86400


class TestCacheServiceDisabled:
    """Tests for CacheService when disabled."""

    @pytest.fixture
    def disabled_cache_service(self):
        """Create CacheService without client (disabled)."""
        from app.infrastructure.cache.cache_service import CacheService
        return CacheService(client=None)

    def test_is_enabled_false_without_client(
        self, disabled_cache_service
    ) -> None:
        """Test is_enabled returns False without client."""
        assert disabled_cache_service.is_enabled is False

    @pytest.mark.asyncio
    async def test_get_returns_none_when_disabled(
        self, disabled_cache_service
    ) -> None:
        """Test get returns None when cache is disabled."""
        result = await disabled_cache_service.get("any_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_returns_false_when_disabled(
        self, disabled_cache_service
    ) -> None:
        """Test set returns False when cache is disabled."""
        result = await disabled_cache_service.set("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_all_returns_false_when_disabled(
        self, disabled_cache_service
    ) -> None:
        """Test clear_all returns False when cache is disabled."""
        result = await disabled_cache_service.clear_all()
        assert result is False


class TestCacheServiceClearAll:
    """Tests for CacheService clear_all method."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        return AsyncMock()

    @pytest.fixture
    def cache_service(self, mock_redis_client):
        """Create CacheService with mock Redis."""
        from app.infrastructure.cache.cache_service import CacheService
        return CacheService(mock_redis_client)

    @pytest.mark.asyncio
    async def test_clear_all_success(
        self, cache_service, mock_redis_client: AsyncMock
    ) -> None:
        """Test clear_all succeeds when delete_pattern works."""
        # Mock scan_iter and delete to simulate delete_pattern behavior
        mock_redis_client.scan_iter.return_value = AsyncIterator(["key1", "key2"])
        mock_redis_client.delete.return_value = 2
        
        result = await cache_service.clear_all()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_clear_all_returns_false_on_error(
        self, cache_service, mock_redis_client: AsyncMock
    ) -> None:
        """Test clear_all returns False when delete_pattern raises error."""
        from unittest.mock import patch
        
        # Patch delete_pattern to raise exception
        with patch.object(cache_service, 'delete_pattern', side_effect=Exception("Redis error")):
            result = await cache_service.clear_all()
        
        assert result is False


class AsyncIterator:
    """Helper async iterator for testing."""
    def __init__(self, items):
        self.items = items
        self.index = 0
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


class TestGetCacheServiceCoverage:
    """Tests for get_cache_service function coverage."""

    @pytest.mark.asyncio
    async def test_get_cache_service_creates_connection(self) -> None:
        """Test get_cache_service creates Redis connection (lines 332-349)."""
        from unittest.mock import patch
        import app.infrastructure.cache.cache_service as cache_module
        
        # Save original
        original = cache_module._cache_service
        cache_module._cache_service = None
        
        try:
            with patch.object(cache_module, 'settings') as mock_settings, \
                 patch.object(cache_module, 'redis') as mock_redis:
                
                mock_settings.CACHE_ENABLED = True
                mock_settings.REDIS_HOST = "localhost"
                mock_settings.REDIS_PORT = 6379
                mock_settings.REDIS_PASSWORD = None
                mock_settings.REDIS_DB = 0
                
                mock_client = AsyncMock()
                mock_client.ping = AsyncMock()
                mock_redis.Redis.return_value = mock_client
                
                result = await cache_module.get_cache_service()
                
                assert result is not None
                mock_client.ping.assert_called_once()
        finally:
            cache_module._cache_service = original

    @pytest.mark.asyncio
    async def test_get_cache_service_handles_redis_error(self) -> None:
        """Test get_cache_service handles Redis connection error (lines 350-353)."""
        from unittest.mock import patch
        import app.infrastructure.cache.cache_service as cache_module
        
        original = cache_module._cache_service
        cache_module._cache_service = None
        
        try:
            with patch.object(cache_module, 'settings') as mock_settings, \
                 patch.object(cache_module, 'redis') as mock_redis:
                
                mock_settings.CACHE_ENABLED = True
                mock_settings.REDIS_HOST = "localhost"
                mock_settings.REDIS_PORT = 6379
                mock_settings.REDIS_PASSWORD = None
                mock_settings.REDIS_DB = 0
                
                mock_client = AsyncMock()
                mock_client.ping = AsyncMock(side_effect=Exception("Connection failed"))
                mock_redis.Redis.return_value = mock_client
                
                result = await cache_module.get_cache_service()
                
                # Should return service with client=None
                assert result is not None
                assert result._client is None
        finally:
            cache_module._cache_service = original


class TestCachedDecoratorCoverage:
    """Tests for cached decorator coverage."""

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_disabled(self) -> None:
        """Test cached decorator when cache is disabled (line 395)."""
        from unittest.mock import patch
        from app.infrastructure.cache.cache_service import cached, CacheService
        
        with patch("app.infrastructure.cache.cache_service.get_cache_service") as mock_get:
            mock_cache = MagicMock(spec=CacheService)
            mock_cache.is_enabled = False  # Cache disabled
            mock_get.return_value = mock_cache
            
            @cached("test")
            async def get_data(id: str) -> dict:
                return {"id": id, "value": "test"}
            
            result = await get_data("123")
            
            assert result == {"id": "123", "value": "test"}

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_hit(self) -> None:
        """Test cached decorator with cache hit (line 402)."""
        from unittest.mock import patch
        from app.infrastructure.cache.cache_service import cached, CacheService
        
        with patch("app.infrastructure.cache.cache_service.get_cache_service") as mock_get:
            mock_cache = MagicMock(spec=CacheService)
            mock_cache.is_enabled = True
            mock_cache.get = AsyncMock(return_value={"cached": True})
            mock_get.return_value = mock_cache
            
            call_count = 0
            
            @cached("test")
            async def get_data(id: str) -> dict:
                nonlocal call_count
                call_count += 1
                return {"id": id}
            
            result = await get_data("123")
            
            assert result == {"cached": True}
            assert call_count == 0  # Function was not called

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_miss(self) -> None:
        """Test cached decorator with cache miss (lines 405-410)."""
        from unittest.mock import patch
        from app.infrastructure.cache.cache_service import cached, CacheService
        
        with patch("app.infrastructure.cache.cache_service.get_cache_service") as mock_get:
            mock_cache = MagicMock(spec=CacheService)
            mock_cache.is_enabled = True
            mock_cache.get = AsyncMock(return_value=None)  # Cache miss
            mock_cache.set = AsyncMock()
            mock_get.return_value = mock_cache
            
            @cached("test", ttl=300)
            async def get_data(id: str) -> dict:
                return {"id": id}
            
            result = await get_data("123")
            
            assert result == {"id": "123"}
            mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_decorator_with_custom_key_builder(self) -> None:
        """Test cached decorator with custom key builder (line 398)."""
        from unittest.mock import patch
        from app.infrastructure.cache.cache_service import cached, CacheService
        
        with patch("app.infrastructure.cache.cache_service.get_cache_service") as mock_get:
            mock_cache = MagicMock(spec=CacheService)
            mock_cache.is_enabled = True
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_get.return_value = mock_cache
            
            custom_key_builder = lambda tenant_id, **kw: f"tenant:{tenant_id}"
            
            @cached("roles", key_builder=custom_key_builder)
            async def get_roles(tenant_id: str) -> list:
                return ["admin", "user"]
            
            result = await get_roles("tenant123")
            
            assert result == ["admin", "user"]