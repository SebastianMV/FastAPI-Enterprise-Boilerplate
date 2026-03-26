# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for Tenants API endpoints.

Tests for tenant management CRUD operations.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


class TestListTenantsEndpoint:
    """Tests for /tenants (list) endpoint."""

    @pytest.mark.asyncio
    async def test_list_tenants_success(self) -> None:
        """Test listing tenants successfully."""
        from app.api.v1.endpoints.tenants import list_tenants

        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.name = "Test Tenant"
        mock_tenant.slug = "test-tenant"
        mock_tenant.email = "contact@testtenant.com"
        mock_tenant.phone = None
        mock_tenant.domain = None
        mock_tenant.is_active = True
        mock_tenant.is_verified = False
        mock_tenant.plan = "free"
        mock_tenant.timezone = "UTC"
        mock_tenant.locale = "en"
        mock_tenant.settings = MagicMock()
        mock_tenant.settings.enable_2fa = False
        mock_tenant.settings.enable_api_keys = True
        mock_tenant.settings.enable_webhooks = False
        mock_tenant.settings.max_users = 10
        mock_tenant.settings.max_api_keys_per_user = 5
        mock_tenant.settings.max_storage_mb = 1000
        mock_tenant.settings.primary_color = "#000000"
        mock_tenant.settings.logo_url = None
        mock_tenant.settings.password_min_length = 8
        mock_tenant.settings.session_timeout_minutes = 60
        mock_tenant.settings.require_email_verification = True
        mock_tenant.created_at = datetime.now(UTC)
        mock_tenant.updated_at = datetime.now(UTC)

        mock_repo = AsyncMock()
        mock_repo.list_all.return_value = [mock_tenant]
        mock_repo.count.return_value = 1

        result = await list_tenants(
            skip=0,
            limit=20,
            is_active=None,
            _=uuid4(),  # superuser id
            repo=mock_repo,
        )

        assert result.total == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_list_tenants_empty(self) -> None:
        """Test listing tenants when none exist."""
        from app.api.v1.endpoints.tenants import list_tenants

        mock_repo = AsyncMock()
        mock_repo.list_all.return_value = []
        mock_repo.count.return_value = 0

        result = await list_tenants(
            skip=0,
            limit=20,
            is_active=None,
            _=uuid4(),
            repo=mock_repo,
        )

        assert result.total == 0
        assert result.items == []

    @pytest.mark.asyncio
    async def test_list_tenants_with_filter(self) -> None:
        """Test listing tenants with active filter."""
        from app.api.v1.endpoints.tenants import list_tenants

        mock_repo = AsyncMock()
        mock_repo.list_all.return_value = []
        mock_repo.count.return_value = 0

        await list_tenants(
            skip=0,
            limit=20,
            is_active=True,
            _=uuid4(),
            repo=mock_repo,
        )

        mock_repo.list_all.assert_awaited_once_with(skip=0, limit=20, is_active=True)


class TestCreateTenantEndpoint:
    """Tests for /tenants (create) endpoint."""

    @pytest.mark.asyncio
    async def test_create_tenant_slug_exists(self) -> None:
        """Test creating tenant with existing slug."""
        from app.api.v1.endpoints.tenants import create_tenant
        from app.api.v1.schemas.tenants import TenantCreate

        request = TenantCreate(
            name="Test Tenant",
            slug="existing-slug",
        )

        mock_repo = AsyncMock()
        mock_repo.slug_exists.return_value = True

        with pytest.raises(HTTPException) as exc_info:
            await create_tenant(
                data=request,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 409
        assert "already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_tenant_domain_exists(self) -> None:
        """Test creating tenant with existing domain."""
        from app.api.v1.endpoints.tenants import create_tenant
        from app.api.v1.schemas.tenants import TenantCreate

        request = TenantCreate(
            name="Test Tenant",
            slug="new-slug",
            domain="existing.domain.com",
        )

        mock_repo = AsyncMock()
        mock_repo.slug_exists.return_value = False
        mock_repo.domain_exists.return_value = True

        with pytest.raises(HTTPException) as exc_info:
            await create_tenant(
                data=request,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 409
        assert "domain" in str(exc_info.value.detail).lower()


class TestGetTenantRepository:
    """Tests for get_tenant_repository dependency."""

    def test_get_tenant_repository_returns_cached_repo(self) -> None:
        """Test that get_tenant_repository returns a CachedTenantRepository."""
        from app.api.v1.endpoints.tenants import get_tenant_repository

        mock_session = MagicMock()

        with (
            patch(
                "app.api.v1.endpoints.tenants.SQLAlchemyTenantRepository"
            ) as mock_base_repo,
            patch(
                "app.api.v1.endpoints.tenants.get_cached_tenant_repository"
            ) as mock_get_cached,
        ):
            mock_cached_repo = MagicMock()
            mock_get_cached.return_value = mock_cached_repo

            result = get_tenant_repository(session=mock_session)

            mock_base_repo.assert_called_once_with(mock_session)
            assert result == mock_cached_repo


class TestTenantSchemas:
    """Tests for tenant schemas."""

    def test_tenant_create_valid(self) -> None:
        """Test valid TenantCreate schema."""
        from app.api.v1.schemas.tenants import TenantCreate

        tenant = TenantCreate(
            name="Test Organization",
            slug="test-org",
            email="contact@testorg.com",
        )

        assert tenant.name == "Test Organization"
        assert tenant.slug == "test-org"

    def test_tenant_create_minimal(self) -> None:
        """Test TenantCreate with minimal data."""
        from app.api.v1.schemas.tenants import TenantCreate

        tenant = TenantCreate(
            name="Minimal Tenant",
            slug="minimal",
        )

        assert tenant.name == "Minimal Tenant"
        assert tenant.email is None

    def test_tenant_update_valid(self) -> None:
        """Test valid TenantUpdate schema."""
        from app.api.v1.schemas.tenants import TenantUpdate

        update = TenantUpdate(
            name="Updated Name",
            email="new@email.com",
        )

        assert update.name == "Updated Name"

    def test_tenant_response_schema(self) -> None:
        """Test TenantResponse schema."""
        from app.api.v1.schemas.tenants import TenantResponse, TenantSettingsSchema

        response = TenantResponse(
            id=uuid4(),
            name="Test Tenant",
            slug="test-tenant",
            email="test@tenant.com",
            phone=None,
            domain=None,
            is_active=True,
            is_verified=False,
            plan="free",
            timezone="UTC",
            locale="en",
            settings=TenantSettingsSchema(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert response.name == "Test Tenant"
        assert response.is_active is True

    def test_tenant_list_response(self) -> None:
        """Test TenantListResponse schema."""
        from app.api.v1.schemas.tenants import (
            TenantListResponse,
            TenantResponse,
            TenantSettingsSchema,
        )

        response = TenantListResponse(
            items=[
                TenantResponse(
                    id=uuid4(),
                    name="Test",
                    slug="test",
                    email=None,
                    phone=None,
                    domain=None,
                    is_active=True,
                    is_verified=False,
                    plan="free",
                    timezone="UTC",
                    locale="en",
                    settings=TenantSettingsSchema(),
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
            total=1,
            page=1,
            page_size=20,
            pages=1,
        )

        assert len(response.items) == 1
        assert response.total == 1

    def test_tenant_settings_schema(self) -> None:
        """Test TenantSettingsSchema defaults."""
        from app.api.v1.schemas.tenants import TenantSettingsSchema

        settings = TenantSettingsSchema()

        assert settings.enable_2fa is False
        assert settings.enable_api_keys is True
        assert settings.max_users == 100

    def test_tenant_plan_update(self) -> None:
        """Test TenantPlanUpdate schema."""
        from app.api.v1.schemas.tenants import TenantPlanUpdate

        update = TenantPlanUpdate(
            plan="enterprise",
        )

        assert update.plan == "enterprise"

    def test_tenant_activate_request(self) -> None:
        """Test TenantActivateRequest schema."""
        from app.api.v1.schemas.tenants import TenantActivateRequest

        request = TenantActivateRequest(
            is_active=True,
        )

        assert request.is_active is True

    def test_tenant_verify_request(self) -> None:
        """Test TenantVerifyRequest schema."""
        from app.api.v1.schemas.tenants import TenantVerifyRequest

        request = TenantVerifyRequest(
            is_verified=True,
        )

        assert request.is_verified is True
