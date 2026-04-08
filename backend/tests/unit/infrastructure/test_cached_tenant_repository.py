# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Unit tests for CachedTenantRepository."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.domain.entities.tenant import Tenant, TenantSettings
from app.infrastructure.database.repositories.cached_tenant_repository import (
    CachedTenantRepository,
    get_cached_tenant_repository,
)


def create_mock_tenant(
    tenant_id=None,
    name="Test Tenant",
    slug="test-tenant",
):
    """Create a mock Tenant for testing."""
    return Tenant(
        id=tenant_id or uuid4(),
        name=name,
        slug=slug,
        email="test@example.com",
        is_active=True,
        is_verified=True,
        plan="pro",
        settings=TenantSettings(),
        timezone="UTC",
        locale="en",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=uuid4(),
        is_deleted=False,
    )


class TestCachedTenantRepositoryInit:
    """Tests for CachedTenantRepository initialization."""

    def test_init_with_base_repo(self):
        mock_repo = Mock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600

            cached_repo = CachedTenantRepository(mock_repo)

            assert cached_repo._repo is mock_repo
            assert cached_repo._ttl == 3600

    def test_cache_prefix(self):
        assert CachedTenantRepository.CACHE_PREFIX == "tenant"


class TestCachedTenantRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_returns_from_cache_on_hit(self):
        mock_repo = Mock()
        tenant_id = uuid4()

        cached_data = {
            "id": str(tenant_id),
            "name": "Cached Tenant",
            "slug": "cached",
            "email": "cached@test.com",
            "is_active": True,
            "is_verified": True,
            "plan": "pro",
            "settings": {},
            "timezone": "UTC",
            "locale": "en",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_deleted": False,
        }

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=cached_data)

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                result = await cached_repo.get_by_id(tenant_id)

        assert result is not None
        assert result.name == "Cached Tenant"
        mock_repo.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetches_from_db_on_miss(self):
        mock_repo = Mock()
        tenant = create_mock_tenant()
        mock_repo.get_by_id = AsyncMock(return_value=tenant)

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                result = await cached_repo.get_by_id(tenant.id)

        assert result is tenant
        mock_repo.get_by_id.assert_called_once_with(tenant.id)
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_cache_none(self):
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                result = await cached_repo.get_by_id(uuid4())

        assert result is None
        mock_cache.set.assert_not_called()


class TestCachedTenantRepositoryGetBySlug:
    """Tests for get_by_slug method."""

    @pytest.mark.asyncio
    async def test_returns_from_cache_on_hit(self):
        mock_repo = Mock()
        tenant_id = uuid4()

        cached_data = {
            "id": str(tenant_id),
            "name": "Cached Tenant",
            "slug": "cached-slug",
            "email": "cached@test.com",
            "is_active": True,
            "is_verified": True,
            "plan": "pro",
            "settings": {},
            "timezone": "UTC",
            "locale": "en",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_deleted": False,
        }

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=cached_data)

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                result = await cached_repo.get_by_slug("cached-slug")

        assert result is not None
        assert result.slug == "cached-slug"

    @pytest.mark.asyncio
    async def test_caches_by_slug_and_id(self):
        mock_repo = Mock()
        tenant = create_mock_tenant()
        mock_repo.get_by_slug = AsyncMock(return_value=tenant)

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                await cached_repo.get_by_slug(tenant.slug)

        # Should cache by both slug and ID
        assert mock_cache.set.call_count == 2


class TestCachedTenantRepositoryGetByDomain:
    """Tests for get_by_domain method."""

    @pytest.mark.asyncio
    async def test_returns_from_cache_on_hit(self):
        mock_repo = Mock()
        tenant_id = uuid4()

        cached_data = {
            "id": str(tenant_id),
            "name": "Domain Tenant",
            "slug": "domain",
            "email": "domain@test.com",
            "domain": "custom.example.com",
            "is_active": True,
            "is_verified": True,
            "plan": "pro",
            "settings": {},
            "timezone": "UTC",
            "locale": "en",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_deleted": False,
        }

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=cached_data)

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                result = await cached_repo.get_by_domain("custom.example.com")

        assert result is not None
        mock_repo.get_by_domain.assert_not_called()

    @pytest.mark.asyncio
    async def test_caches_by_domain_and_id(self):
        mock_repo = Mock()
        tenant = create_mock_tenant()
        tenant.domain = "custom.example.com"
        mock_repo.get_by_domain = AsyncMock(return_value=tenant)

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                await cached_repo.get_by_domain("custom.example.com")

        assert mock_cache.set.call_count == 2


class TestCachedTenantRepositoryCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_creates_without_invalidation(self):
        mock_repo = Mock()
        tenant = create_mock_tenant()
        mock_repo.create = AsyncMock(return_value=tenant)

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600

            cached_repo = CachedTenantRepository(mock_repo)
            result = await cached_repo.create(tenant)

        assert result is tenant
        mock_repo.create.assert_called_once_with(tenant)


class TestCachedTenantRepositoryUpdate:
    """Tests for update method."""

    @pytest.mark.asyncio
    async def test_updates_and_invalidates_cache(self):
        mock_repo = Mock()
        tenant = create_mock_tenant()
        mock_repo.update = AsyncMock(return_value=tenant)

        mock_cache = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                result = await cached_repo.update(tenant)

        assert result is tenant
        mock_repo.update.assert_called_once_with(tenant)
        mock_cache.delete.assert_called()


class TestCachedTenantRepositoryDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_deletes_and_invalidates_cache(self):
        mock_repo = Mock()
        tenant = create_mock_tenant()
        mock_repo.get_by_id = AsyncMock(return_value=tenant)
        mock_repo.delete = AsyncMock(return_value=True)

        mock_cache = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                result = await cached_repo.delete(tenant.id)

        assert result is True
        mock_cache.delete.assert_called()

    @pytest.mark.asyncio
    async def test_handles_nonexistent_tenant(self):
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        mock_repo.delete = AsyncMock(return_value=False)

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600

            cached_repo = CachedTenantRepository(mock_repo)
            result = await cached_repo.delete(uuid4())

        assert result is False


class TestCachedTenantRepositoryListAll:
    """Tests for list_all method."""

    @pytest.mark.asyncio
    async def test_returns_from_cache_on_hit(self):
        mock_repo = Mock()
        tenant_id = uuid4()

        cached_data = [
            {
                "id": str(tenant_id),
                "name": "Cached Tenant",
                "slug": "cached",
                "email": "cached@test.com",
                "is_active": True,
                "is_verified": True,
                "plan": "pro",
                "settings": {},
                "timezone": "UTC",
                "locale": "en",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "is_deleted": False,
            }
        ]

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=cached_data)

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                result = await cached_repo.list_all()

        assert len(result) == 1
        mock_repo.list_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetches_from_db_on_miss(self):
        mock_repo = Mock()
        tenant = create_mock_tenant()
        mock_repo.list_all = AsyncMock(return_value=[tenant])

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                result = await cached_repo.list_all()

        assert len(result) == 1
        mock_cache.set.assert_called_once()


class TestCachedTenantRepositoryDelegatedMethods:
    """Tests for methods delegated to base repo without caching."""

    @pytest.mark.asyncio
    async def test_count_delegates(self):
        mock_repo = Mock()
        mock_repo.count = AsyncMock(return_value=5)

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600

            cached_repo = CachedTenantRepository(mock_repo)
            result = await cached_repo.count()

        assert result == 5
        mock_repo.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_slug_exists_delegates(self):
        mock_repo = Mock()
        mock_repo.slug_exists = AsyncMock(return_value=True)

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600

            cached_repo = CachedTenantRepository(mock_repo)
            result = await cached_repo.slug_exists("test-slug")

        assert result is True

    @pytest.mark.asyncio
    async def test_domain_exists_delegates(self):
        mock_repo = Mock()
        mock_repo.domain_exists = AsyncMock(return_value=False)

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600

            cached_repo = CachedTenantRepository(mock_repo)
            result = await cached_repo.domain_exists("example.com")

        assert result is False


class TestCachedTenantRepositorySerialization:
    """Tests for serialization helpers."""

    def test_tenant_to_dict(self):
        tenant = create_mock_tenant(name="Serialize Test")
        tenant.domain = "custom.example.com"
        result = CachedTenantRepository._tenant_to_dict(tenant)

        assert result["name"] == "Serialize Test"
        assert result["slug"] == "test-tenant"
        assert result["domain"] == "custom.example.com"

    def test_dict_to_tenant(self):
        tenant_id = uuid4()
        data = {
            "id": str(tenant_id),
            "name": "From Dict",
            "slug": "from-dict",
            "email": "dict@test.com",
            "is_active": True,
            "is_verified": False,
            "plan": "enterprise",
            "settings": {},
            "timezone": "America/New_York",
            "locale": "es",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_deleted": False,
        }

        result = CachedTenantRepository._dict_to_tenant(data)

        assert result.id == tenant_id
        assert result.name == "From Dict"
        assert result.plan == "enterprise"
        assert result.locale == "es"


class TestCachedTenantRepositoryInvalidation:
    """Tests for cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidates_domain_when_present(self):
        mock_repo = Mock()
        tenant = create_mock_tenant()
        tenant.domain = "custom.example.com"
        mock_repo.update = AsyncMock(return_value=tenant)

        mock_cache = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600
            with patch(
                "app.infrastructure.database.repositories.cached_tenant_repository.get_cache_service",
                return_value=mock_cache,
            ):
                cached_repo = CachedTenantRepository(mock_repo)
                await cached_repo.update(tenant)

        # Should delete id, slug, domain keys + pattern
        assert mock_cache.delete.call_count >= 3


class TestGetCachedTenantRepository:
    """Tests for factory function."""

    def test_returns_cached_repository(self):
        mock_repo = Mock()

        with patch(
            "app.infrastructure.database.repositories.cached_tenant_repository.settings"
        ) as mock_settings:
            mock_settings.CACHE_TENANT_TTL = 3600

            result = get_cached_tenant_repository(mock_repo)

        assert isinstance(result, CachedTenantRepository)
        assert result._repo is mock_repo
