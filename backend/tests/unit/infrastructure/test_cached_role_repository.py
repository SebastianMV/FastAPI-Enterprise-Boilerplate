# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for CachedRoleRepository."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4

from app.infrastructure.database.repositories.cached_role_repository import (
    CachedRoleRepository,
    get_cached_role_repository,
)
from app.domain.entities.role import Role, Permission


def create_mock_role(
    role_id=None,
    tenant_id=None,
    name="Test Role",
    permissions=None,
):
    """Create a mock Role for testing."""
    return Role(
        id=role_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        name=name,
        description="Test description",
        permissions=permissions or [],
        is_system=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=uuid4(),
    )


class TestCachedRoleRepositoryInit:
    """Tests for CachedRoleRepository initialization."""
    
    def test_init_with_base_repo(self):
        mock_repo = Mock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            
            cached_repo = CachedRoleRepository(mock_repo)
            
            assert cached_repo._repo is mock_repo
            assert cached_repo._ttl == 300
    
    def test_cache_prefix(self):
        assert CachedRoleRepository.CACHE_PREFIX == "role"


class TestCachedRoleRepositoryGetById:
    """Tests for get_by_id method."""
    
    @pytest.mark.asyncio
    async def test_returns_from_cache_on_hit(self):
        mock_repo = Mock()
        role_id = uuid4()
        cached_role = create_mock_role(role_id=role_id)
        
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value={"id": str(role_id)})
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                cached_repo._dict_to_role = Mock(return_value=cached_role)
                result = await cached_repo.get_by_id(role_id)
        
        assert result is not None
        assert result.id == role_id
        mock_repo.get_by_id.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fetches_from_db_on_miss(self):
        mock_repo = Mock()
        role = create_mock_role()
        mock_repo.get_by_id = AsyncMock(return_value=role)
        
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                cached_repo._role_to_dict = Mock(return_value={"id": str(role.id)})
                result = await cached_repo.get_by_id(role.id)
        
        assert result is role
        mock_repo.get_by_id.assert_called_once_with(role.id)
        mock_cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_does_not_cache_none_result(self):
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                result = await cached_repo.get_by_id(uuid4())
        
        assert result is None
        mock_cache.set.assert_not_called()


class TestCachedRoleRepositoryGetByName:
    """Tests for get_by_name method (not cached)."""
    
    @pytest.mark.asyncio
    async def test_delegates_to_base_repo(self):
        mock_repo = Mock()
        role = create_mock_role()
        mock_repo.get_by_name = AsyncMock(return_value=role)
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            
            cached_repo = CachedRoleRepository(mock_repo)
            result = await cached_repo.get_by_name("admin", role.tenant_id)
        
        assert result is role
        mock_repo.get_by_name.assert_called_once_with("admin", role.tenant_id)


class TestCachedRoleRepositoryCreate:
    """Tests for create method."""
    
    @pytest.mark.asyncio
    async def test_creates_and_invalidates_cache(self):
        mock_repo = Mock()
        role = create_mock_role()
        mock_repo.create = AsyncMock(return_value=role)
        
        mock_cache = AsyncMock()
        mock_cache.delete_pattern = AsyncMock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                result = await cached_repo.create(role)
        
        assert result is role
        mock_repo.create.assert_called_once_with(role)


class TestCachedRoleRepositoryUpdate:
    """Tests for update method."""
    
    @pytest.mark.asyncio
    async def test_updates_and_invalidates_cache(self):
        mock_repo = Mock()
        role = create_mock_role()
        mock_repo.update = AsyncMock(return_value=role)
        
        mock_cache = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                result = await cached_repo.update(role)
        
        assert result is role
        mock_repo.update.assert_called_once_with(role)
        mock_cache.delete.assert_called()


class TestCachedRoleRepositoryDelete:
    """Tests for delete method."""
    
    @pytest.mark.asyncio
    async def test_deletes_and_invalidates_cache(self):
        mock_repo = Mock()
        role = create_mock_role()
        mock_repo.get_by_id = AsyncMock(return_value=role)
        mock_repo.delete = AsyncMock()
        
        mock_cache = AsyncMock()
        mock_cache.delete = AsyncMock()
        mock_cache.delete_pattern = AsyncMock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                await cached_repo.delete(role.id)
        
        mock_repo.delete.assert_called_once_with(role.id)
        mock_cache.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_handles_nonexistent_role(self):
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        mock_repo.delete = AsyncMock()
        
        mock_cache = AsyncMock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                await cached_repo.delete(uuid4())
        
        mock_repo.delete.assert_called_once()


class TestCachedRoleRepositoryList:
    """Tests for list method."""
    
    @pytest.mark.asyncio
    async def test_returns_from_cache_on_hit(self):
        mock_repo = Mock()
        tenant_id = uuid4()
        cached_role = create_mock_role(tenant_id=tenant_id)
        
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=[{"id": str(cached_role.id)}])
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                cached_repo._dict_to_role = Mock(return_value=cached_role)
                result = await cached_repo.list(tenant_id=tenant_id)
        
        assert len(result) == 1
        mock_repo.list.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fetches_from_db_on_miss(self):
        mock_repo = Mock()
        role = create_mock_role()
        mock_repo.list = AsyncMock(return_value=[role])
        
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                cached_repo._role_to_dict = Mock(return_value={"id": str(role.id)})
                result = await cached_repo.list(tenant_id=role.tenant_id)
        
        assert len(result) == 1
        mock_cache.set.assert_called_once()


class TestCachedRoleRepositoryListByIds:
    """Tests for list_by_ids method."""
    
    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_ids(self):
        mock_repo = Mock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            
            cached_repo = CachedRoleRepository(mock_repo)
            result = await cached_repo.list_by_ids([])
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_fetches_missing_from_db(self):
        mock_repo = Mock()
        role = create_mock_role()
        mock_repo.list_by_ids = AsyncMock(return_value=[role])
        
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                cached_repo._role_to_dict = Mock(return_value={"id": str(role.id)})
                result = await cached_repo.list_by_ids([role.id])
        
        assert len(result) == 1
        mock_repo.list_by_ids.assert_called_once()


class TestCachedRoleRepositoryGetUserRoles:
    """Tests for get_user_roles method."""
    
    @pytest.mark.asyncio
    async def test_returns_from_cache_on_hit(self):
        mock_repo = Mock()
        user_id = uuid4()
        cached_role = create_mock_role()
        
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=[{"id": str(cached_role.id)}])
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                cached_repo._dict_to_role = Mock(return_value=cached_role)
                result = await cached_repo.get_user_roles(user_id)
        
        assert len(result) == 1
        mock_repo.get_user_roles.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fetches_from_db_on_miss(self):
        mock_repo = Mock()
        role = create_mock_role()
        mock_repo.get_user_roles = AsyncMock(return_value=[role])
        
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            with patch("app.infrastructure.database.repositories.cached_role_repository.get_cache_service", return_value=mock_cache):
                cached_repo = CachedRoleRepository(mock_repo)
                cached_repo._role_to_dict = Mock(return_value={"id": str(role.id)})
                result = await cached_repo.get_user_roles(uuid4())
        
        assert len(result) == 1


class TestCachedRoleRepositorySerialization:
    """Tests for serialization helpers."""
    
    def test_role_to_dict_basic_fields(self):
        role = create_mock_role(name="Test")
        # Add is_deleted attribute for serialization test
        role.is_deleted = False
        role.deleted_at = None
        result = CachedRoleRepository._role_to_dict(role)
        
        assert result["name"] == "Test"
        assert result["id"] == str(role.id)
        assert result["tenant_id"] == str(role.tenant_id)
        assert "permissions" in result
        assert "is_system" in result


class TestGetCachedRoleRepository:
    """Tests for factory function."""
    
    def test_returns_cached_repository(self):
        mock_repo = Mock()
        
        with patch("app.infrastructure.database.repositories.cached_role_repository.settings") as mock_settings:
            mock_settings.CACHE_ROLE_TTL = 300
            
            result = get_cached_role_repository(mock_repo)
        
        assert isinstance(result, CachedRoleRepository)
        assert result._repo is mock_repo
