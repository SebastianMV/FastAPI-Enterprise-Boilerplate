# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
SQLAlchemy model for UserSession entity.

Maps domain UserSession entity to database table.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.tenant import TenantModel
    from app.infrastructure.database.models.user import UserModel


class UserSessionModel(Base):
    """
    User session database model.

    Table: user_sessions
    Tracks active user sessions for session management.
    """

    __tablename__ = "user_sessions"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User reference
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Session identification
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Device information
    device_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )
    device_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="desktop",
    )
    browser: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )
    os: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )

    # Location information
    ip_address: Mapped[str] = mapped_column(
        String(45),  # IPv6 max length
        nullable=False,
        default="",
    )
    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )

    # Activity tracking
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Session status
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        lazy="select",
    )

    tenant: Mapped["TenantModel"] = relationship(
        "TenantModel",
        lazy="select",
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<UserSession(id={self.id}, user_id={self.user_id}, device={self.device_name})>"
