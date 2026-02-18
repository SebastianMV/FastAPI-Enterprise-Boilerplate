# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Audit Log domain entity for tracking all system actions."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class AuditAction(str, Enum):
    """Types of auditable actions in the system."""

    # CRUD Operations
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    # Authentication
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET = "PASSWORD_RESET"
    MFA_ENABLED = "MFA_ENABLED"
    MFA_DISABLED = "MFA_DISABLED"

    # Authorization
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PERMISSION_REVOKED = "PERMISSION_REVOKED"
    ROLE_ASSIGNED = "ROLE_ASSIGNED"
    ROLE_REMOVED = "ROLE_REMOVED"

    # Data Operations
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    BULK_UPDATE = "BULK_UPDATE"
    BULK_DELETE = "BULK_DELETE"

    # System
    API_KEY_CREATED = "API_KEY_CREATED"
    API_KEY_REVOKED = "API_KEY_REVOKED"
    TENANT_CREATED = "TENANT_CREATED"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"


class AuditResourceType(str, Enum):
    """Types of resources that can be audited."""

    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    TENANT = "tenant"
    API_KEY = "api_key"
    SESSION = "session"
    SYSTEM = "system"


@dataclass
class AuditLog:
    """
    Immutable audit log entry.

    Records WHO did WHAT to WHICH resource, WHEN, and from WHERE.
    This entity is append-only and should never be modified or deleted.

    Attributes:
        id: Unique identifier for the audit entry
        timestamp: When the action occurred (UTC)
        actor_id: User ID who performed the action (None for system actions)
        actor_email: Email of the actor for quick reference
        actor_ip: IP address of the request
        actor_user_agent: Browser/client user agent string
        action: Type of action performed
        resource_type: Type of resource affected
        resource_id: ID of the affected resource
        resource_name: Human-readable name of the resource
        tenant_id: Tenant context (for multi-tenant isolation)
        old_value: State before the action (for updates/deletes)
        new_value: State after the action (for creates/updates)
        metadata: Additional context (request_id, correlation_id, etc.)
        reason: Optional reason for the action (for sensitive operations)
    """

    # Identity
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Actor (WHO)
    actor_id: UUID | None = None
    actor_email: str | None = None
    actor_ip: str | None = None
    actor_user_agent: str | None = None

    # Action (WHAT)
    action: AuditAction = AuditAction.READ

    # Resource (WHICH)
    resource_type: AuditResourceType = AuditResourceType.SYSTEM
    resource_id: str | None = None
    resource_name: str | None = None

    # Tenant Context
    tenant_id: UUID | None = None

    # Change Details (HOW)
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None

    # Additional Context
    metadata: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action.value}, "
            f"resource={self.resource_type.value}/{self.resource_id})>"
        )

    def __post_init__(self) -> None:
        """Validate audit log entry."""
        # Ensure timestamp is in UTC
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)

    @property
    def changes(self) -> dict[str, tuple[Any, Any]] | None:
        """
        Get the diff between old and new values.

        Returns:
            Dictionary of {field: (old_value, new_value)} for changed fields
        """
        if not self.old_value or not self.new_value:
            return None

        changes = {}
        all_keys = set(self.old_value.keys()) | set(self.new_value.keys())

        for key in all_keys:
            old = self.old_value.get(key)
            new = self.new_value.get(key)
            if old != new:
                changes[key] = (old, new)

        return changes if changes else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "actor_email": self.actor_email,
            "actor_ip": self.actor_ip,
            "action": self.action.value,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "metadata": self.metadata,
            "reason": self.reason,
        }
