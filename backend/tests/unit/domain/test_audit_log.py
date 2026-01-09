# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for AuditLog domain entity.

Tests for audit log functionality including changes detection.
"""

from datetime import datetime, UTC
from uuid import uuid4

import pytest

from app.domain.entities.audit_log import (
    AuditLog,
    AuditAction,
    AuditResourceType,
)


class TestAuditAction:
    """Tests for AuditAction enum."""

    def test_crud_actions(self) -> None:
        """Test CRUD action values."""
        assert AuditAction.CREATE.value == "CREATE"
        assert AuditAction.READ.value == "READ"
        assert AuditAction.UPDATE.value == "UPDATE"
        assert AuditAction.DELETE.value == "DELETE"

    def test_authentication_actions(self) -> None:
        """Test authentication action values."""
        assert AuditAction.LOGIN.value == "LOGIN"
        assert AuditAction.LOGOUT.value == "LOGOUT"
        assert AuditAction.LOGIN_FAILED.value == "LOGIN_FAILED"
        assert AuditAction.PASSWORD_CHANGE.value == "PASSWORD_CHANGE"
        assert AuditAction.PASSWORD_RESET.value == "PASSWORD_RESET"

    def test_mfa_actions(self) -> None:
        """Test MFA action values."""
        assert AuditAction.MFA_ENABLED.value == "MFA_ENABLED"
        assert AuditAction.MFA_DISABLED.value == "MFA_DISABLED"

    def test_authorization_actions(self) -> None:
        """Test authorization action values."""
        assert AuditAction.PERMISSION_GRANTED.value == "PERMISSION_GRANTED"
        assert AuditAction.PERMISSION_REVOKED.value == "PERMISSION_REVOKED"
        assert AuditAction.ROLE_ASSIGNED.value == "ROLE_ASSIGNED"
        assert AuditAction.ROLE_REMOVED.value == "ROLE_REMOVED"

    def test_data_operations(self) -> None:
        """Test data operation action values."""
        assert AuditAction.EXPORT.value == "EXPORT"
        assert AuditAction.IMPORT.value == "IMPORT"
        assert AuditAction.BULK_UPDATE.value == "BULK_UPDATE"
        assert AuditAction.BULK_DELETE.value == "BULK_DELETE"

    def test_system_actions(self) -> None:
        """Test system action values."""
        assert AuditAction.API_KEY_CREATED.value == "API_KEY_CREATED"
        assert AuditAction.API_KEY_REVOKED.value == "API_KEY_REVOKED"
        assert AuditAction.TENANT_CREATED.value == "TENANT_CREATED"
        assert AuditAction.TENANT_SUSPENDED.value == "TENANT_SUSPENDED"


class TestAuditResourceType:
    """Tests for AuditResourceType enum."""

    def test_resource_type_values(self) -> None:
        """Test resource type values."""
        assert AuditResourceType.USER.value == "user"
        assert AuditResourceType.ROLE.value == "role"
        assert AuditResourceType.PERMISSION.value == "permission"
        assert AuditResourceType.TENANT.value == "tenant"
        assert AuditResourceType.API_KEY.value == "api_key"
        assert AuditResourceType.SESSION.value == "session"
        assert AuditResourceType.SYSTEM.value == "system"


class TestAuditLog:
    """Tests for AuditLog entity."""

    def test_create_basic_audit_log(self) -> None:
        """Test creating basic audit log."""
        log = AuditLog(
            action=AuditAction.LOGIN,
            resource_type=AuditResourceType.USER,
        )
        
        assert log.id is not None
        assert log.action == AuditAction.LOGIN
        assert log.resource_type == AuditResourceType.USER
        assert log.timestamp is not None

    def test_default_values(self) -> None:
        """Test default values."""
        log = AuditLog()
        
        assert log.action == AuditAction.READ
        assert log.resource_type == AuditResourceType.SYSTEM
        assert log.actor_id is None
        assert log.actor_email is None
        assert log.actor_ip is None
        assert log.actor_user_agent is None
        assert log.resource_id is None
        assert log.resource_name is None
        assert log.tenant_id is None
        assert log.old_value is None
        assert log.new_value is None
        assert log.metadata == {}
        assert log.reason is None

    def test_with_actor_info(self) -> None:
        """Test audit log with actor information."""
        actor_id = uuid4()
        log = AuditLog(
            actor_id=actor_id,
            actor_email="admin@example.com",
            actor_ip="192.168.1.100",
            actor_user_agent="Mozilla/5.0",
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.USER,
        )
        
        assert log.actor_id == actor_id
        assert log.actor_email == "admin@example.com"
        assert log.actor_ip == "192.168.1.100"
        assert log.actor_user_agent == "Mozilla/5.0"

    def test_with_resource_info(self) -> None:
        """Test audit log with resource information."""
        resource_id = str(uuid4())
        log = AuditLog(
            action=AuditAction.DELETE,
            resource_type=AuditResourceType.USER,
            resource_id=resource_id,
            resource_name="john.doe@example.com",
        )
        
        assert log.resource_id == resource_id
        assert log.resource_name == "john.doe@example.com"

    def test_with_tenant_context(self) -> None:
        """Test audit log with tenant context."""
        tenant_id = uuid4()
        log = AuditLog(
            tenant_id=tenant_id,
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.ROLE,
        )
        
        assert log.tenant_id == tenant_id

    def test_with_change_values(self) -> None:
        """Test audit log with old and new values."""
        log = AuditLog(
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.USER,
            old_value={"name": "John", "active": True},
            new_value={"name": "Johnny", "active": True},
        )
        
        assert log.old_value == {"name": "John", "active": True}
        assert log.new_value == {"name": "Johnny", "active": True}

    def test_with_metadata(self) -> None:
        """Test audit log with metadata."""
        log = AuditLog(
            action=AuditAction.EXPORT,
            resource_type=AuditResourceType.USER,
            metadata={
                "request_id": "abc123",
                "correlation_id": "xyz789",
                "exported_count": 150,
            },
        )
        
        assert log.metadata["request_id"] == "abc123"
        assert log.metadata["correlation_id"] == "xyz789"
        assert log.metadata["exported_count"] == 150

    def test_with_reason(self) -> None:
        """Test audit log with reason."""
        log = AuditLog(
            action=AuditAction.DELETE,
            resource_type=AuditResourceType.USER,
            reason="User requested account deletion",
        )
        
        assert log.reason == "User requested account deletion"


class TestAuditLogPostInit:
    """Tests for __post_init__ validation."""

    def test_timestamp_gets_utc_timezone(self) -> None:
        """Test that naive timestamps get UTC timezone."""
        naive_timestamp = datetime(2025, 1, 15, 12, 0, 0)
        log = AuditLog(timestamp=naive_timestamp)
        
        assert log.timestamp.tzinfo == UTC

    def test_aware_timestamp_preserved(self) -> None:
        """Test that aware timestamps are preserved."""
        aware_timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        log = AuditLog(timestamp=aware_timestamp)
        
        assert log.timestamp == aware_timestamp


class TestAuditLogChanges:
    """Tests for changes property."""

    def test_changes_with_no_old_value(self) -> None:
        """Test changes returns None when no old value."""
        log = AuditLog(
            action=AuditAction.CREATE,
            new_value={"name": "John"},
        )
        
        assert log.changes is None

    def test_changes_with_no_new_value(self) -> None:
        """Test changes returns None when no new value."""
        log = AuditLog(
            action=AuditAction.DELETE,
            old_value={"name": "John"},
        )
        
        assert log.changes is None

    def test_changes_detects_modifications(self) -> None:
        """Test changes detects modified fields."""
        log = AuditLog(
            action=AuditAction.UPDATE,
            old_value={"name": "John", "email": "john@example.com"},
            new_value={"name": "Johnny", "email": "john@example.com"},
        )
        
        changes = log.changes
        
        assert changes is not None
        assert "name" in changes
        assert changes["name"] == ("John", "Johnny")
        assert "email" not in changes

    def test_changes_detects_additions(self) -> None:
        """Test changes detects added fields."""
        log = AuditLog(
            action=AuditAction.UPDATE,
            old_value={"name": "John"},
            new_value={"name": "John", "phone": "123-456-7890"},
        )
        
        changes = log.changes
        
        assert changes is not None
        assert "phone" in changes
        assert changes["phone"] == (None, "123-456-7890")

    def test_changes_detects_removals(self) -> None:
        """Test changes detects removed fields."""
        log = AuditLog(
            action=AuditAction.UPDATE,
            old_value={"name": "John", "phone": "123-456-7890"},
            new_value={"name": "John"},
        )
        
        changes = log.changes
        
        assert changes is not None
        assert "phone" in changes
        assert changes["phone"] == ("123-456-7890", None)

    def test_changes_returns_none_when_identical(self) -> None:
        """Test changes returns None when values are identical."""
        log = AuditLog(
            action=AuditAction.UPDATE,
            old_value={"name": "John", "active": True},
            new_value={"name": "John", "active": True},
        )
        
        assert log.changes is None

    def test_changes_multiple_fields(self) -> None:
        """Test changes with multiple changed fields."""
        log = AuditLog(
            action=AuditAction.UPDATE,
            old_value={
                "name": "John",
                "email": "john@old.com",
                "active": False,
            },
            new_value={
                "name": "Johnny",
                "email": "john@new.com",
                "active": True,
            },
        )
        
        changes = log.changes
        
        assert changes is not None
        assert len(changes) == 3
        assert changes["name"] == ("John", "Johnny")
        assert changes["email"] == ("john@old.com", "john@new.com")
        assert changes["active"] == (False, True)


class TestAuditLogToDict:
    """Tests for to_dict method."""

    def test_to_dict_basic(self) -> None:
        """Test basic to_dict conversion."""
        log_id = uuid4()
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        
        log = AuditLog(
            id=log_id,
            timestamp=timestamp,
            action=AuditAction.LOGIN,
            resource_type=AuditResourceType.USER,
        )
        
        result = log.to_dict()
        
        assert result["id"] == str(log_id)
        assert result["timestamp"] == timestamp.isoformat()
        assert result["action"] == "LOGIN"
        assert result["resource_type"] == "user"

    def test_to_dict_with_actor(self) -> None:
        """Test to_dict with actor information."""
        actor_id = uuid4()
        log = AuditLog(
            actor_id=actor_id,
            actor_email="test@example.com",
            actor_ip="10.0.0.1",
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.ROLE,
        )
        
        result = log.to_dict()
        
        assert result["actor_id"] == str(actor_id)
        assert result["actor_email"] == "test@example.com"
        assert result["actor_ip"] == "10.0.0.1"

    def test_to_dict_with_tenant(self) -> None:
        """Test to_dict with tenant ID."""
        tenant_id = uuid4()
        log = AuditLog(
            tenant_id=tenant_id,
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.TENANT,
        )
        
        result = log.to_dict()
        
        assert result["tenant_id"] == str(tenant_id)

    def test_to_dict_null_ids(self) -> None:
        """Test to_dict handles null IDs."""
        log = AuditLog(
            action=AuditAction.READ,
            resource_type=AuditResourceType.SYSTEM,
        )
        
        result = log.to_dict()
        
        assert result["actor_id"] is None
        assert result["tenant_id"] is None

    def test_to_dict_with_values(self) -> None:
        """Test to_dict includes old and new values."""
        log = AuditLog(
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.USER,
            old_value={"name": "Old"},
            new_value={"name": "New"},
            metadata={"source": "api"},
        )
        
        result = log.to_dict()
        
        assert result["old_value"] == {"name": "Old"}
        assert result["new_value"] == {"name": "New"}
        assert result["metadata"] == {"source": "api"}
