# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
SQLAlchemy model for Audit Log entity.

Maps domain AuditLog entity to database table.
This table is append-only for compliance and security.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base
from app.infrastructure.database.models.custom_types import JSONBCompat


class AuditLogModel(Base):
    """
    Audit Log database model.

    Table: audit_logs

    This table stores immutable audit trail entries.
    No UPDATE or DELETE operations should be performed on this table.

    Indexes are optimized for common query patterns:
    - By actor (who did what)
    - By resource (what happened to this resource)
    - By tenant + timestamp (tenant activity)
    - By action type (security monitoring)
    """

    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Timestamp (when)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Actor information (who)
    actor_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    actor_ip: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    actor_user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Action (what)
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Resource (which)
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    resource_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Tenant context
    tenant_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Change details (stored as JSONB for flexibility)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
    )
    new_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONBCompat,
        nullable=True,
    )

    # Additional context
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # Column name in DB
        JSONBCompat,
        nullable=True,
        default=dict,
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        # For querying resource history
        Index(
            "ix_audit_logs_resource",
            "resource_type",
            "resource_id",
            "timestamp",
        ),
        # For tenant activity reports
        Index(
            "ix_audit_logs_tenant_activity",
            "tenant_id",
            "timestamp",
        ),
        # For security monitoring (login attempts, etc.)
        Index(
            "ix_audit_logs_security",
            "action",
            "timestamp",
        ),
        # For user activity reports
        Index(
            "ix_audit_logs_actor_activity",
            "actor_id",
            "timestamp",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"resource={self.resource_type}/{self.resource_id})>"
        )
