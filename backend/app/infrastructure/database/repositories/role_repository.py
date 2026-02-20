# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
SQLAlchemy implementation of RoleRepository.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.role import Permission, Role
from app.domain.exceptions.base import ConflictError, EntityNotFoundError
from app.domain.ports.role_repository import RoleRepositoryPort
from app.infrastructure.database.models.role import RoleModel
from app.infrastructure.database.models.user import UserModel


class SQLAlchemyRoleRepository(RoleRepositoryPort):
    """
    SQLAlchemy implementation of role repository.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository.

        Args:
            session: Async database session
        """
        self._session = session

    async def get_by_id(self, role_id: UUID) -> Role | None:
        """Get role by ID."""
        stmt = select(RoleModel).where(
            RoleModel.id == role_id,
            RoleModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def get_by_name(self, name: str, tenant_id: UUID) -> Role | None:
        """Get role by name within a tenant."""
        stmt = select(RoleModel).where(
            RoleModel.name == name,
            RoleModel.tenant_id == tenant_id,
            RoleModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def create(self, role: Role) -> Role:
        """Create a new role."""
        model = self._to_model(role)

        try:
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)

        except IntegrityError:
            await self._session.rollback()
            raise ConflictError(
                message="A role with this name already exists",
                conflicting_field="name",
            ) from None

    async def update(self, role: Role) -> Role:
        """Update existing role."""
        stmt = select(RoleModel).where(
            RoleModel.id == role.id,
            RoleModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise EntityNotFoundError(
                entity_type="Role",
                entity_id=str(role.id),
            )

        # Update fields
        model.name = role.name
        model.description = role.description
        model.permissions = role.permission_strings
        model.updated_at = role.updated_at
        model.updated_by = role.updated_by

        await self._session.flush()
        await self._session.refresh(model)

        return self._to_entity(model)

    async def delete(self, role_id: UUID) -> None:
        """Soft delete role by ID."""
        stmt = select(RoleModel).where(
            RoleModel.id == role_id,
            RoleModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise EntityNotFoundError(
                entity_type="Role",
                entity_id=str(role_id),
            )

        if model.is_system:
            raise ConflictError(
                message="Cannot delete system role",
                conflicting_field="is_system",
            )

        from datetime import UTC, datetime

        model.is_deleted = True
        model.deleted_at = datetime.now(UTC)

        await self._session.flush()

    async def count(
        self,
        *,
        tenant_id: UUID,
    ) -> int:
        """Count roles for a tenant."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(RoleModel)
            .where(
                RoleModel.tenant_id == tenant_id,
                RoleModel.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_roles(
        self,
        *,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Role]:
        """List roles for a tenant."""
        stmt = (
            select(RoleModel)
            .where(
                RoleModel.tenant_id == tenant_id,
                RoleModel.is_deleted.is_(False),
            )
            .offset(skip)
            .limit(limit)
            .order_by(RoleModel.name)
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models]

    async def list_by_ids(self, role_ids: list[UUID]) -> list[Role]:
        """Get multiple roles by IDs."""
        if not role_ids:
            return []

        stmt = select(RoleModel).where(
            RoleModel.id.in_(role_ids),
            RoleModel.is_deleted.is_(False),
        )

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models]

    async def get_user_roles(self, user_id: UUID) -> list[Role]:
        """Get all roles assigned to a user."""
        # First get user's role IDs
        user_stmt = select(UserModel.roles).where(
            UserModel.id == user_id,
            UserModel.is_deleted.is_(False),
        )

        result = await self._session.execute(user_stmt)
        role_ids = result.scalar_one_or_none()

        if not role_ids:
            return []

        return await self.list_by_ids(role_ids)

    def _to_entity(self, model: RoleModel) -> Role:
        """Convert SQLAlchemy model to domain entity."""
        permissions = [Permission.from_string(p) for p in (model.permissions or [])]

        return Role(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            description=model.description,
            permissions=permissions,
            is_system=model.is_system,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            updated_by=model.updated_by,
        )

    def _to_model(self, entity: Role) -> RoleModel:
        """Convert domain entity to SQLAlchemy model."""
        return RoleModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            description=entity.description,
            permissions=entity.permission_strings,
            is_system=entity.is_system,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )
