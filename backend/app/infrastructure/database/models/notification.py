# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""SQLAlchemy model for Notification entity."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.notification import NotificationPriority, NotificationType
from app.infrastructure.database.connection import Base
from app.infrastructure.database.models.custom_types import JSONEncodedList, JSONBCompat


class NotificationModel(Base):
    """
    Notification database model.
    
    Table: notifications
    """
    
    __tablename__ = "notifications"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Tenant isolation
    tenant_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,  # Null for system-wide notifications
        index=True,
    )
    
    # Target user
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Notification content
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=NotificationType.INFO.value,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # Rich content metadata
    extra_data: Mapped[dict] = mapped_column(
        "metadata",  # Column name in DB
        JSONBCompat,
        nullable=False,
        server_default="{}",
    )
    
    # Priority and categorization
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=NotificationPriority.NORMAL.value,
    )
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    
    # Delivery channels
    channels: Mapped[list[str]] = mapped_column(
        JSONEncodedList,
        nullable=False,
        server_default="{}",
    )
    
    # Delivery status per channel
    delivery_status: Mapped[dict] = mapped_column(
        JSONBCompat,
        nullable=False,
        server_default="{}",
    )
    
    # Read status
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Grouping
    group_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    
    # Action tracking
    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    action_clicked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    action_clicked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )
    
    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
