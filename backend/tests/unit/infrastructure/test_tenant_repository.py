# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for SQLAlchemy Tenant Repository implementation."""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
from app.domain.entities.tenant import Tenant, TenantSettings


def create_mock_tenant(
    tenant_id=None,
    name="Test Tenant",
    slug="test-tenant",
    is_active=True,
):
    """Create a mock Tenant entity for testing."""
    return Tenant(
        id=tenant_id or uuid4(),
        name=name,
        slug=slug,
        email="tenant@example.com",
        phone=None,
        is_active=is_active,
        is_verified=True,
        plan="basic",
        plan_expires_at=None,
        settings=TenantSettings(),
        domain=None,
        timezone="UTC",
        locale="en",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by=uuid4(),
    )


def create_mock_tenant_model(
    tenant_id=None,
    name="Test Tenant",
    slug="test-tenant",
    is_active=True,
    domain=None,
):
    """Create a mock TenantModel for testing."""
    mock = MagicMock()
    mock.id = tenant_id or uuid4()
    mock.name = name
    mock.slug = slug
    mock.email = "tenant@example.com"
    mock.phone = None
    mock.is_active = is_active
    mock.is_verified = True
    mock.plan = "basic"
    mock.plan_expires_at = None
    mock.settings = {}
    mock.domain = domain
    mock.timezone = "UTC"
    mock.locale = "en"
    mock.created_at = datetime.now(UTC)
    mock.updated_at = datetime.now(UTC)
    mock.created_by = uuid4()
    mock.updated_by = None
    mock.is_deleted = False
    mock.deleted_at = None
    mock.deleted_by = None
    return mock


class TestSQLAlchemyTenantRepositoryInit:
    """Tests for SQLAlchemyTenantRepository initialization."""

    def test_init_with_session(self):
        """Test initialization with session."""
        session = AsyncMock()
        repo = SQLAlchemyTenantRepository(session=session)
        
        assert repo.session is session


class TestSQLAlchemyTenantRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        """Test getting tenant by ID when found."""
        session = AsyncMock()
        tenant_id = uuid4()
        mock_model = create_mock_tenant_model(tenant_id=tenant_id)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.get_by_id(tenant_id)
        
        assert result is not None
        assert result.id == tenant_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test getting tenant by ID when not found."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.get_by_id(uuid4())
        
        assert result is None


class TestSQLAlchemyTenantRepositoryGetBySlug:
    """Tests for get_by_slug method."""

    @pytest.mark.asyncio
    async def test_get_by_slug_found(self):
        """Test getting tenant by slug when found."""
        session = AsyncMock()
        mock_model = create_mock_tenant_model(slug="my-tenant")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.get_by_slug("my-tenant")
        
        assert result is not None
        assert result.slug == "my-tenant"

    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(self):
        """Test getting tenant by slug when not found."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.get_by_slug("nonexistent")
        
        assert result is None


class TestSQLAlchemyTenantRepositoryGetByDomain:
    """Tests for get_by_domain method."""

    @pytest.mark.asyncio
    async def test_get_by_domain_found(self):
        """Test getting tenant by domain when found."""
        session = AsyncMock()
        mock_model = create_mock_tenant_model(domain="example.com")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.get_by_domain("example.com")
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_by_domain_not_found(self):
        """Test getting tenant by domain when not found."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.get_by_domain("nonexistent.com")
        
        assert result is None


class TestSQLAlchemyTenantRepositoryCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful tenant creation."""
        session = AsyncMock()
        tenant = create_mock_tenant()
        
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        
        repo = SQLAlchemyTenantRepository(session=session)
        
        with patch.object(repo, '_to_entity', return_value=tenant):
            result = await repo.create(tenant)
        
        assert result is not None
        session.add.assert_called_once()
        session.flush.assert_called_once()


class TestSQLAlchemyTenantRepositoryUpdate:
    """Tests for update method."""

    @pytest.mark.asyncio
    async def test_update_success(self):
        """Test successful tenant update."""
        session = AsyncMock()
        tenant_id = uuid4()
        tenant = create_mock_tenant(tenant_id=tenant_id)
        mock_model = create_mock_tenant_model(tenant_id=tenant_id)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        
        repo = SQLAlchemyTenantRepository(session=session)
        
        with patch.object(repo, '_to_entity', return_value=tenant):
            result = await repo.update(tenant)
        
        assert result is not None
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """Test update when tenant not found."""
        session = AsyncMock()
        tenant = create_mock_tenant()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        
        with pytest.raises(ValueError):
            await repo.update(tenant)


class TestSQLAlchemyTenantRepositoryDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """Test successful tenant deletion."""
        session = AsyncMock()
        tenant_id = uuid4()
        mock_model = create_mock_tenant_model(tenant_id=tenant_id)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        
        repo = SQLAlchemyTenantRepository(session=session)
        
        result = await repo.delete(tenant_id)
        
        assert result is True
        session.delete.assert_called_once_with(mock_model)
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """Test delete when tenant not found."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        
        result = await repo.delete(uuid4())
        
        assert result is False


class TestSQLAlchemyTenantRepositoryListAll:
    """Tests for list_all method."""

    @pytest.mark.asyncio
    async def test_list_all_tenants(self):
        """Test listing all tenants."""
        session = AsyncMock()
        mock_model1 = create_mock_tenant_model()
        mock_model2 = create_mock_tenant_model()
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_model1, mock_model2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.list_all()
        
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_all_with_pagination(self):
        """Test listing tenants with pagination."""
        session = AsyncMock()
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.list_all(skip=10, limit=5)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_list_all_active_only(self):
        """Test listing only active tenants."""
        session = AsyncMock()
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.list_all(is_active=True)
        
        assert result == []


class TestSQLAlchemyTenantRepositoryCount:
    """Tests for count method."""

    @pytest.mark.asyncio
    async def test_count_all_tenants(self):
        """Test counting all tenants."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.count()
        
        assert result == 42

    @pytest.mark.asyncio
    async def test_count_active_tenants(self):
        """Test counting active tenants only."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.count(is_active=True)
        
        assert result == 10

    @pytest.mark.asyncio
    async def test_count_returns_zero_for_null(self):
        """Test count returns 0 when scalar is None."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.count()
        
        assert result == 0


class TestSQLAlchemyTenantRepositorySlugExists:
    """Tests for slug_exists method."""

    @pytest.mark.asyncio
    async def test_slug_exists_true(self):
        """Test slug_exists when slug exists."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.slug_exists("existing-slug")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_slug_exists_false(self):
        """Test slug_exists when slug doesn't exist."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.slug_exists("nonexistent")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_slug_exists_with_exclude_id(self):
        """Test slug_exists excluding specific tenant ID."""
        session = AsyncMock()
        exclude_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.slug_exists("my-slug", exclude_id=exclude_id)
        
        assert result is False


class TestSQLAlchemyTenantRepositoryDomainExists:
    """Tests for domain_exists method."""

    @pytest.mark.asyncio
    async def test_domain_exists_true(self):
        """Test domain_exists when domain exists."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.domain_exists("example.com")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_domain_exists_false(self):
        """Test domain_exists when domain doesn't exist."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.domain_exists("nonexistent.com")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_domain_exists_with_exclude_id(self):
        """Test domain_exists excluding specific tenant ID."""
        session = AsyncMock()
        exclude_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.domain_exists("example.com", exclude_id=exclude_id)
        
        assert result is False


class TestSQLAlchemyTenantRepositoryGetDefaultTenant:
    """Tests for get_default_tenant method."""

    @pytest.mark.asyncio
    async def test_get_default_tenant_found_by_slug(self):
        """Test getting default tenant found by 'default' slug."""
        session = AsyncMock()
        mock_model = create_mock_tenant_model(slug="default")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.get_default_tenant()
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_default_tenant_fallback_to_first_active(self):
        """Test getting default tenant falls back to first active."""
        session = AsyncMock()
        mock_model = create_mock_tenant_model(slug="first-active")
        
        # First call returns None (no 'default' slug)
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None
        
        # Second call returns first active tenant
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_model
        
        session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.get_default_tenant()
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_default_tenant_not_found(self):
        """Test getting default tenant when none available."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyTenantRepository(session=session)
        result = await repo.get_default_tenant()
        
        assert result is None


class TestSQLAlchemyTenantRepositoryConversion:
    """Tests for entity/model conversion methods."""

    def test_to_entity_conversion(self):
        """Test converting model to entity."""
        session = AsyncMock()
        repo = SQLAlchemyTenantRepository(session=session)
        
        mock_model = create_mock_tenant_model()
        
        entity = repo._to_entity(mock_model)
        
        assert entity.id == mock_model.id
        assert entity.name == mock_model.name
        assert entity.slug == mock_model.slug
        assert entity.is_active == mock_model.is_active

    def test_to_entity_with_null_settings(self):
        """Test converting model with null settings."""
        session = AsyncMock()
        repo = SQLAlchemyTenantRepository(session=session)
        
        mock_model = create_mock_tenant_model()
        mock_model.settings = None
        
        entity = repo._to_entity(mock_model)
        
        assert entity.settings is not None  # Should use default TenantSettings

    def test_to_model_conversion(self):
        """Test converting entity to model."""
        session = AsyncMock()
        repo = SQLAlchemyTenantRepository(session=session)
        
        tenant = create_mock_tenant()
        
        model = repo._to_model(tenant)
        
        assert model.id == tenant.id
        assert model.name == tenant.name
        assert model.slug == tenant.slug
        assert model.is_active == tenant.is_active
