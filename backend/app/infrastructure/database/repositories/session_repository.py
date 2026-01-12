# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
SQLAlchemy implementation of SessionRepository.

Handles user session persistence and retrieval.
"""

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.session import UserSession
from app.infrastructure.database.models.session import UserSessionModel


class SQLAlchemySessionRepository:
    """
    SQLAlchemy implementation of session repository.
    
    Manages user sessions in the database.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self._session = session
    
    async def create(self, user_session: UserSession) -> UserSession:
        """Create a new session record."""
        model = self._to_model(user_session)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
    
    async def get_by_id(self, session_id: UUID) -> UserSession | None:
        """Get session by ID."""
        stmt = select(UserSessionModel).where(
            UserSessionModel.id == session_id,
            UserSessionModel.is_revoked == False,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        """Get session by refresh token hash."""
        stmt = select(UserSessionModel).where(
            UserSessionModel.refresh_token_hash == token_hash,
            UserSessionModel.is_revoked == False,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
    
    async def get_user_sessions(
        self, 
        user_id: UUID, 
        include_revoked: bool = False
    ) -> list[UserSession]:
        """Get all sessions for a user."""
        stmt = select(UserSessionModel).where(
            UserSessionModel.user_id == user_id,
        ).order_by(UserSessionModel.last_activity.desc())
        
        if not include_revoked:
            stmt = stmt.where(UserSessionModel.is_revoked == False)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]
    
    async def revoke(self, session_id: UUID) -> bool:
        """Revoke a specific session."""
        stmt = (
            update(UserSessionModel)
            .where(
                UserSessionModel.id == session_id,
                UserSessionModel.is_revoked == False,
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0  # type: ignore[union-attr]
    
    async def revoke_all_except(self, user_id: UUID, current_session_id: UUID) -> int:
        """Revoke all sessions for a user except the current one."""
        stmt = (
            update(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.id != current_session_id,
                UserSessionModel.is_revoked == False,
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[union-attr]
    
    async def revoke_all(self, user_id: UUID) -> int:
        """Revoke all sessions for a user."""
        stmt = (
            update(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.is_revoked == False,
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[union-attr]
    
    async def update_activity(
        self, 
        session_id: UUID, 
        ip_address: str | None = None
    ) -> None:
        """Update last activity for a session."""
        values: dict[str, Any] = {"last_activity": datetime.now(UTC)}
        if ip_address:
            values["ip_address"] = ip_address
        
        stmt = (
            update(UserSessionModel)
            .where(UserSessionModel.id == session_id)
            .values(**values)
        )
        await self._session.execute(stmt)
    
    async def cleanup_old_sessions(self, older_than: datetime) -> int:
        """Delete sessions older than specified date."""
        stmt = delete(UserSessionModel).where(
            UserSessionModel.created_at < older_than,
            UserSessionModel.is_revoked == True,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount  # type: ignore[union-attr]
    
    def _to_entity(self, model: UserSessionModel) -> UserSession:
        """Convert SQLAlchemy model to domain entity."""
        return UserSession(
            id=model.id,  # type: ignore[arg-type]
            tenant_id=model.tenant_id,  # type: ignore[arg-type]
            user_id=model.user_id,  # type: ignore[arg-type]
            refresh_token_hash=model.refresh_token_hash,
            device_name=model.device_name,
            device_type=model.device_type,
            browser=model.browser,
            os=model.os,
            ip_address=model.ip_address,
            location=model.location,
            last_activity=model.last_activity,
            is_revoked=model.is_revoked,
            revoked_at=model.revoked_at,
            created_at=model.created_at,
        )
    
    def _to_model(self, entity: UserSession) -> UserSessionModel:
        """Convert domain entity to SQLAlchemy model."""
        return UserSessionModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            user_id=entity.user_id,
            refresh_token_hash=entity.refresh_token_hash,
            device_name=entity.device_name,
            device_type=entity.device_type,
            browser=entity.browser,
            os=entity.os,
            ip_address=entity.ip_address,
            location=entity.location,
            last_activity=entity.last_activity,
            is_revoked=entity.is_revoked,
            revoked_at=entity.revoked_at,
            created_at=entity.created_at,
        )
