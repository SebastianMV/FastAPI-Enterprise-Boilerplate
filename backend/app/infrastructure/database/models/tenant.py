# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""SQLAlchemy model for Tenant."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base
from app.infrastructure.database.models.custom_types import JSONBCompat

if TYPE_CHECKING:
    from app.infrastructure.database.models.user import UserModel


class TenantModel(Base):
    """
    SQLAlchemy model for tenants table.

    This is the root entity for multi-tenant isolation.
    RLS policies filter all tenant-scoped tables by tenant_id.
    """

    __tablename__ = "tenants"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Contact
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Subscription
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    plan_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Settings (JSONB for flexibility)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONBCompat,
        default=dict,
        nullable=False,
    )

    # Metadata
    domain: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Relationships
    users: Mapped[list["UserModel"]] = relationship(
        "UserModel",
        back_populates="tenant",
        lazy="raise",
        # NOTE: lazy="raise" prevents accidental eager loading of ALL tenant
        # users. Use explicit joinedload/selectinload when needed.
        # Previous lazy="selectin" caused an N+1 bomb on tenant queries.
    )

    # Indexes
    __table_args__ = (
        Index("ix_tenants_is_active", "is_active"),
        Index("ix_tenants_plan", "plan"),
        Index("ix_tenants_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id})>"
