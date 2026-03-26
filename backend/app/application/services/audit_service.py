# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Audit Service for logging system actions.

Provides a centralized way to create audit log entries
throughout the application.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.entities.audit_log import AuditAction, AuditLog, AuditResourceType
from app.domain.ports.audit_log_repository import AuditLogRepository
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """
    Service for creating and managing audit logs.

    This service provides a high-level API for logging actions
    throughout the application. It handles the creation of
    properly formatted audit log entries.
    """

    def __init__(self, repository: AuditLogRepository) -> None:
        """
        Initialize the audit service.

        Args:
            repository: The audit log repository for persistence
        """
        self._repository = repository

    async def log(
        self,
        action: AuditAction,
        resource_type: AuditResourceType,
        *,
        resource_id: str | None = None,
        resource_name: str | None = None,
        actor_id: UUID | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        actor_user_agent: str | None = None,
        tenant_id: UUID | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> AuditLog:
        """
        Create a new audit log entry.

        Args:
            action: The type of action performed
            resource_type: The type of resource affected
            resource_id: ID of the affected resource
            resource_name: Human-readable name of the resource
            actor_id: User ID who performed the action
            actor_email: Email of the actor
            actor_ip: IP address of the request
            actor_user_agent: User agent of the client
            tenant_id: Tenant context
            old_value: State before the action
            new_value: State after the action
            metadata: Additional context
            reason: Optional reason for sensitive actions

        Returns:
            The created audit log entry
        """
        audit_log = AuditLog(
            timestamp=datetime.now(UTC),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            tenant_id=tenant_id,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
            reason=reason,
        )

        return await self._repository.create(audit_log)

    async def log_create(
        self,
        resource_type: AuditResourceType,
        resource_id: str,
        new_value: dict[str, Any],
        *,
        resource_name: str | None = None,
        actor_id: UUID | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Convenience method for logging CREATE actions."""
        return await self.log(
            action=AuditAction.CREATE,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
            new_value=new_value,
            metadata=metadata,
        )

    async def log_update(
        self,
        resource_type: AuditResourceType,
        resource_id: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        *,
        resource_name: str | None = None,
        actor_id: UUID | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Convenience method for logging UPDATE actions."""
        return await self.log(
            action=AuditAction.UPDATE,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata,
        )

    async def log_delete(
        self,
        resource_type: AuditResourceType,
        resource_id: str,
        old_value: dict[str, Any],
        *,
        resource_name: str | None = None,
        actor_id: UUID | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Convenience method for logging DELETE actions."""
        return await self.log(
            action=AuditAction.DELETE,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
            old_value=old_value,
            reason=reason,
            metadata=metadata,
        )

    async def log_login(
        self,
        actor_id: UUID | None,
        actor_email: str,
        *,
        success: bool = True,
        actor_ip: str | None = None,
        actor_user_agent: str | None = None,
        tenant_id: UUID | None = None,
        failure_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a login attempt."""
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        return await self.log(
            action=action,
            resource_type=AuditResourceType.SESSION,
            resource_id=str(actor_id) if actor_id else None,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            tenant_id=tenant_id,
            reason=failure_reason if not success else None,
            metadata=metadata,
        )

    async def log_logout(
        self,
        actor_id: UUID,
        actor_email: str,
        *,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
    ) -> AuditLog:
        """Log a logout action."""
        return await self.log(
            action=AuditAction.LOGOUT,
            resource_type=AuditResourceType.SESSION,
            resource_id=str(actor_id),
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
        )

    async def log_password_change(
        self,
        actor_id: UUID,
        actor_email: str,
        *,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
    ) -> AuditLog:
        """Log a password change."""
        return await self.log(
            action=AuditAction.PASSWORD_CHANGE,
            resource_type=AuditResourceType.USER,
            resource_id=str(actor_id),
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
        )

    async def log_mfa_change(
        self,
        actor_id: UUID,
        actor_email: str,
        *,
        enabled: bool,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
    ) -> AuditLog:
        """Log MFA enable/disable."""
        action = AuditAction.MFA_ENABLED if enabled else AuditAction.MFA_DISABLED
        return await self.log(
            action=action,
            resource_type=AuditResourceType.USER,
            resource_id=str(actor_id),
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
        )

    async def log_api_key_created(
        self,
        api_key_id: str,
        api_key_name: str,
        *,
        actor_id: UUID | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
        scopes: list[str] | None = None,
    ) -> AuditLog:
        """Log API key creation."""
        return await self.log(
            action=AuditAction.API_KEY_CREATED,
            resource_type=AuditResourceType.API_KEY,
            resource_id=api_key_id,
            resource_name=api_key_name,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
            new_value={"scopes": scopes} if scopes else None,
        )

    async def log_api_key_revoked(
        self,
        api_key_id: str,
        api_key_name: str,
        *,
        actor_id: UUID | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
        reason: str | None = None,
    ) -> AuditLog:
        """Log API key revocation."""
        return await self.log(
            action=AuditAction.API_KEY_REVOKED,
            resource_type=AuditResourceType.API_KEY,
            resource_id=api_key_id,
            resource_name=api_key_name,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
            reason=reason,
        )

    async def log_role_assignment(
        self,
        user_id: UUID,
        role_id: UUID,
        role_name: str,
        *,
        assigned: bool = True,
        actor_id: UUID | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
    ) -> AuditLog:
        """Log role assignment or removal."""
        action = AuditAction.ROLE_ASSIGNED if assigned else AuditAction.ROLE_REMOVED
        return await self.log(
            action=action,
            resource_type=AuditResourceType.USER,
            resource_id=str(user_id),
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
            new_value={"role_id": str(role_id), "role_name": role_name},
        )

    async def log_export(
        self,
        resource_type: AuditResourceType,
        *,
        record_count: int,
        export_format: str,
        actor_id: UUID | None = None,
        actor_email: str | None = None,
        actor_ip: str | None = None,
        tenant_id: UUID | None = None,
    ) -> AuditLog:
        """Log data export action."""
        return await self.log(
            action=AuditAction.EXPORT,
            resource_type=resource_type,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            tenant_id=tenant_id,
            metadata={
                "record_count": record_count,
                "format": export_format,
            },
        )
