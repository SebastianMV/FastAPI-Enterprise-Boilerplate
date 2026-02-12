# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Base entities for domain layer."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass
class BaseEntity:
    """
    Base entity with identity.

    All domain entities should inherit from this class.
    """

    id: UUID = field(default_factory=uuid4)

    def __eq__(self, other: Any) -> bool:
        """Entities are equal if they have the same ID."""
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on entity ID."""
        return hash(self.id)


@dataclass
class AuditableEntity(BaseEntity):
    """
    Entity with audit fields.

    Tracks creation and modification timestamps, plus the user
    who made the changes.
    """

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: UUID | None = None
    updated_by: UUID | None = None

    def mark_updated(self, by_user: UUID | None = None) -> None:
        """Mark entity as updated with current timestamp."""
        self.updated_at = datetime.now(UTC)
        if by_user:
            self.updated_by = by_user


@dataclass
class TenantEntity(AuditableEntity):
    """
    Entity scoped to a tenant.

    Used for multi-tenant data isolation. The tenant_id is
    enforced at database level via RLS policies.
    """

    tenant_id: UUID = field(default_factory=uuid4)


@dataclass
class SoftDeletableEntity(AuditableEntity):
    """
    Entity with soft delete support.

    Instead of physical deletion, entities are marked as deleted
    and filtered out in queries.

    Note: Does NOT require tenant scoping. Use ``TenantSoftDeletableEntity``
    when both tenant isolation and soft delete are needed.
    """

    is_deleted: bool = False
    deleted_at: datetime | None = None
    deleted_by: UUID | None = None

    def soft_delete(self, by_user: UUID | None = None) -> None:
        """Mark entity as deleted without physical removal."""
        self.is_deleted = True
        self.deleted_at = datetime.now(UTC)
        if by_user:
            self.deleted_by = by_user

    def restore(self) -> None:
        """Restore a soft-deleted entity."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None


@dataclass
class TenantSoftDeletableEntity(TenantEntity):
    """
    Entity with both tenant scoping and soft delete.

    Use this when an entity needs multi-tenant isolation AND
    soft-delete behaviour.
    """

    is_deleted: bool = False
    deleted_at: datetime | None = None
    deleted_by: UUID | None = None

    def soft_delete(self, by_user: UUID | None = None) -> None:
        """Mark entity as deleted without physical removal."""
        self.is_deleted = True
        self.deleted_at = datetime.now(UTC)
        if by_user:
            self.deleted_by = by_user

    def restore(self) -> None:
        """Restore a soft-deleted entity."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
