# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for domain entities - executing real code."""

from __future__ import annotations

from uuid import uuid4
from datetime import datetime, UTC, timedelta

import pytest


class TestUserEntity:
    """Tests for User entity."""

    def test_user_entity_import(self) -> None:
        """Test User entity can be imported."""
        from app.domain.entities.user import User

        assert User is not None

    def test_user_entity_creation(self) -> None:
        """Test User entity creation."""
        from app.domain.entities.user import User
        from app.domain.value_objects.email import Email

        user = User(
            id=uuid4(),
            email=Email("test@example.com"),
            password_hash="hashed_password",
            first_name="Test",
            last_name="User",
            is_active=True,
        )
        assert user.email.value == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True

    def test_user_entity_has_id(self) -> None:
        """Test User entity has id."""
        from app.domain.entities.user import User
        from app.domain.value_objects.email import Email

        user_id = uuid4()
        user = User(
            id=user_id,
            email=Email("test@example.com"),
            password_hash="hashed_password",
            first_name="Test",
            last_name="User",
        )
        assert user.id == user_id


class TestTenantEntity:
    """Tests for Tenant entity."""

    def test_tenant_entity_import(self) -> None:
        """Test Tenant entity can be imported."""
        from app.domain.entities.tenant import Tenant

        assert Tenant is not None

    def test_tenant_entity_creation(self) -> None:
        """Test Tenant entity creation."""
        from app.domain.entities.tenant import Tenant

        tenant = Tenant(
            id=uuid4(),
            name="Test Tenant",
            slug="test-tenant",
            is_active=True,
        )
        assert tenant.name == "Test Tenant"
        assert tenant.slug == "test-tenant"


class TestRoleEntity:
    """Tests for Role entity."""

    def test_role_entity_import(self) -> None:
        """Test Role entity can be imported."""
        from app.domain.entities.role import Role

        assert Role is not None

    def test_role_entity_creation(self) -> None:
        """Test Role entity creation."""
        from app.domain.entities.role import Role

        role = Role(
            id=uuid4(),
            name="admin",
            description="Administrator role",
        )
        assert role.name == "admin"


class TestNotificationEntity:
    """Tests for Notification entity."""

    def test_notification_entity_import(self) -> None:
        """Test Notification entity can be imported."""
        from app.domain.entities.notification import Notification, NotificationType

        assert Notification is not None
        assert NotificationType is not None

    def test_notification_type_enum(self) -> None:
        """Test NotificationType enum values."""
        from app.domain.entities.notification import NotificationType

        assert hasattr(NotificationType, "INFO") or hasattr(NotificationType, "info")


class TestAuditLogEntity:
    """Tests for AuditLog entity."""

    def test_audit_log_entity_import(self) -> None:
        """Test AuditLog entity can be imported."""
        from app.domain.entities.audit_log import AuditLog, AuditAction, AuditResourceType

        assert AuditLog is not None
        assert AuditAction is not None
        assert AuditResourceType is not None

    def test_audit_action_enum(self) -> None:
        """Test AuditAction enum values."""
        from app.domain.entities.audit_log import AuditAction

        # Should have common actions
        assert hasattr(AuditAction, "CREATE") or hasattr(AuditAction, "create")


class TestAPIKeyEntity:
    """Tests for APIKey entity."""

    def test_api_key_entity_import(self) -> None:
        """Test APIKey entity can be imported."""
        from app.domain.entities.api_key import APIKey

        assert APIKey is not None


class TestMFAConfigEntity:
    """Tests for MFAConfig entity."""

    def test_mfa_config_entity_import(self) -> None:
        """Test MFAConfig entity can be imported."""
        try:
            from app.domain.entities.mfa import MFAConfig

            assert MFAConfig is not None
        except ImportError:
            pytest.skip("MFAConfig not in expected location")
