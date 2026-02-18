# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
SQLAlchemy implementation of UserRepository.

Implements the UserRepositoryPort interface for PostgreSQL.
Optimized with eager loading to avoid N+1 queries.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.user import User
from app.domain.exceptions.base import ConflictError, EntityNotFoundError
from app.domain.ports.user_repository import UserRepositoryPort
from app.domain.value_objects.email import Email
from app.infrastructure.database.models.user import UserModel


class SQLAlchemyUserRepository(UserRepositoryPort):
    """
    SQLAlchemy implementation of user repository.

    Uses async session for non-blocking database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository.

        Args:
            session: Async database session
        """
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID with eager loading to avoid N+1."""
        stmt = (
            select(UserModel)
            .options(
                selectinload(UserModel.tenant),
                selectinload(UserModel.oauth_connections),
            )
            .where(
                UserModel.id == user_id,
                UserModel.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address with eager loading."""
        normalized_email = email.lower().strip()

        stmt = (
            select(UserModel)
            .options(
                selectinload(UserModel.tenant),
                selectinload(UserModel.oauth_connections),
            )
            .where(
                UserModel.email == normalized_email,
                UserModel.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        return self._to_entity(model) if model else None

    async def create(self, user: User) -> User:
        """Create a new user."""
        model = self._to_model(user)

        try:
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return self._to_entity(model)

        except IntegrityError as e:
            await self._session.rollback()
            constraint = getattr(e.orig, "constraint_name", "") or ""
            orig_str = str(e.orig) if not constraint else ""
            if "email" in constraint or "email" in orig_str:
                raise ConflictError(
                    message="A user with this email already exists",
                    conflicting_field="email",
                ) from e
            raise

    async def update(self, user: User) -> User:
        """Update existing user."""
        stmt = select(UserModel).where(
            UserModel.id == user.id,
            UserModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise EntityNotFoundError(
                entity_type="User",
                entity_id=str(user.id),
            )

        # Update fields
        model.email = str(user.email)
        model.password_hash = user.password_hash
        model.first_name = user.first_name
        model.last_name = user.last_name
        model.is_active = user.is_active
        model.is_superuser = user.is_superuser
        model.last_login = user.last_login
        model.roles = user.roles  # pyright: ignore[reportAttributeAccessIssue]
        # Account Lockout
        model.failed_login_attempts = user.failed_login_attempts
        model.locked_until = user.locked_until
        # Email Verification
        model.email_verified = user.email_verified
        model.email_verification_token = user.email_verification_token
        model.email_verification_sent_at = user.email_verification_sent_at
        # Avatar
        model.avatar_url = user.avatar_url
        # Timestamps
        model.updated_at = user.updated_at
        model.updated_by = user.updated_by  # pyright: ignore[reportAttributeAccessIssue]

        await self._session.flush()
        await self._session.refresh(model)

        return self._to_entity(model)

    async def delete(self, user_id: UUID) -> None:
        """Soft delete user by ID."""
        stmt = select(UserModel).where(
            UserModel.id == user_id,
            UserModel.is_deleted.is_(False),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise EntityNotFoundError(
                message="",
                entity_type="User",
                entity_id=str(user_id),
            )

        from datetime import UTC, datetime

        model.is_deleted = True
        model.deleted_at = datetime.now(UTC)

        await self._session.flush()

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        tenant_id: UUID | None = None,
    ) -> list[User]:
        """List users with pagination, eager loading, and tenant isolation."""
        stmt = (
            select(UserModel)
            .options(
                selectinload(UserModel.tenant),
            )
            .where(UserModel.is_deleted.is_(False))
        )

        if tenant_id is not None:
            stmt = stmt.where(UserModel.tenant_id == tenant_id)

        if is_active is not None:
            stmt = stmt.where(UserModel.is_active.is_(is_active))

        stmt = stmt.offset(skip).limit(limit).order_by(UserModel.created_at.desc())

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models]

    async def count(
        self, *, is_active: bool | None = None, tenant_id: UUID | None = None
    ) -> int:
        """Count users matching criteria."""
        stmt = select(func.count(UserModel.id)).where(UserModel.is_deleted.is_(False))

        if tenant_id is not None:
            stmt = stmt.where(UserModel.tenant_id == tenant_id)

        if is_active is not None:
            stmt = stmt.where(UserModel.is_active.is_(is_active))

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def exists_by_email(self, email: str) -> bool:
        """Check if user with email exists."""
        normalized_email = email.lower().strip()

        stmt = select(func.count(UserModel.id)).where(
            UserModel.email == normalized_email,
            UserModel.is_deleted.is_(False),
        )

        result = await self._session.execute(stmt)
        count = result.scalar_one()

        return count > 0

    def _to_entity(self, model: UserModel) -> User:  # pyright: ignore[reportReturnType]
        """Convert SQLAlchemy model to domain entity."""
        return User(
            id=model.id,  # pyright: ignore[reportArgumentType]
            tenant_id=model.tenant_id,  # pyright: ignore[reportArgumentType]
            email=Email(model.email),
            password_hash=model.password_hash,
            first_name=model.first_name,
            last_name=model.last_name,
            is_active=model.is_active,
            is_superuser=model.is_superuser,
            last_login=model.last_login,
            roles=list(model.roles) if model.roles else [],  # pyright: ignore[reportArgumentType]
            # Account Lockout
            failed_login_attempts=model.failed_login_attempts,
            locked_until=model.locked_until,
            # Email Verification
            email_verified=model.email_verified,
            email_verification_token=model.email_verification_token,
            email_verification_sent_at=model.email_verification_sent_at,
            # Timestamps
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,  # pyright: ignore[reportArgumentType]
            updated_by=model.updated_by,  # pyright: ignore[reportArgumentType]
            is_deleted=model.is_deleted,
            deleted_at=model.deleted_at,
            deleted_by=model.deleted_by,  # pyright: ignore[reportArgumentType]
        )

    def _to_model(self, entity: User) -> UserModel:
        """Convert domain entity to SQLAlchemy model."""
        return UserModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            email=str(entity.email),
            password_hash=entity.password_hash,
            first_name=entity.first_name,
            last_name=entity.last_name,
            is_active=entity.is_active,
            is_superuser=entity.is_superuser,
            last_login=entity.last_login,
            roles=entity.roles,
            # Account Lockout
            failed_login_attempts=entity.failed_login_attempts,
            locked_until=entity.locked_until,
            # Email Verification
            email_verified=entity.email_verified,
            email_verification_token=entity.email_verification_token,
            email_verification_sent_at=entity.email_verification_sent_at,
            # Timestamps
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at,
            deleted_by=entity.deleted_by,
        )
