"""Additional tenant endpoint tests for coverage."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException


class TestUpdateTenantEndpoint:
    """Tests for update tenant endpoint."""

    @pytest.fixture
    def mock_repo(self):
        """Create mock tenant repository."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock()
        repo.slug_exists = AsyncMock()
        repo.domain_exists = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_tenant(self):
        """Create mock tenant entity."""
        from app.domain.entities.tenant import TenantSettings

        tenant = MagicMock()
        tenant.id = uuid4()
        tenant.name = "Test Tenant"
        tenant.slug = "test-tenant"
        tenant.domain = "test.example.com"
        tenant.email = "admin@test.example.com"
        tenant.phone = "+1234567890"
        tenant.is_active = True
        tenant.is_verified = True
        tenant.plan = "professional"
        tenant.plan_expires_at = None
        tenant.timezone = "UTC"
        tenant.locale = "en"
        tenant.created_at = datetime.now(UTC)
        tenant.updated_at = datetime.now(UTC)
        tenant.settings = TenantSettings(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=True,
            max_users=100,
            max_api_keys_per_user=10,
            max_storage_mb=10000,
        )
        tenant.mark_updated = MagicMock()
        return tenant

    @pytest.mark.asyncio
    async def test_update_tenant_not_found(self, mock_repo):
        """Test updating non-existent tenant."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate

        tenant_id = uuid4()
        mock_repo.get_by_id.return_value = None

        data = TenantUpdate(name="Updated Tenant")

        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=tenant_id,
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc.value.status_code == 404
        assert "Tenant not found" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_slug_conflict(self, mock_repo, mock_tenant):
        """Test updating tenant with conflicting slug."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate

        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.slug_exists.return_value = True

        data = TenantUpdate(slug="existing-slug")

        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=mock_tenant.id,
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_domain_conflict(self, mock_repo, mock_tenant):
        """Test updating tenant with conflicting domain."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate

        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.slug_exists.return_value = False
        mock_repo.domain_exists.return_value = True

        data = TenantUpdate(domain="existing.example.com")

        with pytest.raises(HTTPException) as exc:
            await update_tenant(
                tenant_id=mock_tenant.id,
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc.value.status_code == 409
        assert "already exists" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_tenant_success(self, mock_repo, mock_tenant):
        """Test successful tenant update."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantUpdate

        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.slug_exists.return_value = False
        mock_repo.domain_exists.return_value = False
        mock_repo.update.return_value = mock_tenant

        data = TenantUpdate(
            name="Updated Tenant",
            email="updated@example.com",
            phone="+9876543210",
        )

        result = await update_tenant(
            tenant_id=mock_tenant.id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )

        assert result.id == mock_tenant.id
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tenant_with_settings(self, mock_repo, mock_tenant):
        """Test updating tenant settings."""
        from app.api.v1.endpoints.tenants import update_tenant
        from app.api.v1.schemas.tenants import TenantSettingsSchema, TenantUpdate

        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant

        settings = TenantSettingsSchema(
            enable_2fa=False,
            enable_api_keys=False,
            enable_webhooks=False,
            max_users=50,
            max_api_keys_per_user=5,
            max_storage_mb=5000,
        )

        data = TenantUpdate(settings=settings)

        result = await update_tenant(
            tenant_id=mock_tenant.id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )

        assert result is not None
        mock_repo.update.assert_called_once()


class TestUpdateTenantPlanEndpoint:
    """Tests for update tenant plan endpoint."""

    @pytest.fixture
    def mock_repo(self):
        """Create mock tenant repository."""
        repo = MagicMock()
        repo.get_by_id = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_tenant(self):
        """Create mock tenant entity."""
        from app.domain.entities.tenant import TenantSettings

        tenant = MagicMock()
        tenant.id = uuid4()
        tenant.name = "Test Tenant"
        tenant.slug = "test-tenant"
        tenant.domain = None
        tenant.email = "admin@test.example.com"
        tenant.phone = None
        tenant.is_active = True
        tenant.is_verified = True
        tenant.plan = "basic"
        tenant.plan_expires_at = None
        tenant.timezone = "UTC"
        tenant.locale = "en"
        tenant.created_at = datetime.now(UTC)
        tenant.updated_at = datetime.now(UTC)
        tenant.settings = TenantSettings(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=True,
            max_users=100,
            max_api_keys_per_user=10,
            max_storage_mb=10000,
        )
        tenant.update_plan = MagicMock()
        tenant.mark_updated = MagicMock()
        return tenant

    @pytest.mark.asyncio
    async def test_update_tenant_plan_not_found(self, mock_repo):
        """Test updating plan for non-existent tenant."""
        from app.api.v1.endpoints.tenants import update_tenant_plan
        from app.api.v1.schemas.tenants import TenantPlanUpdate

        tenant_id = uuid4()
        mock_repo.get_by_id.return_value = None

        data = TenantPlanUpdate(plan="enterprise")

        with pytest.raises(HTTPException) as exc:
            await update_tenant_plan(
                tenant_id=tenant_id,
                data=data,
                current_user_id=uuid4(),
                repo=mock_repo,
            )

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_tenant_plan_success(self, mock_repo, mock_tenant):
        """Test successful plan update."""
        from app.api.v1.endpoints.tenants import update_tenant_plan
        from app.api.v1.schemas.tenants import TenantPlanUpdate

        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant

        data = TenantPlanUpdate(plan="enterprise")

        result = await update_tenant_plan(
            tenant_id=mock_tenant.id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )

        assert result is not None
        mock_tenant.update_plan.assert_called_once()
        mock_tenant.mark_updated.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_tenant_plan_with_expiry(self, mock_repo, mock_tenant):
        """Test plan update with expiry date."""
        from app.api.v1.endpoints.tenants import update_tenant_plan
        from app.api.v1.schemas.tenants import TenantPlanUpdate

        mock_repo.get_by_id.return_value = mock_tenant
        mock_repo.update.return_value = mock_tenant

        expires_at = datetime.now(UTC)
        data = TenantPlanUpdate(plan="professional", expires_at=expires_at)

        result = await update_tenant_plan(
            tenant_id=mock_tenant.id,
            data=data,
            current_user_id=uuid4(),
            repo=mock_repo,
        )

        assert result is not None
        mock_tenant.update_plan.assert_called_with("professional", expires_at)


class TestTenantResponseHelper:
    """Tests for tenant response helper function."""

    def test_to_response_helper(self):
        """Test _to_response helper function."""
        from app.api.v1.endpoints.tenants import _to_response
        from app.domain.entities.tenant import Tenant, TenantSettings

        tenant = Tenant(
            id=uuid4(),
            name="Test Tenant",
            slug="test-tenant",
            email="admin@test.example.com",
            is_active=True,
            is_verified=True,
            plan="basic",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            settings=TenantSettings(
                enable_2fa=True,
                enable_api_keys=True,
                enable_webhooks=True,
                max_users=100,
                max_api_keys_per_user=10,
                max_storage_mb=10000,
            ),
        )

        response = _to_response(tenant)

        assert response.id == tenant.id
        assert response.name == "Test Tenant"
        assert response.slug == "test-tenant"
        assert response.is_active is True


class TestTenantSchemas:
    """Tests for tenant schemas."""

    def test_tenant_update_minimal(self):
        """Test TenantUpdate with minimal data."""
        from app.api.v1.schemas.tenants import TenantUpdate

        update = TenantUpdate()

        assert update.name is None
        assert update.slug is None
        assert update.domain is None

    def test_tenant_update_full(self):
        """Test TenantUpdate with all fields."""
        from app.api.v1.schemas.tenants import TenantSettingsSchema, TenantUpdate

        settings = TenantSettingsSchema(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=True,
            max_users=100,
            max_api_keys_per_user=10,
            max_storage_mb=10000,
        )

        update = TenantUpdate(
            name="Updated Name",
            slug="updated-slug",
            domain="updated.example.com",
            email="updated@example.com",
            phone="+1234567890",
            timezone="America/New_York",
            locale="en-US",
            plan="enterprise",
            settings=settings,
        )

        assert update.name == "Updated Name"
        assert update.slug == "updated-slug"
        assert update.settings is not None and update.settings.max_users == 100

    def test_tenant_plan_update(self):
        """Test TenantPlanUpdate schema."""
        from app.api.v1.schemas.tenants import TenantPlanUpdate

        update = TenantPlanUpdate(plan="professional")

        assert update.plan == "professional"
        assert update.expires_at is None

    def test_tenant_settings_schema(self):
        """Test TenantSettingsSchema."""
        from app.api.v1.schemas.tenants import TenantSettingsSchema

        settings = TenantSettingsSchema(
            enable_2fa=True,
            enable_api_keys=True,
            enable_webhooks=False,
            max_users=50,
            max_api_keys_per_user=5,
            max_storage_mb=5000,
            primary_color="#FF0000",
            logo_url="https://example.com/logo.png",
            password_min_length=12,
        )

        assert settings.enable_2fa is True
        assert settings.enable_webhooks is False
        assert settings.max_users == 50
        assert settings.primary_color == "#FF0000"
