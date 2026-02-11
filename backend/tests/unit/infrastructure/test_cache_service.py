# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for cache service."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.infrastructure.cache.cache_service import (
    CacheKeyBuilder,
    CacheSerializer,
    CacheService,
)


class TestCacheKeyBuilder:
    """Tests for CacheKeyBuilder."""

    def test_build_with_prefix_only(self):
        key = CacheKeyBuilder.build("users")
        assert key == "users"

    def test_build_with_positional_args(self):
        key = CacheKeyBuilder.build("user", "123", "456")
        assert key == "user:123:456"

    def test_build_with_uuid(self):
        uid = uuid4()
        key = CacheKeyBuilder.build("user", uid)
        assert key == f"user:{uid}"

    def test_build_ignores_none_args(self):
        key = CacheKeyBuilder.build("user", "123", None, "456")
        assert key == "user:123:456"

    def test_build_with_kwargs(self):
        key = CacheKeyBuilder.build("user", page=1, size=10)
        assert key == "user:page:1:size:10"

    def test_build_kwargs_sorted(self):
        key = CacheKeyBuilder.build("items", z="last", a="first")
        assert key == "items:a:first:z:last"

    def test_build_ignores_none_kwargs(self):
        key = CacheKeyBuilder.build("user", active=True, deleted=None)
        assert key == "user:active:True"

    def test_build_with_uuid_kwargs(self):
        uid = uuid4()
        key = CacheKeyBuilder.build("role", tenant_id=uid)
        assert key == f"role:tenant_id:{uid}"

    def test_build_hash_returns_hash_key(self):
        data = {"query": "test", "filters": [1, 2, 3]}
        key = CacheKeyBuilder.build_hash("search", data)
        assert key.startswith("search:hash:")
        assert len(key.split(":")[-1]) == 12

    def test_build_hash_consistent_for_same_data(self):
        data = {"a": 1, "b": 2}
        key1 = CacheKeyBuilder.build_hash("test", data)
        key2 = CacheKeyBuilder.build_hash("test", data)
        assert key1 == key2

    def test_build_hash_different_for_different_data(self):
        key1 = CacheKeyBuilder.build_hash("test", {"a": 1})
        key2 = CacheKeyBuilder.build_hash("test", {"a": 2})
        assert key1 != key2


class TestCacheSerializer:
    """Tests for CacheSerializer."""

    def test_serialize_dict(self):
        data = {"key": "value", "num": 123}
        result = CacheSerializer.serialize(data)
        assert isinstance(result, str)
        assert json.loads(result) == data

    def test_serialize_list(self):
        data = [1, 2, 3, "four"]
        result = CacheSerializer.serialize(data)
        assert json.loads(result) == data

    def test_serialize_uuid(self):
        uid = uuid4()
        result = CacheSerializer.serialize({"id": uid})
        parsed = json.loads(result)
        assert parsed["id"] == str(uid)

    def test_serialize_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = CacheSerializer.serialize({"created": dt})
        parsed = json.loads(result)
        assert parsed["created"] == dt.isoformat()

    def test_serialize_pydantic_model(self):
        mock_model = Mock()
        mock_model.model_dump = Mock(return_value={"name": "test"})
        result = CacheSerializer.serialize(mock_model)
        assert json.loads(result) == {"name": "test"}

    def test_serialize_object_with_dict(self):
        class SimpleObj:
            def __init__(self):
                self.value = 42

        obj = SimpleObj()
        result = CacheSerializer.serialize(obj)
        parsed = json.loads(result)
        assert parsed["value"] == 42

    def test_serialize_raises_for_unknown_type(self):
        class UnknownType:
            __slots__ = ()

        with pytest.raises(TypeError):
            CacheSerializer.serialize(UnknownType())

    def test_deserialize_dict(self):
        data = '{"key": "value"}'
        result = CacheSerializer.deserialize(data)
        assert result == {"key": "value"}

    def test_deserialize_list(self):
        data = "[1, 2, 3]"
        result = CacheSerializer.deserialize(data)
        assert result == [1, 2, 3]


class TestCacheService:
    """Tests for CacheService."""

    def test_init_without_client(self):
        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=None)
            assert service._client is None
            assert service.is_enabled is False

    def test_init_with_client(self):
        mock_client = Mock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "myapp"

            service = CacheService(client=mock_client)
            assert service._client is mock_client

    def test_is_enabled_when_disabled(self):
        mock_client = Mock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = False
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            assert service.is_enabled is False

    def test_is_enabled_when_enabled_with_client(self):
        mock_client = Mock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            assert service.is_enabled is True

    def test_make_key_adds_prefix(self):
        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "app"

            service = CacheService(client=Mock())
            key = service._make_key("user:123")
            assert key == "app:user:123"

    @pytest.mark.asyncio
    async def test_get_returns_none_when_disabled(self):
        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = False
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=None)
            result = await service.get("test_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_cached_value(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value='{"data": "test"}')

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.get("my_key")

            assert result == {"data": "test"}
            assert service._stats["hits"] == 1

    @pytest.mark.asyncio
    async def test_get_returns_none_on_miss(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.get("missing_key")

            assert result is None
            assert service._stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_get_handles_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Redis error"))

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.get("error_key")

            assert result is None
            assert service._stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_set_returns_false_when_disabled(self):
        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = False
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=None)
            result = await service.set("key", "value")
            assert result is False

    @pytest.mark.asyncio
    async def test_set_stores_value(self):
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"
            mock_settings.CACHE_DEFAULT_TTL = 300

            service = CacheService(client=mock_client)
            result = await service.set("my_key", {"data": "value"})

            assert result is True
            mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self):
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"
            mock_settings.CACHE_DEFAULT_TTL = 300

            service = CacheService(client=mock_client)
            await service.set("my_key", "value", ttl=60)

            call_args = mock_client.setex.call_args
            assert call_args[0][1] == 60  # TTL argument

    @pytest.mark.asyncio
    async def test_set_handles_error(self):
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(side_effect=Exception("Redis error"))

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"
            mock_settings.CACHE_DEFAULT_TTL = 300

            service = CacheService(client=mock_client)
            result = await service.set("key", "value")

            assert result is False
            assert service._stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_disabled(self):
        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = False
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=None)
            result = await service.delete("key")
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_removes_key(self):
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.delete("my_key")

            assert result is True
            mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_handles_error(self):
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(side_effect=Exception("Redis error"))

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.delete("key")

            assert result is False
            assert service._stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_delete_pattern_returns_zero_when_disabled(self):
        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = False
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=None)
            result = await service.delete_pattern("user:*")
            assert result == 0

    @pytest.mark.asyncio
    async def test_delete_pattern_deletes_matching_keys(self):
        mock_client = AsyncMock()

        async def mock_scan_iter(match):
            for key in [b"key1", b"key2", b"key3"]:
                yield key

        mock_client.scan_iter = mock_scan_iter
        mock_client.delete = AsyncMock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.delete_pattern("user:*")

            assert result == 3
            mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_pattern_returns_zero_when_no_matches(self):
        mock_client = AsyncMock()

        async def mock_scan_iter(match):
            return
            yield  # Empty generator

        mock_client.scan_iter = mock_scan_iter

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.delete_pattern("nonexistent:*")

            assert result == 0

    @pytest.mark.asyncio
    async def test_delete_pattern_handles_error(self):
        mock_client = AsyncMock()

        async def mock_scan_iter(match):
            raise Exception("Redis error")
            yield  # pragma: no cover

        mock_client.scan_iter = mock_scan_iter

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.delete_pattern("pattern:*")

            assert result == 0
            assert service._stats["errors"] == 1


class TestCacheServiceTTLConstants:
    """Tests for CacheService TTL constants."""

    def test_ttl_short(self):
        assert CacheService.TTL_SHORT == 60

    def test_ttl_medium(self):
        assert CacheService.TTL_MEDIUM == 300

    def test_ttl_long(self):
        assert CacheService.TTL_LONG == 3600

    def test_ttl_very_long(self):
        assert CacheService.TTL_VERY_LONG == 86400


class TestCacheServiceExists:
    """Tests for CacheService.exists method."""

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_disabled(self):
        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = False
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=None)
            result = await service.exists("key")
            assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_key_exists(self):
        mock_client = AsyncMock()
        mock_client.exists = AsyncMock(return_value=1)

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.exists("my_key")

            assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_key_missing(self):
        mock_client = AsyncMock()
        mock_client.exists = AsyncMock(return_value=0)

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.exists("missing_key")

            assert result is False

    @pytest.mark.asyncio
    async def test_exists_handles_error(self):
        mock_client = AsyncMock()
        mock_client.exists = AsyncMock(side_effect=Exception("Redis error"))

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.exists("key")

            assert result is False
            assert service._stats["errors"] == 1


class TestCacheServiceGetOrSet:
    """Tests for CacheService.get_or_set method."""

    @pytest.mark.asyncio
    async def test_get_or_set_returns_cached_value(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value='{"data": "cached"}')

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)

            factory = AsyncMock(return_value={"data": "computed"})
            result = await service.get_or_set("key", factory)

            assert result == {"data": "cached"}
            factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_set_computes_on_miss(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.setex = AsyncMock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"
            mock_settings.CACHE_DEFAULT_TTL = 300

            service = CacheService(client=mock_client)

            factory = AsyncMock(return_value={"data": "computed"})
            result = await service.get_or_set("key", factory)

            assert result == {"data": "computed"}
            factory.assert_called_once()
            mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_set_with_sync_factory(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.setex = AsyncMock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"
            mock_settings.CACHE_DEFAULT_TTL = 300

            service = CacheService(client=mock_client)

            def sync_factory():
                return {"data": "sync"}

            result = await service.get_or_set("key", sync_factory)

            assert result == {"data": "sync"}


class TestCacheServiceStats:
    """Tests for CacheService.get_stats method."""

    def test_get_stats_returns_copy(self):
        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=Mock())
            service._stats = {"hits": 10, "misses": 5, "errors": 1}

            stats = service.get_stats()

            assert stats == {"hits": 10, "misses": 5, "errors": 1}
            # Ensure it's a copy
            stats["hits"] = 100
            assert service._stats["hits"] == 10


class TestCacheServiceClearAll:
    """Tests for CacheService.clear_all method."""

    @pytest.mark.asyncio
    async def test_clear_all_returns_false_when_disabled(self):
        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = False
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=None)
            result = await service.clear_all()
            assert result is False

    @pytest.mark.asyncio
    async def test_clear_all_deletes_all_keys(self):
        mock_client = AsyncMock()

        async def mock_scan_iter(match):
            for key in [b"key1", b"key2"]:
                yield key

        mock_client.scan_iter = mock_scan_iter
        mock_client.delete = AsyncMock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            service = CacheService(client=mock_client)
            result = await service.clear_all()

            assert result is True


class TestCachedDecorator:
    """Tests for @cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator_returns_cached_value(self):
        from app.infrastructure.cache.cache_service import (
            CacheService,
            cached,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value='{"result": "cached"}')

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            mock_service = CacheService(client=mock_client)

            with patch(
                "app.infrastructure.cache.cache_service.get_cache_service",
                return_value=mock_service,
            ):

                @cached("users")
                async def get_user(user_id: str):
                    return {"result": "fresh"}

                result = await get_user("123")
                assert result == {"result": "cached"}

    @pytest.mark.asyncio
    async def test_cached_decorator_computes_on_miss(self):
        from app.infrastructure.cache.cache_service import CacheService, cached

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        mock_client.setex = AsyncMock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"
            mock_settings.CACHE_DEFAULT_TTL = 300

            mock_service = CacheService(client=mock_client)

            with patch(
                "app.infrastructure.cache.cache_service.get_cache_service",
                return_value=mock_service,
            ):
                call_count = 0

                @cached("users", ttl=60)
                async def get_user(user_id: str):
                    nonlocal call_count
                    call_count += 1
                    return {"result": "fresh"}

                result = await get_user("123")

                assert result == {"result": "fresh"}
                assert call_count == 1
                mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_decorator_bypasses_when_disabled(self):
        from app.infrastructure.cache.cache_service import CacheService, cached

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = False
            mock_settings.CACHE_PREFIX = "test"

            mock_service = CacheService(client=None)

            with patch(
                "app.infrastructure.cache.cache_service.get_cache_service",
                return_value=mock_service,
            ):

                @cached("users")
                async def get_user(user_id: str):
                    return {"result": "computed"}

                result = await get_user("123")
                assert result == {"result": "computed"}


class TestInvalidateCacheDecorator:
    """Tests for @invalidate_cache decorator."""

    @pytest.mark.asyncio
    async def test_invalidate_cache_decorator(self):
        from app.infrastructure.cache.cache_service import (
            CacheService,
            invalidate_cache,
        )

        mock_client = AsyncMock()

        async def mock_scan_iter(match):
            for key in [b"key1"]:
                yield key

        mock_client.scan_iter = mock_scan_iter
        mock_client.delete = AsyncMock()

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = True
            mock_settings.CACHE_PREFIX = "test"

            mock_service = CacheService(client=mock_client)

            with patch(
                "app.infrastructure.cache.cache_service.get_cache_service",
                return_value=mock_service,
            ):

                @invalidate_cache("user:*")
                async def update_user(user_id: str, data: dict):
                    return {"updated": True}

                result = await update_user("123", {"name": "New Name"})

                assert result == {"updated": True}
                mock_client.delete.assert_called()

    @pytest.mark.asyncio
    async def test_invalidate_cache_skips_when_disabled(self):
        from app.infrastructure.cache.cache_service import (
            CacheService,
            invalidate_cache,
        )

        with patch("app.infrastructure.cache.cache_service.settings") as mock_settings:
            mock_settings.CACHE_ENABLED = False
            mock_settings.CACHE_PREFIX = "test"

            mock_service = CacheService(client=None)

            with patch(
                "app.infrastructure.cache.cache_service.get_cache_service",
                return_value=mock_service,
            ):

                @invalidate_cache("user:*")
                async def update_user(user_id: str):
                    return {"updated": True}

                result = await update_user("123")
                assert result == {"updated": True}
