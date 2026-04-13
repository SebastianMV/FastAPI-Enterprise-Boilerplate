# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Repository port (interface) for Role entity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.domain.entities.role import Role


class RoleRepositoryPort(ABC):
    """
    Abstract repository for Role entity.
    """

    @abstractmethod
    async def get_by_id(self, role_id: UUID) -> Role | None:
        """Get role by ID."""
        ...

    @abstractmethod
    async def get_by_name(self, name: str, tenant_id: UUID) -> Role | None:
        """Get role by name within a tenant."""
        ...

    @abstractmethod
    async def create(self, role: Role) -> Role:
        """Create a new role."""
        ...

    @abstractmethod
    async def update(self, role: Role) -> Role:
        """Update existing role."""
        ...

    @abstractmethod
    async def delete(self, role_id: UUID) -> None:
        """Delete role by ID (soft delete)."""
        ...

    @abstractmethod
    async def list_roles(
        self,
        *,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Role]:
        """List roles for a tenant."""
        ...

    @abstractmethod
    async def list_by_ids(self, role_ids: list[UUID]) -> list[Role]:
        """Get multiple roles by IDs."""
        ...

    @abstractmethod
    async def get_user_roles(self, user_id: UUID) -> list[Role]:
        """Get all roles assigned to a user."""
        ...
