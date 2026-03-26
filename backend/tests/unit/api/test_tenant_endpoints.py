# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for tenant endpoints module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.api.v1.schemas.tenants import (
    TenantActivateRequest,
    TenantCreate,
    TenantListResponse,
    TenantPlanUpdate,
    TenantResponse,
    TenantSettingsSchema,
    TenantUpdate,
    TenantVerifyRequest,
)


def create_mock_settings() -> MagicMock:
    """Create a mock settings object with all required attributes."""
    settings = MagicMock()
    settings.enable_2fa = False
    settings.enable_api_keys = True
    settings.enable_webhooks = False
    settings.max_users = 100
    settings.max_api_keys_per_user = 5
    settings.max_storage_mb = 1024
    settings.primary_color = "#3B82F6"
    settings.logo_url = None
    settings.password_min_length = 8
    settings.session_timeout_minutes = 60
    settings.require_email_verification = True
    return settings


def create_mock_tenant(tenant_id: UUID | None = None) -> MagicMock:
    """Create a mock tenant with all required attributes."""
    if tenant_id is None:
        tenant_id = uuid4()
    mock_tenant = MagicMock()
    mock_tenant.id = tenant_id
    mock_tenant.name = "Test Tenant"
    mock_tenant.slug = "test-tenant"
    mock_tenant.email = None
    mock_tenant.phone = None
    mock_tenant.domain = None
    mock_tenant.timezone = "UTC"
    mock_tenant.locale = "en"
    mock_tenant.is_active = True
    mock_tenant.is_verified = False
    mock_tenant.plan = "free"
    mock_tenant.plan_expires_at = None
    mock_tenant.settings = create_mock_settings()
    mock_tenant.created_at = datetime.now(UTC)
    mock_tenant.updated_at = datetime.now(UTC)
    return mock_tenant


class TestTenantCreateSchema:
    """Tests for TenantCreate schema."""

    def test_tenant_create_minimal(self) -> None:
        """Test tenant create with minimal fields."""
        data = TenantCreate(
            name="Test Tenant",
            slug="test-tenant",
        )
        assert data.name == "Test Tenant"
        assert data.slug == "test-tenant"
        assert data.email is None
        assert data.plan == "free"

    def test_tenant_create_full(self) -> None:
        """Test tenant create with all fields."""
        data = TenantCreate(
            name="Full Tenant",
            slug="full-tenant",
            email="admin@example.com",
            phone="+1234567890",
            domain="example.com",
            timezone="America/New_York",
            locale="en-US",
            plan="enterprise",
        )
        assert data.name == "Full Tenant"
        assert data.domain == "example.com"
        assert data.plan == "enterprise"

    def test_tenant_create_with_settings(self) -> None:
        """Test tenant create with settings."""
        settings = TenantSettingsSchema(
            enable_2fa=True,
            max_users=100,
            max_api_keys_per_user=10,
        )
        data = TenantCreate(
            name="Tenant With Settings",
            slug="settings-tenant",
            settings=settings,
        )
        assert data.settings is not None
        assert data.settings.enable_2fa is True
        assert data.settings.max_users == 100


class TestTenantUpdateSchema:
    """Tests for TenantUpdate schema."""

    def test_tenant_update_partial(self) -> None:
        """Test partial tenant update."""
        data = TenantUpdate(name="Updated Name")
        assert data.name == "Updated Name"
        assert data.slug is None
        assert data.email is None

    def test_tenant_update_full(self) -> None:
        """Test full tenant update."""
        data = TenantUpdate(
            name="Updated",
            slug="updated-slug",
            email="new@example.com",
            domain="new.example.com",
            plan="professional",
        )
        assert data.name == "Updated"
        assert data.slug == "updated-slug"
        assert data.plan == "professional"


class TestTenantResponseSchema:
    """Tests for TenantResponse schema."""

    def test_tenant_response_creation(self) -> None:
        """Test tenant response creation."""
        from datetime import datetime

        tenant_id = uuid4()
        response = TenantResponse(
            id=tenant_id,
            name="Test Tenant",
            slug="test-tenant",
            is_active=True,
            is_verified=False,
            plan="free",
            settings=TenantSettingsSchema(),
            timezone="UTC",
            locale="en",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert response.id == tenant_id
        assert response.name == "Test Tenant"
        assert response.is_active is True


class TestTenantListResponseSchema:
    """Tests for TenantListResponse schema."""

    def test_tenant_list_response(self) -> None:
        """Test tenant list response."""
        from datetime import datetime

        items = [
            TenantResponse(
                id=uuid4(),
                name=f"Tenant {i}",
                slug=f"tenant-{i}",
                is_active=True,
                is_verified=False,
                plan="free",
                settings=TenantSettingsSchema(),
                timezone="UTC",
                locale="en",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            for i in range(3)
        ]
        response = TenantListResponse(
            items=items,
            total=10,
            page=1,
            page_size=20,
            pages=1,
        )
        assert len(response.items) == 3
        assert response.total == 10

    def test_tenant_list_response_empty(self) -> None:
        """Test empty tenant list."""
        response = TenantListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            pages=0,
        )
        assert len(response.items) == 0
        assert response.total == 0


class TestTenantActivateRequest:
    """Tests for TenantActivateRequest schema."""

    def test_activate_request_true(self) -> None:
        """Test activation request."""
        data = TenantActivateRequest(is_active=True)
        assert data.is_active is True

    def test_activate_request_false(self) -> None:
        """Test deactivation request."""
        data = TenantActivateRequest(is_active=False)
        assert data.is_active is False


class TestTenantVerifyRequest:
    """Tests for TenantVerifyRequest schema."""

    def test_verify_request_true(self) -> None:
        """Test verification request."""
        data = TenantVerifyRequest(is_verified=True)
        assert data.is_verified is True


class TestTenantPlanUpdate:
    """Tests for TenantPlanUpdate schema."""

    def test_plan_update_free(self) -> None:
        """Test plan update to free."""
        data = TenantPlanUpdate(plan="free")
        assert data.plan == "free"

    def test_plan_update_pro(self) -> None:
        """Test plan update to professional."""
        data = TenantPlanUpdate(plan="professional")
        assert data.plan == "professional"

    def test_plan_update_enterprise(self) -> None:
        """Test plan update to enterprise."""
        data = TenantPlanUpdate(plan="enterprise")
        assert data.plan == "enterprise"


class TestTenantSettingsSchema:
    """Tests for TenantSettingsSchema."""

    def test_settings_defaults(self) -> None:
        """Test settings with defaults."""
        settings = TenantSettingsSchema()
        assert settings.enable_2fa is False
        assert settings.enable_api_keys is True
        assert settings.enable_webhooks is False
        assert settings.max_users == 100

    def test_settings_custom(self) -> None:
        """Test settings with custom values."""
        settings = TenantSettingsSchema(
            enable_2fa=True,
            enable_api_keys=False,
            max_users=500,
            max_storage_mb=10000,
            primary_color="#FF5733",
        )
        assert settings.enable_2fa is True
        assert settings.enable_api_keys is False
        assert settings.max_users == 500
        assert settings.max_storage_mb == 10000
        assert settings.primary_color == "#FF5733"


class TestListTenantsEndpoint:
    """Tests for list tenants endpoint."""

    @pytest.mark.asyncio
    async def test_list_tenants_success(self) -> None:
        """Test listing tenants successfully."""
        from app.api.v1.endpoints.tenants import list_tenants

        mock_tenant = create_mock_tenant()

        mock_repo = AsyncMock()
        mock_repo.list_all.return_value = [mock_tenant]
        mock_repo.count.return_value = 1

        result = await list_tenants(
            skip=0,
            limit=20,
            is_active=None,
            _=uuid4(),
            repo=mock_repo,
        )

        assert result.total == 1
        assert len(result.items) == 1
        mock_repo.list_all.assert_called_once()


class TestCreateTenantEndpoint:
    """Tests for create tenant endpoint."""

    @pytest.mark.asyncio
    async def test_create_tenant_success(self) -> None:
        """Test creating tenant successfully."""
        from app.api.v1.endpoints.tenants import create_tenant

        mock_created = create_mock_tenant()
        mock_created.name = "New Tenant"
        mock_created.slug = "new-tenant"

        mock_repo = AsyncMock()
        mock_repo.slug_exists.return_value = False
        mock_repo.domain_exists.return_value = False
        mock_repo.create.return_value = mock_created

        data = TenantCreate(name="New Tenant", slug="new-tenant")

        result = await create_tenant(
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )

        assert result.name == "New Tenant"
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_tenant_slug_conflict(self) -> None:
        """Test creating tenant with existing slug."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tenants import create_tenant

        mock_repo = AsyncMock()
        mock_repo.slug_exists.return_value = True

        data = TenantCreate(name="Test", slug="existing-slug")

        with pytest.raises(HTTPException) as exc_info:
            await create_tenant(
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 409
        assert "already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_tenant_domain_conflict(self) -> None:
        """Test creating tenant with existing domain."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tenants import create_tenant

        mock_repo = AsyncMock()
        mock_repo.slug_exists.return_value = False
        mock_repo.domain_exists.return_value = True

        data = TenantCreate(
            name="Test",
            slug="new-slug",
            domain="existing.com",
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_tenant(
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 409


class TestGetTenantEndpoint:
    """Tests for get tenant endpoint."""

    @pytest.mark.asyncio
    async def test_get_tenant_success(self) -> None:
        """Test getting tenant by ID."""
        from app.api.v1.endpoints.tenants import get_tenant

        tenant_id = uuid4()
        mock_tenant = create_mock_tenant(tenant_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant

        result = await get_tenant(
            tenant_id=tenant_id,
            _=uuid4(),
            repo=mock_repo,
        )

        assert result.id == tenant_id
        mock_repo.get_by_id.assert_called_once_with(tenant_id)

    @pytest.mark.asyncio
    async def test_get_tenant_not_found(self) -> None:
        """Test getting non-existent tenant."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tenants import get_tenant

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_tenant(
                tenant_id=uuid4(),
                _=uuid4(),
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 404


class TestGetTenantBySlugEndpoint:
    """Tests for get tenant by slug endpoint."""

    @pytest.mark.asyncio
    async def test_get_tenant_by_slug_success(self) -> None:
        """Test getting tenant by slug."""
        from app.api.v1.endpoints.tenants import get_tenant_by_slug

        mock_tenant = create_mock_tenant()
        mock_tenant.slug = "test-slug"

        mock_repo = AsyncMock()
        mock_repo.get_by_slug.return_value = mock_tenant

        result = await get_tenant_by_slug(
            slug="test-slug",
            _=uuid4(),
            repo=mock_repo,
        )

        assert result.slug == "test-slug"

    @pytest.mark.asyncio
    async def test_get_tenant_by_slug_not_found(self) -> None:
        """Test getting non-existent tenant by slug."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tenants import get_tenant_by_slug

        mock_repo = AsyncMock()
        mock_repo.get_by_slug.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_by_slug(
                slug="nonexistent",
                _=uuid4(),
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 404


class TestUpdateTenantEndpoint:
    """Tests for update tenant endpoint."""

    @pytest.mark.asyncio
    async def test_update_tenant_success(self) -> None:
        """Test updating tenant."""
        from app.api.v1.endpoints.tenants import update_tenant

        tenant_id = uuid4()
        mock_tenant = create_mock_tenant(tenant_id)
        mock_tenant.name = "Original"
        mock_tenant.slug = "original-slug"

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant

        data = TenantUpdate(name="Updated")

        result = await update_tenant(
            tenant_id=tenant_id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )

        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tenant_not_found(self) -> None:
        """Test updating non-existent tenant."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tenants import update_tenant

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        data = TenantUpdate(name="Updated")

        with pytest.raises(HTTPException) as exc_info:
            await update_tenant(
                tenant_id=uuid4(),
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 404


class TestDeleteTenantEndpoint:
    """Tests for delete tenant endpoint."""

    @pytest.mark.asyncio
    async def test_delete_tenant_success(self) -> None:
        """Test deleting tenant."""
        from app.api.v1.endpoints.tenants import delete_tenant

        mock_repo = AsyncMock()
        mock_repo.delete.return_value = True

        result = await delete_tenant(
            tenant_id=uuid4(),
            _=uuid4(),
            repo=mock_repo,
        )

        assert result is None
        mock_repo.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_tenant_not_found(self) -> None:
        """Test deleting non-existent tenant."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tenants import delete_tenant

        mock_repo = AsyncMock()
        mock_repo.delete.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_tenant(
                tenant_id=uuid4(),
                _=uuid4(),
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 404


class TestSetTenantActiveEndpoint:
    """Tests for activate/deactivate tenant endpoint."""

    @pytest.mark.asyncio
    async def test_activate_tenant(self) -> None:
        """Test activating a tenant."""
        from app.api.v1.endpoints.tenants import set_tenant_active

        tenant_id = uuid4()
        mock_tenant = create_mock_tenant(tenant_id)
        mock_tenant.is_active = False

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant

        data = TenantActivateRequest(is_active=True)

        result = await set_tenant_active(
            tenant_id=tenant_id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )

        mock_tenant.activate.assert_called_once()
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_deactivate_tenant(self) -> None:
        """Test deactivating a tenant."""
        from app.api.v1.endpoints.tenants import set_tenant_active

        tenant_id = uuid4()
        mock_tenant = create_mock_tenant(tenant_id)
        mock_tenant.is_active = True

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant

        data = TenantActivateRequest(is_active=False)

        result = await set_tenant_active(
            tenant_id=tenant_id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )

        mock_tenant.deactivate.assert_called_once()


class TestSetTenantVerifiedEndpoint:
    """Tests for verify tenant endpoint."""

    @pytest.mark.asyncio
    async def test_verify_tenant(self) -> None:
        """Test verifying a tenant."""
        from app.api.v1.endpoints.tenants import set_tenant_verified

        tenant_id = uuid4()
        mock_tenant = create_mock_tenant(tenant_id)
        mock_tenant.is_verified = False

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant

        data = TenantVerifyRequest(is_verified=True)

        result = await set_tenant_verified(
            tenant_id=tenant_id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )

        mock_tenant.verify.assert_called_once()
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_tenant_not_found(self) -> None:
        """Test verifying non-existent tenant."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tenants import set_tenant_verified

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        data = TenantVerifyRequest(is_verified=True)

        with pytest.raises(HTTPException) as exc_info:
            await set_tenant_verified(
                tenant_id=uuid4(),
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 404
