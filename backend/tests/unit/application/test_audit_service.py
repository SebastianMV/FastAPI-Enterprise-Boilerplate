# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for Audit Service.

Tests for audit logging functionality.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.services.audit_service import AuditService
from app.domain.entities.audit_log import AuditAction, AuditLog, AuditResourceType


class TestAuditService:
    """Tests for AuditService."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock audit log repository."""
        repo = AsyncMock()

        # Make create return the passed audit log
        async def mock_create(audit_log: AuditLog) -> AuditLog:
            return audit_log

        repo.create.side_effect = mock_create
        return repo

    @pytest.fixture
    def audit_service(self, mock_repository: AsyncMock) -> AuditService:
        """Create audit service with mock repository."""
        return AuditService(repository=mock_repository)

    @pytest.mark.asyncio
    async def test_log_creates_audit_entry(
        self, audit_service: AuditService, mock_repository: AsyncMock
    ) -> None:
        """Test that log creates an audit entry."""
        user_id = uuid4()
        tenant_id = uuid4()

        result = await audit_service.log(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.USER,
            resource_id="user-123",
            resource_name="Test User",
            actor_id=user_id,
            actor_email="admin@example.com",
            actor_ip="192.168.1.1",
            tenant_id=tenant_id,
        )

        assert isinstance(result, AuditLog)
        assert result.action == AuditAction.CREATE
        assert result.resource_type == AuditResourceType.USER
        assert result.resource_id == "user-123"
        assert result.actor_id == user_id
        assert result.actor_email == "admin@example.com"
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_with_old_and_new_values(
        self, audit_service: AuditService
    ) -> None:
        """Test logging with old and new values for update."""
        old_value = {"name": "Old Name", "email": "old@example.com"}
        new_value = {"name": "New Name", "email": "new@example.com"}

        result = await audit_service.log(
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.USER,
            resource_id="user-123",
            old_value=old_value,
            new_value=new_value,
        )

        assert result.old_value == old_value
        assert result.new_value == new_value

    @pytest.mark.asyncio
    async def test_log_with_metadata(self, audit_service: AuditService) -> None:
        """Test logging with additional metadata."""
        metadata = {"source": "api", "version": "v1"}

        result = await audit_service.log(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.API_KEY,
            resource_id="key-123",
            metadata=metadata,
        )

        assert result.metadata == metadata

    @pytest.mark.asyncio
    async def test_log_with_reason(self, audit_service: AuditService) -> None:
        """Test logging with reason for sensitive actions."""
        result = await audit_service.log(
            action=AuditAction.DELETE,
            resource_type=AuditResourceType.USER,
            resource_id="user-123",
            reason="User requested account deletion",
        )

        assert result.reason == "User requested account deletion"


class TestAuditServiceConvenienceMethods:
    """Tests for AuditService convenience methods."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock audit log repository."""
        repo = AsyncMock()

        async def mock_create(audit_log: AuditLog) -> AuditLog:
            return audit_log

        repo.create.side_effect = mock_create
        return repo

    @pytest.fixture
    def audit_service(self, mock_repository: AsyncMock) -> AuditService:
        """Create audit service with mock repository."""
        return AuditService(repository=mock_repository)

    @pytest.mark.asyncio
    async def test_log_create(self, audit_service: AuditService) -> None:
        """Test log_create convenience method."""
        new_value = {"email": "new@example.com", "name": "New User"}

        result = await audit_service.log_create(
            resource_type=AuditResourceType.USER,
            resource_id="user-123",
            new_value=new_value,
            resource_name="New User",
        )

        assert result.action == AuditAction.CREATE
        assert result.resource_type == AuditResourceType.USER
        assert result.new_value == new_value

    @pytest.mark.asyncio
    async def test_log_update(self, audit_service: AuditService) -> None:
        """Test log_update convenience method."""
        old_value = {"name": "Old"}
        new_value = {"name": "New"}

        result = await audit_service.log_update(
            resource_type=AuditResourceType.USER,
            resource_id="user-123",
            old_value=old_value,
            new_value=new_value,
        )

        assert result.action == AuditAction.UPDATE
        assert result.old_value == old_value
        assert result.new_value == new_value

    @pytest.mark.asyncio
    async def test_log_delete(self, audit_service: AuditService) -> None:
        """Test log_delete convenience method."""
        old_value = {"email": "deleted@example.com"}

        result = await audit_service.log_delete(
            resource_type=AuditResourceType.USER,
            resource_id="user-123",
            old_value=old_value,
            reason="GDPR request",
        )

        assert result.action == AuditAction.DELETE
        assert result.old_value == old_value
        assert result.reason == "GDPR request"

    @pytest.mark.asyncio
    async def test_log_login_success(self, audit_service: AuditService) -> None:
        """Test log_login for successful login."""
        user_id = uuid4()

        result = await audit_service.log_login(
            actor_id=user_id,
            actor_email="user@example.com",
            success=True,
            actor_ip="192.168.1.1",
            actor_user_agent="Mozilla/5.0",
        )

        assert result.action == AuditAction.LOGIN
        assert result.actor_email == "user@example.com"
        assert result.actor_ip == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_log_login_failure(self, audit_service: AuditService) -> None:
        """Test log_login for failed login."""
        result = await audit_service.log_login(
            actor_id=None,
            actor_email="unknown@example.com",
            success=False,
            actor_ip="192.168.1.100",
            failure_reason="Invalid password",
        )

        assert result.action == AuditAction.LOGIN_FAILED
        assert result.actor_id is None


class TestAuditAction:
    """Tests for AuditAction enum."""

    def test_crud_actions(self) -> None:
        """Test CRUD action values."""
        assert AuditAction.CREATE.value == "CREATE"
        assert AuditAction.READ.value == "READ"
        assert AuditAction.UPDATE.value == "UPDATE"
        assert AuditAction.DELETE.value == "DELETE"

    def test_auth_actions(self) -> None:
        """Test authentication action values."""
        assert AuditAction.LOGIN.value == "LOGIN"
        assert AuditAction.LOGOUT.value == "LOGOUT"
        assert AuditAction.LOGIN_FAILED.value == "LOGIN_FAILED"
        assert AuditAction.PASSWORD_CHANGE.value == "PASSWORD_CHANGE"
        assert AuditAction.MFA_ENABLED.value == "MFA_ENABLED"
        assert AuditAction.MFA_DISABLED.value == "MFA_DISABLED"

    def test_authorization_actions(self) -> None:
        """Test authorization action values."""
        assert AuditAction.PERMISSION_GRANTED.value == "PERMISSION_GRANTED"
        assert AuditAction.PERMISSION_REVOKED.value == "PERMISSION_REVOKED"
        assert AuditAction.ROLE_ASSIGNED.value == "ROLE_ASSIGNED"
        assert AuditAction.ROLE_REMOVED.value == "ROLE_REMOVED"


class TestAuditResourceType:
    """Tests for AuditResourceType enum."""

    def test_resource_types(self) -> None:
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

    def test_create_audit_log(self) -> None:
        """Test creating an audit log entry."""
        user_id = uuid4()
        tenant_id = uuid4()

        log = AuditLog(
            timestamp=datetime.now(UTC),
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.USER,
            resource_id="user-123",
            resource_name="Test User",
            actor_id=user_id,
            actor_email="admin@example.com",
            actor_ip="192.168.1.1",
            tenant_id=tenant_id,
        )

        assert log.action == AuditAction.CREATE
        assert log.resource_type == AuditResourceType.USER
        assert log.actor_id == user_id
        assert log.tenant_id == tenant_id

    def test_audit_log_with_changes(self) -> None:
        """Test audit log with old and new values."""
        log = AuditLog(
            timestamp=datetime.now(UTC),
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.USER,
            resource_id="user-123",
            old_value={"status": "active"},
            new_value={"status": "inactive"},
        )

        assert log.old_value == {"status": "active"}
        assert log.new_value == {"status": "inactive"}

    def test_audit_log_has_id(self) -> None:
        """Test that audit log has a generated ID."""
        log = AuditLog(
            timestamp=datetime.now(UTC),
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.USER,
        )

        assert log.id is not None
