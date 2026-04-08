# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for Audit Service.

Tests the high-level audit logging service that provides
convenience methods for common audit operations.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.application.services.audit_service import AuditService
from app.domain.entities.audit_log import AuditAction, AuditLog, AuditResourceType


@pytest.fixture
def mock_repository():
    """Mock audit log repository."""
    repository = MagicMock()
    repository.create = AsyncMock()
    return repository


@pytest.fixture
def audit_service(mock_repository):
    """Audit service instance."""
    return AuditService(mock_repository)


@pytest.fixture
def mock_audit_log():
    """Mock audit log entity."""
    return AuditLog(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        timestamp=datetime.now(UTC),
        action=AuditAction.CREATE,
        resource_type=AuditResourceType.USER,
        resource_id="user-123",
        resource_name="Test User",
        actor_id=UUID("87654321-4321-8765-4321-876543218765"),
        actor_email="admin@example.com",
        actor_ip="192.168.1.1",
        actor_user_agent="Mozilla/5.0",
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        old_value=None,
        new_value={"email": "test@example.com"},
        metadata={},
        reason=None,
    )


class TestAuditServiceLog:
    """Tests for base log method."""

    @pytest.mark.asyncio
    async def test_log_success(self, audit_service, mock_repository, mock_audit_log):
        """Test successful audit log creation."""
        mock_repository.create.return_value = mock_audit_log

        result = await audit_service.log(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.USER,
            resource_id="user-123",
            resource_name="Test User",
            actor_id=UUID("87654321-4321-8765-4321-876543218765"),
            actor_email="admin@example.com",
            actor_ip="192.168.1.1",
            actor_user_agent="Mozilla/5.0",
            tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
            new_value={"email": "test@example.com"},
            metadata={"source": "api"},
        )

        assert result == mock_audit_log
        mock_repository.create.assert_called_once()
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.CREATE
        assert created_log.resource_type == AuditResourceType.USER
        assert created_log.resource_id == "user-123"
        assert created_log.actor_email == "admin@example.com"

    @pytest.mark.asyncio
    async def test_log_minimal_params(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test log with only required parameters."""
        mock_repository.create.return_value = mock_audit_log

        result = await audit_service.log(
            action=AuditAction.LOGIN,
            resource_type=AuditResourceType.SESSION,
        )

        assert result == mock_audit_log
        mock_repository.create.assert_called_once()
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.LOGIN
        assert created_log.resource_type == AuditResourceType.SESSION
        assert created_log.metadata == {}


class TestAuditServiceLogCreate:
    """Tests for log_create convenience method."""

    @pytest.mark.asyncio
    async def test_log_create_success(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test CREATE action logging."""
        mock_repository.create.return_value = mock_audit_log

        result = await audit_service.log_create(
            resource_type=AuditResourceType.USER,
            resource_id="user-456",
            new_value={"email": "newuser@example.com", "name": "New User"},
            resource_name="New User",
            actor_id=UUID("87654321-4321-8765-4321-876543218765"),
            actor_email="admin@example.com",
        )

        assert result == mock_audit_log
        mock_repository.create.assert_called_once()
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.CREATE
        assert created_log.new_value == {
            "email": "newuser@example.com",
            "name": "New User",
        }
        assert created_log.old_value is None


class TestAuditServiceLogUpdate:
    """Tests for log_update convenience method."""

    @pytest.mark.asyncio
    async def test_log_update_success(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test UPDATE action logging."""
        mock_repository.create.return_value = mock_audit_log

        result = await audit_service.log_update(
            resource_type=AuditResourceType.USER,
            resource_id="user-789",
            old_value={"email": "old@example.com"},
            new_value={"email": "new@example.com"},
            actor_id=UUID("87654321-4321-8765-4321-876543218765"),
            actor_email="admin@example.com",
        )

        assert result == mock_audit_log
        mock_repository.create.assert_called_once()
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.UPDATE
        assert created_log.old_value == {"email": "old@example.com"}
        assert created_log.new_value == {"email": "new@example.com"}


class TestAuditServiceLogDelete:
    """Tests for log_delete convenience method."""

    @pytest.mark.asyncio
    async def test_log_delete_success(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test DELETE action logging."""
        mock_repository.create.return_value = mock_audit_log

        result = await audit_service.log_delete(
            resource_type=AuditResourceType.USER,
            resource_id="user-999",
            old_value={"email": "deleted@example.com"},
            actor_id=UUID("87654321-4321-8765-4321-876543218765"),
            actor_email="admin@example.com",
            reason="Account violation",
        )

        assert result == mock_audit_log
        mock_repository.create.assert_called_once()
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.DELETE
        assert created_log.old_value == {"email": "deleted@example.com"}
        assert created_log.reason == "Account violation"


class TestAuditServiceLogLogin:
    """Tests for log_login convenience method."""

    @pytest.mark.asyncio
    async def test_log_login_success(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test successful login logging."""
        mock_repository.create.return_value = mock_audit_log
        actor_id = UUID("87654321-4321-8765-4321-876543218765")

        result = await audit_service.log_login(
            actor_id=actor_id,
            actor_email="user@example.com",
            success=True,
            actor_ip="192.168.1.100",
        )

        assert result == mock_audit_log
        mock_repository.create.assert_called_once()
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.LOGIN
        assert created_log.resource_type == AuditResourceType.SESSION
        assert created_log.actor_email == "user@example.com"

    @pytest.mark.asyncio
    async def test_log_login_failed(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test failed login logging."""
        mock_repository.create.return_value = mock_audit_log

        result = await audit_service.log_login(
            actor_id=None,
            actor_email="hacker@example.com",
            success=False,
            failure_reason="Invalid password",
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.LOGIN_FAILED
        assert created_log.reason == "Invalid password"


class TestAuditServiceLogLogout:
    """Tests for log_logout convenience method."""

    @pytest.mark.asyncio
    async def test_log_logout_success(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test logout logging."""
        mock_repository.create.return_value = mock_audit_log
        actor_id = UUID("87654321-4321-8765-4321-876543218765")

        result = await audit_service.log_logout(
            actor_id=actor_id,
            actor_email="user@example.com",
            actor_ip="192.168.1.100",
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.LOGOUT
        assert created_log.resource_type == AuditResourceType.SESSION


class TestAuditServiceLogPasswordChange:
    """Tests for log_password_change convenience method."""

    @pytest.mark.asyncio
    async def test_log_password_change_success(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test password change logging."""
        mock_repository.create.return_value = mock_audit_log
        actor_id = UUID("87654321-4321-8765-4321-876543218765")

        result = await audit_service.log_password_change(
            actor_id=actor_id,
            actor_email="user@example.com",
            actor_ip="192.168.1.100",
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.PASSWORD_CHANGE
        assert created_log.resource_type == AuditResourceType.USER


class TestAuditServiceLogMFAChange:
    """Tests for log_mfa_change convenience method."""

    @pytest.mark.asyncio
    async def test_log_mfa_enabled(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test MFA enabled logging."""
        mock_repository.create.return_value = mock_audit_log
        actor_id = UUID("87654321-4321-8765-4321-876543218765")

        result = await audit_service.log_mfa_change(
            actor_id=actor_id,
            actor_email="user@example.com",
            enabled=True,
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.MFA_ENABLED

    @pytest.mark.asyncio
    async def test_log_mfa_disabled(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test MFA disabled logging."""
        mock_repository.create.return_value = mock_audit_log
        actor_id = UUID("87654321-4321-8765-4321-876543218765")

        result = await audit_service.log_mfa_change(
            actor_id=actor_id,
            actor_email="user@example.com",
            enabled=False,
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.MFA_DISABLED


class TestAuditServiceLogAPIKey:
    """Tests for API key logging methods."""

    @pytest.mark.asyncio
    async def test_log_api_key_created(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test API key creation logging."""
        mock_repository.create.return_value = mock_audit_log

        result = await audit_service.log_api_key_created(
            api_key_id="key-123",
            api_key_name="Production API Key",
            actor_id=UUID("87654321-4321-8765-4321-876543218765"),
            actor_email="admin@example.com",
            scopes=["read:users", "write:users"],
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.API_KEY_CREATED
        assert created_log.resource_type == AuditResourceType.API_KEY
        assert created_log.new_value == {"scopes": ["read:users", "write:users"]}

    @pytest.mark.asyncio
    async def test_log_api_key_revoked(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test API key revocation logging."""
        mock_repository.create.return_value = mock_audit_log

        result = await audit_service.log_api_key_revoked(
            api_key_id="key-456",
            api_key_name="Compromised Key",
            actor_id=UUID("87654321-4321-8765-4321-876543218765"),
            actor_email="admin@example.com",
            reason="Security breach detected",
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.API_KEY_REVOKED
        assert created_log.reason == "Security breach detected"


class TestAuditServiceLogRoleAssignment:
    """Tests for role assignment logging."""

    @pytest.mark.asyncio
    async def test_log_role_assigned(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test role assignment logging."""
        mock_repository.create.return_value = mock_audit_log
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        role_id = UUID("22222222-2222-2222-2222-222222222222")

        result = await audit_service.log_role_assignment(
            user_id=user_id,
            role_id=role_id,
            role_name="admin",
            assigned=True,
            actor_id=UUID("87654321-4321-8765-4321-876543218765"),
            actor_email="superadmin@example.com",
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.ROLE_ASSIGNED
        assert created_log.new_value == {"role_id": str(role_id), "role_name": "admin"}

    @pytest.mark.asyncio
    async def test_log_role_removed(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test role removal logging."""
        mock_repository.create.return_value = mock_audit_log
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        role_id = UUID("22222222-2222-2222-2222-222222222222")

        result = await audit_service.log_role_assignment(
            user_id=user_id,
            role_id=role_id,
            role_name="moderator",
            assigned=False,
            actor_id=UUID("87654321-4321-8765-4321-876543218765"),
            actor_email="admin@example.com",
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.ROLE_REMOVED


class TestAuditServiceLogExport:
    """Tests for export logging."""

    @pytest.mark.asyncio
    async def test_log_export_success(
        self, audit_service, mock_repository, mock_audit_log
    ):
        """Test data export logging."""
        mock_repository.create.return_value = mock_audit_log

        result = await audit_service.log_export(
            resource_type=AuditResourceType.USER,
            record_count=1500,
            export_format="csv",
            actor_id=UUID("87654321-4321-8765-4321-876543218765"),
            actor_email="admin@example.com",
        )

        assert result == mock_audit_log
        created_log = mock_repository.create.call_args[0][0]
        assert created_log.action == AuditAction.EXPORT
        assert created_log.metadata["record_count"] == 1500
        assert created_log.metadata["format"] == "csv"
