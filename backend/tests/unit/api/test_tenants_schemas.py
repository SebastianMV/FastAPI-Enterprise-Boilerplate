# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for tenant endpoint schemas."""

import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from app.api.v1.schemas.tenants import (
    TenantSettingsSchema,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
    TenantActivateRequest,
    TenantPlanUpdate,
    TenantVerifyRequest,
)


class TestTenantSettingsSchema:
    """Tests for TenantSettingsSchema."""

    def test_settings_defaults(self):
        """Test settings with defaults."""
        settings = TenantSettingsSchema()
        assert settings.enable_2fa is False
        assert settings.enable_api_keys is True
        assert settings.enable_webhooks is False
        assert settings.max_users == 100
        assert settings.max_api_keys_per_user == 5
        assert settings.max_storage_mb == 1024
        assert settings.primary_color == "#3B82F6"
        assert settings.logo_url is None
        assert settings.password_min_length == 8
        assert settings.session_timeout_minutes == 60
        assert settings.require_email_verification is True

    def test_settings_custom_values(self):
        """Test settings with custom values."""
        settings = TenantSettingsSchema(
            enable_2fa=True,
            enable_api_keys=False,
            enable_webhooks=True,
            max_users=500,
            max_api_keys_per_user=20,
            max_storage_mb=5000,
            primary_color="#FF5733",
            logo_url="https://example.com/logo.png",
            password_min_length=12,
            session_timeout_minutes=120,
            require_email_verification=False
        )
        assert settings.enable_2fa is True
        assert settings.max_users == 500
        assert settings.primary_color == "#FF5733"

    def test_settings_max_users_validation(self):
        """Test max_users validation."""
        with pytest.raises(ValidationError):
            TenantSettingsSchema(max_users=0)
        with pytest.raises(ValidationError):
            TenantSettingsSchema(max_users=10001)

    def test_settings_color_validation(self):
        """Test primary_color validation."""
        with pytest.raises(ValidationError):
            TenantSettingsSchema(primary_color="invalid")
        with pytest.raises(ValidationError):
            TenantSettingsSchema(primary_color="FF5733")  # Missing #


class TestTenantCreate:
    """Tests for TenantCreate schema."""

    def test_tenant_create_minimal(self):
        """Test tenant creation with minimal fields."""
        tenant = TenantCreate(name="Acme Corp", slug="acme-corp")
        assert tenant.name == "Acme Corp"
        assert tenant.slug == "acme-corp"
        assert tenant.plan == "free"
        assert tenant.timezone == "UTC"
        assert tenant.locale == "en"

    def test_tenant_create_full(self):
        """Test tenant creation with all fields."""
        settings = TenantSettingsSchema(enable_2fa=True)
        tenant = TenantCreate(
            name="Enterprise Inc",
            slug="enterprise-inc",
            email="admin@enterprise.com",
            phone="+1-555-0100",
            domain="enterprise.com",
            timezone="America/New_York",
            locale="en-US",
            plan="enterprise",
            settings=settings
        )
        assert tenant.email == "admin@enterprise.com"
        assert tenant.plan == "enterprise"
        assert tenant.settings is not None and tenant.settings.enable_2fa is True

    def test_tenant_create_name_validation(self):
        """Test name validation."""
        with pytest.raises(ValidationError):
            TenantCreate(name="A", slug="valid-slug")  # Too short
        with pytest.raises(ValidationError):
            TenantCreate(name="x" * 256, slug="valid-slug")  # Too long

    def test_tenant_create_slug_validation(self):
        """Test slug validation."""
        with pytest.raises(ValidationError):
            TenantCreate(name="Valid Name", slug="a")  # Too short
        with pytest.raises(ValidationError):
            TenantCreate(name="Valid Name", slug="Invalid Slug")  # Spaces
        with pytest.raises(ValidationError):
            TenantCreate(name="Valid Name", slug="UPPERCASE")  # Uppercase

    def test_tenant_create_valid_slugs(self):
        """Test various valid slugs."""
        valid_slugs = ["abc", "my-company", "company-123", "a1b2c3"]
        for slug in valid_slugs:
            tenant = TenantCreate(name="Test", slug=slug)
            assert tenant.slug == slug

    def test_tenant_create_plan_validation(self):
        """Test plan validation."""
        valid_plans = ["free", "starter", "professional", "enterprise"]
        for plan in valid_plans:
            tenant = TenantCreate(name="Test", slug="test-slug", plan=plan)
            assert tenant.plan == plan
        
        with pytest.raises(ValidationError):
            TenantCreate(name="Test", slug="test-slug", plan="invalid")


class TestTenantUpdate:
    """Tests for TenantUpdate schema."""

    def test_tenant_update_empty(self):
        """Test update with no fields."""
        update = TenantUpdate()
        assert update.name is None
        assert update.slug is None
        assert update.email is None

    def test_tenant_update_partial(self):
        """Test update with partial fields."""
        update = TenantUpdate(name="New Name", email="new@email.com")
        assert update.name == "New Name"
        assert update.email == "new@email.com"
        assert update.slug is None

    def test_tenant_update_all_fields(self):
        """Test update with all fields."""
        settings = TenantSettingsSchema(max_users=200)
        update = TenantUpdate(
            name="Updated Corp",
            slug="updated-corp",
            email="contact@updated.com",
            phone="+1-555-0200",
            domain="updated.com",
            timezone="Europe/London",
            locale="en-GB",
            plan="professional",
            settings=settings
        )
        assert update.plan == "professional"
        assert update.settings is not None and update.settings.max_users == 200


class TestTenantResponse:
    """Tests for TenantResponse schema."""

    def test_tenant_response_valid(self):
        """Test valid tenant response."""
        now = datetime.utcnow()
        response = TenantResponse(
            id=uuid4(),
            name="Test Tenant",
            slug="test-tenant",
            email="admin@test.com",
            phone=None,
            is_active=True,
            is_verified=True,
            plan="starter",
            plan_expires_at=None,
            settings=TenantSettingsSchema(),
            domain=None,
            timezone="UTC",
            locale="en",
            created_at=now,
            updated_at=now
        )
        assert response.is_active is True
        assert response.plan == "starter"

    def test_tenant_response_inactive_unverified(self):
        """Test inactive and unverified tenant."""
        now = datetime.utcnow()
        response = TenantResponse(
            id=uuid4(),
            name="Pending Tenant",
            slug="pending",
            is_active=False,
            is_verified=False,
            plan="free",
            settings=TenantSettingsSchema(),
            timezone="UTC",
            locale="en",
            created_at=now,
            updated_at=now
        )
        assert response.is_active is False
        assert response.is_verified is False


class TestTenantListResponse:
    """Tests for TenantListResponse schema."""

    def test_tenant_list_response(self):
        """Test tenant list response."""
        now = datetime.utcnow()
        response = TenantListResponse(
            items=[
                TenantResponse(
                    id=uuid4(),
                    name="Tenant 1",
                    slug="tenant-1",
                    is_active=True,
                    is_verified=True,
                    plan="free",
                    settings=TenantSettingsSchema(),
                    timezone="UTC",
                    locale="en",
                    created_at=now,
                    updated_at=now
                )
            ],
            total=1,
            skip=0,
            limit=20
        )
        assert len(response.items) == 1
        assert response.total == 1

    def test_tenant_list_response_empty(self):
        """Test empty tenant list."""
        response = TenantListResponse(items=[], total=0, skip=0, limit=20)
        assert len(response.items) == 0


class TestTenantActivateRequest:
    """Tests for TenantActivateRequest schema."""

    def test_activate_request(self):
        """Test activate request."""
        request = TenantActivateRequest(is_active=True)
        assert request.is_active is True

    def test_deactivate_request(self):
        """Test deactivate request."""
        request = TenantActivateRequest(is_active=False)
        assert request.is_active is False


class TestTenantPlanUpdate:
    """Tests for TenantPlanUpdate schema."""

    def test_plan_update(self):
        """Test plan update."""
        now = datetime.utcnow()
        update = TenantPlanUpdate(plan="enterprise", expires_at=now)
        assert update.plan == "enterprise"
        assert update.expires_at == now

    def test_plan_update_no_expiry(self):
        """Test plan update without expiry."""
        update = TenantPlanUpdate(plan="professional")
        assert update.plan == "professional"
        assert update.expires_at is None


class TestTenantVerifyRequest:
    """Tests for TenantVerifyRequest schema."""

    def test_verify_request(self):
        """Test verify request."""
        request = TenantVerifyRequest(is_verified=True)
        assert request.is_verified is True
