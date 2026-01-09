# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Chat message domain entity.

Represents a message in a conversation between users.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID

from app.domain.entities.base import TenantEntity


class MessageStatus(str, Enum):
    """Message delivery status."""
    
    PENDING = "pending"      # Not yet sent to server
    SENT = "sent"            # Sent to server, not delivered
    DELIVERED = "delivered"  # Delivered to recipient's device
    READ = "read"            # Read by recipient


class MessageContentType(str, Enum):
    """Type of message content."""
    
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    SYSTEM = "system"  # System-generated messages


@dataclass
class ChatMessage(TenantEntity):
    """
    Chat message domain entity.
    
    Represents a single message in a conversation.
    Supports various content types and delivery tracking.
    """
    
    # Conversation reference
    conversation_id: UUID = field(default_factory=lambda: UUID(int=0))
    
    # Sender
    sender_id: UUID = field(default_factory=lambda: UUID(int=0))
    
    # Content
    content: str = ""
    content_type: MessageContentType = MessageContentType.TEXT
    
    # Optional metadata for non-text content
    # For images/files: {"url": "...", "name": "...", "size": 123}
    # For location: {"lat": 0.0, "lng": 0.0, "address": "..."}
    metadata: dict = field(default_factory=dict)
    
    # Delivery tracking
    status: MessageStatus = MessageStatus.PENDING
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    
    # Reply reference (for threaded messages)
    reply_to_id: UUID | None = None
    
    # Reactions (emoji -> list of user_ids)
    reactions: dict[str, list[UUID]] = field(default_factory=dict)
    
    # Edit history
    is_edited: bool = False
    edited_at: datetime | None = None
    
    def mark_sent(self) -> None:
        """Mark message as sent to server."""
        self.status = MessageStatus.SENT
    
    def mark_delivered(self) -> None:
        """Mark message as delivered to recipient."""
        self.status = MessageStatus.DELIVERED
        self.delivered_at = datetime.now(UTC)
    
    def mark_read(self) -> None:
        """Mark message as read by recipient."""
        self.status = MessageStatus.READ
        self.read_at = datetime.now(UTC)
    
    def add_reaction(self, emoji: str, user_id: UUID) -> None:
        """Add a reaction from a user."""
        if emoji not in self.reactions:
            self.reactions[emoji] = []
        if user_id not in self.reactions[emoji]:
            self.reactions[emoji].append(user_id)
    
    def remove_reaction(self, emoji: str, user_id: UUID) -> None:
        """Remove a reaction from a user."""
        if emoji in self.reactions and user_id in self.reactions[emoji]:
            self.reactions[emoji].remove(user_id)
            if not self.reactions[emoji]:
                del self.reactions[emoji]
    
    def edit(self, new_content: str) -> None:
        """Edit the message content."""
        self.content = new_content
        self.is_edited = True
        self.edited_at = datetime.now(UTC)
