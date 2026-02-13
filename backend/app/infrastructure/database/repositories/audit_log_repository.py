# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
SQLAlchemy implementation of the AuditLog repository.

Implements the AuditLogRepository port from the domain layer.
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.audit_log import AuditAction, AuditLog, AuditResourceType
from app.domain.ports.audit_log_repository import (
    AuditLogRepository as AuditLogRepositoryPort,
)
from app.infrastructure.database.models.audit_log import AuditLogModel


class SQLAlchemyAuditLogRepository(AuditLogRepositoryPort):
    """
    SQLAlchemy implementation of AuditLogRepository.

    Handles persistence of audit log entries to PostgreSQL.
    This implementation is append-only - no updates or deletes.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    def _to_model(self, entity: AuditLog) -> AuditLogModel:
        """Convert domain entity to database model."""
        return AuditLogModel(
            id=entity.id,
            timestamp=entity.timestamp,
            actor_id=entity.actor_id,
            actor_email=entity.actor_email,
            actor_ip=entity.actor_ip,
            actor_user_agent=entity.actor_user_agent,
            action=entity.action.value,
            resource_type=entity.resource_type.value,
            resource_id=entity.resource_id,
            resource_name=entity.resource_name,
            tenant_id=entity.tenant_id,
            old_value=entity.old_value,
            new_value=entity.new_value,
            metadata=entity.metadata,
            reason=entity.reason,
        )

    def _to_entity(self, model: AuditLogModel) -> AuditLog:
        """Convert database model to domain entity."""
        from uuid import UUID as PyUUID

        return AuditLog(
            id=PyUUID(str(model.id)),
            timestamp=model.timestamp,
            actor_id=PyUUID(str(model.actor_id)) if model.actor_id else None,
            actor_email=model.actor_email,
            actor_ip=model.actor_ip,
            actor_user_agent=model.actor_user_agent,
            action=AuditAction(model.action),
            resource_type=AuditResourceType(model.resource_type),
            resource_id=model.resource_id,
            resource_name=model.resource_name,
            tenant_id=PyUUID(str(model.tenant_id)) if model.tenant_id else None,
            old_value=model.old_value,
            new_value=model.new_value,
            metadata=model.metadata or {},
            reason=model.reason,
        )

    async def create(self, audit_log: AuditLog) -> AuditLog:
        """Create a new audit log entry."""
        model = self._to_model(audit_log)
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def create_many(self, audit_logs: list[AuditLog]) -> list[AuditLog]:
        """Create multiple audit log entries in a single transaction."""
        models = [self._to_model(log) for log in audit_logs]
        self._session.add_all(models)
        await self._session.flush()
        return [self._to_entity(model) for model in models]

    async def get_by_id(self, audit_id: UUID) -> AuditLog | None:
        """Retrieve an audit log entry by ID."""
        result = await self._session.execute(
            select(AuditLogModel).where(AuditLogModel.id == audit_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_actor(
        self,
        actor_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        tenant_id: UUID | None = None,
    ) -> Sequence[AuditLog]:
        """List audit logs for a specific actor."""
        query = select(AuditLogModel).where(AuditLogModel.actor_id == actor_id)

        if tenant_id:
            query = query.where(AuditLogModel.tenant_id == tenant_id)
        if start_date:
            query = query.where(AuditLogModel.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLogModel.timestamp <= end_date)

        query = query.order_by(AuditLogModel.timestamp.desc())
        query = query.limit(limit).offset(offset)

        result = await self._session.execute(query)
        return [self._to_entity(model) for model in result.scalars()]

    async def list_by_resource(
        self,
        resource_type: AuditResourceType,
        resource_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        tenant_id: UUID | None = None,
    ) -> Sequence[AuditLog]:
        """List audit logs for a specific resource."""
        query = (
            select(AuditLogModel)
            .where(AuditLogModel.resource_type == resource_type.value)
            .where(AuditLogModel.resource_id == resource_id)
        )

        if tenant_id:
            query = query.where(AuditLogModel.tenant_id == tenant_id)

        query = (
            query.order_by(AuditLogModel.timestamp.desc()).limit(limit).offset(offset)
        )

        result = await self._session.execute(query)
        return [self._to_entity(model) for model in result.scalars()]

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
        """List audit logs for a specific tenant."""
        query = select(AuditLogModel).where(AuditLogModel.tenant_id == tenant_id)

        if action:
            query = query.where(AuditLogModel.action == action.value)
        if resource_type:
            query = query.where(AuditLogModel.resource_type == resource_type.value)
        if start_date:
            query = query.where(AuditLogModel.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLogModel.timestamp <= end_date)

        query = query.order_by(AuditLogModel.timestamp.desc())
        query = query.limit(limit).offset(offset)

        result = await self._session.execute(query)
        return [self._to_entity(model) for model in result.scalars()]

    async def count_by_tenant(
        self,
        tenant_id: UUID,
        *,
        action: AuditAction | None = None,
        resource_type: AuditResourceType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Count audit logs for a specific tenant."""
        query = select(func.count(AuditLogModel.id)).where(
            AuditLogModel.tenant_id == tenant_id
        )

        if action:
            query = query.where(AuditLogModel.action == action.value)
        if resource_type:
            query = query.where(AuditLogModel.resource_type == resource_type.value)
        if start_date:
            query = query.where(AuditLogModel.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLogModel.timestamp <= end_date)

        result = await self._session.execute(query)
        return result.scalar_one()

    async def list_recent_logins(
        self,
        tenant_id: UUID | None = None,
        *,
        limit: int = 50,
        include_failed: bool = True,
    ) -> Sequence[AuditLog]:
        """List recent login attempts."""
        login_actions = [AuditAction.LOGIN.value]
        if include_failed:
            login_actions.append(AuditAction.LOGIN_FAILED.value)

        query = select(AuditLogModel).where(AuditLogModel.action.in_(login_actions))

        if tenant_id:
            query = query.where(AuditLogModel.tenant_id == tenant_id)

        query = query.order_by(AuditLogModel.timestamp.desc()).limit(limit)

        result = await self._session.execute(query)
        return [self._to_entity(model) for model in result.scalars()]
