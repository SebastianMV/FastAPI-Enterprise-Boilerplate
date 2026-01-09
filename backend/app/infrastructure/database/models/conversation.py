# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""SQLAlchemy model for Conversation entity."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.conversation import ConversationType
from app.infrastructure.database.connection import Base


class ConversationModel(Base):
    """
    Conversation database model.
    
    Table: conversations
    """
    
    __tablename__ = "conversations"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Tenant isolation
    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    
    # Conversation type
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ConversationType.DIRECT.value,
    )
    
    # Group-specific fields
    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Last message info
    last_message_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_message_preview: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # Message count
    message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Settings
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    send_permission: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="all",
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
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
    
    # Relationships
    participants = relationship(
        "ConversationParticipantModel",
        back_populates="conversation",
        lazy="selectin",
    )
    messages = relationship(
        "ChatMessageModel",
        back_populates="conversation",
        lazy="dynamic",
    )


class ConversationParticipantModel(Base):
    """
    Conversation participant database model.
    
    Table: conversation_participants
    """
    
    __tablename__ = "conversation_participants"
    
    # Composite primary key
    conversation_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    
    # Participation info
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    
    # Notification settings
    is_muted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    muted_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Read tracking
    last_read_message_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Role in group
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="member",
    )
    
    # Nickname override
    nickname: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # Relationships
    conversation = relationship(
        "ConversationModel",
        back_populates="participants",
    )
