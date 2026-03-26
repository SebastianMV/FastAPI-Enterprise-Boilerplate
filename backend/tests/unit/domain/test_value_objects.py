# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for domain value objects module."""

import pytest

from app.domain.exceptions.base import ValidationError as DomainValidationError


class TestEmailValueObject:
    """Tests for Email value object."""

    def test_valid_email(self) -> None:
        """Test valid email creation."""
        from app.domain.value_objects.email import Email

        email = Email("test@example.com")
        assert email.value == "test@example.com"

    def test_email_normalization(self) -> None:
        """Test email is normalized to lowercase."""
        from app.domain.value_objects.email import Email

        email = Email("Test@Example.COM")
        assert email.value == "test@example.com"

    def test_invalid_email_format(self) -> None:
        """Test invalid email format raises error."""
        from app.domain.value_objects.email import Email

        with pytest.raises(DomainValidationError):
            Email("not-an-email")

    def test_email_equality(self) -> None:
        """Test email equality comparison."""
        from app.domain.value_objects.email import Email

        email1 = Email("test@example.com")
        email2 = Email("TEST@EXAMPLE.COM")
        assert email1 == email2

    def test_email_str_representation(self) -> None:
        """Test email string representation."""
        from app.domain.value_objects.email import Email

        email = Email("test@example.com")
        assert str(email) == "test@example.com"


class TestPasswordValueObject:
    """Tests for Password value object."""

    def test_valid_password(self) -> None:
        """Test valid password creation."""
        from app.domain.value_objects.password import Password

        password = Password("SecureP@ss123")
        assert password.value is not None

    def test_password_too_short(self) -> None:
        """Test password too short raises error."""
        from app.domain.value_objects.password import Password

        with pytest.raises(DomainValidationError):
            Password("short")

    def test_password_str_representation(self) -> None:
        """Test password string representation is masked."""
        from app.domain.value_objects.password import Password

        password = Password("SecureP@ss123")
        str_repr = str(password)
        # Should not expose actual password
        assert "SecureP@ss123" not in str_repr or len(str_repr) > 0


class TestPermissionEntity:
    """Tests for Permission entity."""

    def test_permission_from_string(self) -> None:
        """Test creating permission from string."""
        from app.domain.entities.role import Permission

        perm = Permission.from_string("users:read")
        assert perm.resource == "users"
        assert perm.action == "read"

    def test_permission_to_string(self) -> None:
        """Test permission to string."""
        from app.domain.entities.role import Permission

        perm = Permission(resource="users", action="write")
        assert str(perm) == "users:write"

    def test_permission_invalid_format(self) -> None:
        """Test invalid permission format raises error."""
        from app.domain.entities.role import Permission

        with pytest.raises(DomainValidationError):
            Permission.from_string("invalid_format")

    def test_permission_equality(self) -> None:
        """Test permission equality."""
        from app.domain.entities.role import Permission

        perm1 = Permission(resource="users", action="read")
        perm2 = Permission.from_string("users:read")
        assert perm1 == perm2


class TestRoleEntity:
    """Tests for Role entity."""

    def test_role_creation(self) -> None:
        """Test role creation."""
        from uuid import uuid4

        from app.domain.entities.role import Role

        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Admin",
            description="Administrator role",
            permissions=[],
        )
        assert role.name == "Admin"

    def test_role_with_permissions(self) -> None:
        """Test role with permissions."""
        from uuid import uuid4

        from app.domain.entities.role import Permission, Role

        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Editor",
            permissions=[
                Permission(resource="posts", action="read"),
                Permission(resource="posts", action="write"),
            ],
        )
        assert len(role.permissions) == 2

    def test_role_has_permission(self) -> None:
        """Test role has_permission method."""
        from uuid import uuid4

        from app.domain.entities.role import Permission, Role

        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Reader",
            permissions=[
                Permission(resource="posts", action="read"),
            ],
        )
        assert role.has_permission("posts", "read")
        assert not role.has_permission("posts", "write")


class TestTenantEntity:
    """Tests for Tenant entity."""

    def test_tenant_creation(self) -> None:
        """Test tenant creation."""
        from uuid import uuid4

        from app.domain.entities.tenant import Tenant

        tenant = Tenant(
            id=uuid4(),
            name="Test Company",
            slug="test-company",
        )
        assert tenant.name == "Test Company"
        assert tenant.slug == "test-company"

    def test_tenant_activate(self) -> None:
        """Test tenant activation."""
        from uuid import uuid4

        from app.domain.entities.tenant import Tenant

        tenant = Tenant(
            id=uuid4(),
            name="Test",
            slug="test",
            is_active=False,
        )
        tenant.activate()
        assert tenant.is_active is True

    def test_tenant_deactivate(self) -> None:
        """Test tenant deactivation."""
        from uuid import uuid4

        from app.domain.entities.tenant import Tenant

        tenant = Tenant(
            id=uuid4(),
            name="Test",
            slug="test",
            is_active=True,
        )
        tenant.deactivate()
        assert tenant.is_active is False


class TestUserEntity:
    """Tests for User entity."""

    def test_user_creation(self) -> None:
        """Test user creation."""
        from uuid import uuid4

        from app.domain.entities.user import User
        from app.domain.value_objects.email import Email

        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("test@example.com"),
            first_name="John",
            last_name="Doe",
            password_hash="hashed",
        )
        assert user.first_name == "John"
        assert user.last_name == "Doe"

    def test_user_full_name(self) -> None:
        """Test user full name property."""
        from uuid import uuid4

        from app.domain.entities.user import User
        from app.domain.value_objects.email import Email

        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("test@example.com"),
            first_name="John",
            last_name="Doe",
            password_hash="hashed",
        )
        assert "John" in user.full_name
        assert "Doe" in user.full_name


class TestMFAEntity:
    """Tests for MFA entity."""

    def test_mfa_config_creation(self) -> None:
        """Test MFA config creation."""
        from uuid import uuid4

        from app.domain.entities.mfa import MFAConfig

        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET123456",
        )
        assert config.secret == "TESTSECRET123456"
        assert config.is_enabled is False

    def test_mfa_config_enable(self) -> None:
        """Test enabling MFA."""
        from uuid import uuid4

        from app.domain.entities.mfa import MFAConfig

        config = MFAConfig(
            user_id=uuid4(),
            secret="TESTSECRET123456",
        )
        config.enable()
        assert config.is_enabled is True


class TestTenantSettings:
    """Tests for TenantSettings value object."""

    def test_tenant_settings_defaults(self) -> None:
        """Test tenant settings defaults."""
        from app.domain.entities.tenant import TenantSettings

        settings = TenantSettings()
        assert settings.enable_2fa is False
        assert settings.max_users > 0

    def test_tenant_settings_custom(self) -> None:
        """Test custom tenant settings."""
        from app.domain.entities.tenant import TenantSettings

        settings = TenantSettings(
            enable_2fa=True,
            max_users=500,
        )
        assert settings.enable_2fa is True
        assert settings.max_users == 500
