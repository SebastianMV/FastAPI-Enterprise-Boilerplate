# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Port (interface) for Audit Log repository."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.domain.entities.audit_log import AuditAction, AuditLog, AuditResourceType


class AuditLogRepository(ABC):
    """
    Abstract repository for audit log operations.

    This is a port (interface) in hexagonal architecture.
    The infrastructure layer provides the concrete implementation.

    Note: Audit logs are append-only. No update or delete operations.
    """

    @abstractmethod
    async def create(self, audit_log: AuditLog) -> AuditLog:
        """
        Create a new audit log entry.

        Args:
            audit_log: The audit log entry to persist

        Returns:
            The created audit log with generated ID
        """
        ...

    @abstractmethod
    async def create_many(self, audit_logs: list[AuditLog]) -> list[AuditLog]:
        """
        Create multiple audit log entries in a single transaction.

        Args:
            audit_logs: List of audit log entries to persist

        Returns:
            List of created audit logs
        """
        ...

    @abstractmethod
    async def get_by_id(self, audit_id: UUID, tenant_id: UUID | None = None) -> AuditLog | None:
        """
        Retrieve an audit log entry by ID, optionally scoped to tenant.

        Args:
            audit_id: The unique identifier of the audit log
            tenant_id: Optional tenant ID for access control

        Returns:
            The audit log entry or None if not found
        """
        ...

    @abstractmethod
    async def list_by_actor(
        self,
        actor_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Sequence[AuditLog]:
        """
        List audit logs for a specific actor (user).

        Args:
            actor_id: The user ID to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            start_date: Filter by minimum timestamp
            end_date: Filter by maximum timestamp

        Returns:
            List of matching audit log entries
        """
        ...

    @abstractmethod
    async def list_by_resource(
        self,
        resource_type: AuditResourceType,
        resource_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        tenant_id: UUID | None = None,
    ) -> Sequence[AuditLog]:
        """
        List audit logs for a specific resource.

        Args:
            resource_type: Type of the resource
            resource_id: ID of the resource
            limit: Maximum number of results
            offset: Number of results to skip
            tenant_id: Filter by tenant ID

        Returns:
            List of matching audit log entries
        """
        ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        action: AuditAction | None = None,
        resource_type: AuditResourceType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Sequence[AuditLog]:
        """
        List audit logs for a specific tenant.

        Args:
            tenant_id: The tenant ID to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            action: Optional filter by action type
            resource_type: Optional filter by resource type
            start_date: Filter by minimum timestamp
            end_date: Filter by maximum timestamp

        Returns:
            List of matching audit log entries
        """
        ...

    @abstractmethod
    async def count_by_tenant(
        self,
        tenant_id: UUID,
        *,
        action: AuditAction | None = None,
        resource_type: AuditResourceType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Count audit logs for a specific tenant.

        Args:
            tenant_id: The tenant ID to filter by
            action: Optional filter by action type
            resource_type: Optional filter by resource type
            start_date: Filter by minimum timestamp
            end_date: Filter by maximum timestamp

        Returns:
            Count of matching audit log entries
        """
        ...

    @abstractmethod
    async def list_recent_logins(
        self,
        tenant_id: UUID | None = None,
        *,
        limit: int = 50,
        include_failed: bool = True,
    ) -> Sequence[AuditLog]:
        """
        List recent login attempts.

        Args:
            tenant_id: Optional tenant filter
            limit: Maximum number of results
            include_failed: Whether to include failed login attempts

        Returns:
            List of login audit log entries
        """
        ...
