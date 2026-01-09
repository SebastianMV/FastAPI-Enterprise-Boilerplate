# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Conversation domain entity.

Represents a chat conversation between users (1:1 or group).
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID

from app.domain.entities.base import TenantEntity


class ConversationType(str, Enum):
    """Type of conversation."""
    
    DIRECT = "direct"  # 1:1 conversation
    GROUP = "group"    # Group conversation


@dataclass
class ConversationParticipant:
    """
    Participant in a conversation.
    
    Tracks individual user settings within a conversation.
    """
    
    user_id: UUID
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    # Notification settings
    is_muted: bool = False
    muted_until: datetime | None = None
    
    # Read tracking
    last_read_message_id: UUID | None = None
    last_read_at: datetime | None = None
    
    # Role in group (for group chats)
    role: str = "member"  # member, admin, owner
    
    # Nickname override (for group chats)
    nickname: str | None = None
    
    def is_admin(self) -> bool:
        """Check if participant is admin or owner."""
        return self.role in ("admin", "owner")


@dataclass
class Conversation(TenantEntity):
    """
    Conversation domain entity.
    
    Represents a chat thread between two or more users.
    """
    
    # Conversation type
    type: ConversationType = ConversationType.DIRECT
    
    # Participants
    participants: list[ConversationParticipant] = field(default_factory=list)
    
    # Group-specific fields
    name: str | None = None  # Only for group chats
    description: str | None = None
    avatar_url: str | None = None
    
    # Last message info (for conversation list)
    last_message_id: UUID | None = None
    last_message_at: datetime | None = None
    last_message_preview: str | None = None
    
    # Message count
    message_count: int = 0
    
    # Settings
    is_archived: bool = False
    
    # For group chats: who can send messages
    # "all" = everyone, "admins" = only admins
    send_permission: str = "all"
    
    def add_participant(
        self,
        user_id: UUID,
        role: str = "member",
    ) -> ConversationParticipant:
        """Add a participant to the conversation."""
        participant = ConversationParticipant(
            user_id=user_id,
            role=role,
        )
        self.participants.append(participant)
        return participant
    
    def remove_participant(self, user_id: UUID) -> bool:
        """Remove a participant from the conversation."""
        for i, p in enumerate(self.participants):
            if p.user_id == user_id:
                self.participants.pop(i)
                return True
        return False
    
    def get_participant(self, user_id: UUID) -> ConversationParticipant | None:
        """Get participant info for a user."""
        for p in self.participants:
            if p.user_id == user_id:
                return p
        return None
    
    def is_participant(self, user_id: UUID) -> bool:
        """Check if user is a participant."""
        return any(p.user_id == user_id for p in self.participants)
    
    def get_other_participant(self, user_id: UUID) -> UUID | None:
        """For direct chats, get the other participant's ID."""
        if self.type != ConversationType.DIRECT:
            return None
        
        for p in self.participants:
            if p.user_id != user_id:
                return p.user_id
        return None
    
    def update_last_message(
        self,
        message_id: UUID,
        preview: str,
        timestamp: datetime | None = None,
    ) -> None:
        """Update last message info."""
        self.last_message_id = message_id
        self.last_message_at = timestamp or datetime.now(UTC)
        self.last_message_preview = preview[:100] if preview else None
        self.message_count += 1
    
    def get_unread_count(self, user_id: UUID) -> int:
        """Get unread message count for a user."""
        participant = self.get_participant(user_id)
        if not participant or not participant.last_read_at:
            return self.message_count
        
        # This would need to be calculated from actual messages
        # For now, return 0 if last_read_at is after last_message_at
        if participant.last_read_at >= (self.last_message_at or datetime.min.replace(tzinfo=UTC)):
            return 0
        
        return 1  # Placeholder - actual count from messages table
    
    def can_send_message(self, user_id: UUID) -> bool:
        """Check if user can send messages in this conversation."""
        participant = self.get_participant(user_id)
        if not participant:
            return False
        
        if self.send_permission == "all":
            return True
        
        return participant.is_admin()
