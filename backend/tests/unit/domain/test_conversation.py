# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Conversation domain entity.

Tests for conversation and participant functionality.
"""

from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest

from app.domain.entities.conversation import (
    Conversation,
    ConversationType,
    ConversationParticipant,
)


class TestConversationType:
    """Tests for ConversationType enum."""

    def test_direct_type(self) -> None:
        """Test DIRECT conversation type."""
        assert ConversationType.DIRECT.value == "direct"

    def test_group_type(self) -> None:
        """Test GROUP conversation type."""
        assert ConversationType.GROUP.value == "group"

    def test_is_string_enum(self) -> None:
        """Test that ConversationType is string enum."""
        assert str(ConversationType.DIRECT) == "ConversationType.DIRECT"
        assert isinstance(ConversationType.DIRECT.value, str)


class TestConversationParticipant:
    """Tests for ConversationParticipant dataclass."""

    def test_basic_participant(self) -> None:
        """Test creating basic participant."""
        user_id = uuid4()
        participant = ConversationParticipant(user_id=user_id)
        
        assert participant.user_id == user_id
        assert participant.is_muted is False
        assert participant.role == "member"

    def test_default_values(self) -> None:
        """Test default values."""
        participant = ConversationParticipant(user_id=uuid4())
        
        assert participant.muted_until is None
        assert participant.last_read_message_id is None
        assert participant.last_read_at is None
        assert participant.nickname is None

    def test_joined_at_default(self) -> None:
        """Test joined_at defaults to now."""
        before = datetime.now(UTC)
        participant = ConversationParticipant(user_id=uuid4())
        after = datetime.now(UTC)
        
        assert before <= participant.joined_at <= after

    def test_is_admin_for_member(self) -> None:
        """Test is_admin returns False for member."""
        participant = ConversationParticipant(user_id=uuid4(), role="member")
        
        assert participant.is_admin() is False

    def test_is_admin_for_admin(self) -> None:
        """Test is_admin returns True for admin."""
        participant = ConversationParticipant(user_id=uuid4(), role="admin")
        
        assert participant.is_admin() is True

    def test_is_admin_for_owner(self) -> None:
        """Test is_admin returns True for owner."""
        participant = ConversationParticipant(user_id=uuid4(), role="owner")
        
        assert participant.is_admin() is True

    def test_muted_participant(self) -> None:
        """Test muted participant."""
        muted_until = datetime.now(UTC) + timedelta(hours=1)
        participant = ConversationParticipant(
            user_id=uuid4(),
            is_muted=True,
            muted_until=muted_until,
        )
        
        assert participant.is_muted is True
        assert participant.muted_until == muted_until

    def test_with_read_tracking(self) -> None:
        """Test participant with read tracking."""
        message_id = uuid4()
        read_at = datetime.now(UTC)
        
        participant = ConversationParticipant(
            user_id=uuid4(),
            last_read_message_id=message_id,
            last_read_at=read_at,
        )
        
        assert participant.last_read_message_id == message_id
        assert participant.last_read_at == read_at


class TestConversation:
    """Tests for Conversation entity."""

    def test_create_direct_conversation(self) -> None:
        """Test creating direct conversation."""
        conversation = Conversation(
            tenant_id=uuid4(),
            type=ConversationType.DIRECT,
        )
        
        assert conversation.type == ConversationType.DIRECT
        assert conversation.participants == []
        assert conversation.name is None

    def test_create_group_conversation(self) -> None:
        """Test creating group conversation."""
        tenant_id = uuid4()
        conversation = Conversation(
            tenant_id=tenant_id,
            type=ConversationType.GROUP,
            name="Test Group",
            description="A test group chat",
        )
        
        assert conversation.type == ConversationType.GROUP
        assert conversation.name == "Test Group"
        assert conversation.description == "A test group chat"
        assert conversation.tenant_id == tenant_id

    def test_default_values(self) -> None:
        """Test default values."""
        conversation = Conversation(tenant_id=uuid4())
        
        assert conversation.type == ConversationType.DIRECT
        assert conversation.avatar_url is None
        assert conversation.last_message_id is None
        assert conversation.last_message_at is None
        assert conversation.last_message_preview is None
        assert conversation.message_count == 0
        assert conversation.is_archived is False
        assert conversation.send_permission == "all"


class TestConversationAddParticipant:
    """Tests for add_participant method."""

    def test_add_participant(self) -> None:
        """Test adding a participant."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        
        participant = conversation.add_participant(user_id)
        
        assert participant.user_id == user_id
        assert participant.role == "member"
        assert len(conversation.participants) == 1
        assert conversation.participants[0] == participant

    def test_add_participant_as_admin(self) -> None:
        """Test adding participant as admin."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        
        participant = conversation.add_participant(user_id, role="admin")
        
        assert participant.role == "admin"
        assert participant.is_admin() is True

    def test_add_multiple_participants(self) -> None:
        """Test adding multiple participants."""
        conversation = Conversation(tenant_id=uuid4())
        user1 = uuid4()
        user2 = uuid4()
        user3 = uuid4()
        
        conversation.add_participant(user1, role="owner")
        conversation.add_participant(user2, role="admin")
        conversation.add_participant(user3)
        
        assert len(conversation.participants) == 3
        assert conversation.participants[0].role == "owner"
        assert conversation.participants[1].role == "admin"
        assert conversation.participants[2].role == "member"


class TestConversationRemoveParticipant:
    """Tests for remove_participant method."""

    def test_remove_existing_participant(self) -> None:
        """Test removing existing participant."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        conversation.add_participant(user_id)
        
        result = conversation.remove_participant(user_id)
        
        assert result is True
        assert len(conversation.participants) == 0

    def test_remove_nonexistent_participant(self) -> None:
        """Test removing non-existent participant."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        other_id = uuid4()
        conversation.add_participant(user_id)
        
        result = conversation.remove_participant(other_id)
        
        assert result is False
        assert len(conversation.participants) == 1


class TestConversationGetParticipant:
    """Tests for get_participant method."""

    def test_get_existing_participant(self) -> None:
        """Test getting existing participant."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        conversation.add_participant(user_id, role="admin")
        
        participant = conversation.get_participant(user_id)
        
        assert participant is not None
        assert participant.user_id == user_id
        assert participant.role == "admin"

    def test_get_nonexistent_participant(self) -> None:
        """Test getting non-existent participant."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        
        participant = conversation.get_participant(user_id)
        
        assert participant is None


class TestConversationIsParticipant:
    """Tests for is_participant method."""

    def test_is_participant_true(self) -> None:
        """Test is_participant returns True for participant."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        conversation.add_participant(user_id)
        
        assert conversation.is_participant(user_id) is True

    def test_is_participant_false(self) -> None:
        """Test is_participant returns False for non-participant."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        
        assert conversation.is_participant(user_id) is False


class TestConversationGetOtherParticipant:
    """Tests for get_other_participant method."""

    def test_get_other_in_direct_chat(self) -> None:
        """Test getting other participant in direct chat."""
        conversation = Conversation(
            tenant_id=uuid4(),
            type=ConversationType.DIRECT,
        )
        user1 = uuid4()
        user2 = uuid4()
        conversation.add_participant(user1)
        conversation.add_participant(user2)
        
        other = conversation.get_other_participant(user1)
        
        assert other == user2

    def test_get_other_in_group_chat_returns_none(self) -> None:
        """Test get_other_participant returns None for group chat."""
        conversation = Conversation(
            tenant_id=uuid4(),
            type=ConversationType.GROUP,
        )
        user1 = uuid4()
        user2 = uuid4()
        conversation.add_participant(user1)
        conversation.add_participant(user2)
        
        other = conversation.get_other_participant(user1)
        
        assert other is None

    def test_get_other_only_one_participant(self) -> None:
        """Test get_other_participant with only one participant."""
        conversation = Conversation(
            tenant_id=uuid4(),
            type=ConversationType.DIRECT,
        )
        user_id = uuid4()
        conversation.add_participant(user_id)
        
        other = conversation.get_other_participant(user_id)
        
        assert other is None


class TestConversationUpdateLastMessage:
    """Tests for update_last_message method."""

    def test_update_last_message(self) -> None:
        """Test updating last message."""
        conversation = Conversation(tenant_id=uuid4())
        message_id = uuid4()
        preview = "Hello, world!"
        
        before = datetime.now(UTC)
        conversation.update_last_message(message_id, preview)
        after = datetime.now(UTC)
        
        assert conversation.last_message_id == message_id
        assert conversation.last_message_preview == preview
        assert conversation.last_message_at is not None
        assert conversation.last_message_at is not None  # Type narrowing
        assert before <= conversation.last_message_at <= after
        assert conversation.message_count == 1

    def test_update_last_message_with_timestamp(self) -> None:
        """Test updating last message with custom timestamp."""
        conversation = Conversation(tenant_id=uuid4())
        message_id = uuid4()
        timestamp = datetime.now(UTC) - timedelta(hours=1)
        
        conversation.update_last_message(message_id, "Test", timestamp)
        
        assert conversation.last_message_at == timestamp

    def test_update_last_message_truncates_preview(self) -> None:
        """Test that long previews are truncated."""
        conversation = Conversation(tenant_id=uuid4())
        message_id = uuid4()
        long_preview = "x" * 200
        
        conversation.update_last_message(message_id, long_preview)
        
        assert conversation.last_message_preview is not None
        assert len(conversation.last_message_preview) == 100

    def test_update_last_message_increments_count(self) -> None:
        """Test that message count is incremented."""
        conversation = Conversation(tenant_id=uuid4())
        
        conversation.update_last_message(uuid4(), "Message 1")
        conversation.update_last_message(uuid4(), "Message 2")
        conversation.update_last_message(uuid4(), "Message 3")
        
        assert conversation.message_count == 3

    def test_update_last_message_empty_preview(self) -> None:
        """Test updating with empty preview."""
        conversation = Conversation(tenant_id=uuid4())
        
        conversation.update_last_message(uuid4(), "")
        
        assert conversation.last_message_preview is None


class TestConversationGetUnreadCount:
    """Tests for get_unread_count method."""

    def test_unread_count_for_non_participant(self) -> None:
        """Test unread count for non-participant returns message count."""
        conversation = Conversation(tenant_id=uuid4())
        conversation.message_count = 10
        user_id = uuid4()
        
        count = conversation.get_unread_count(user_id)
        
        assert count == 10

    def test_unread_count_no_last_read(self) -> None:
        """Test unread count when user never read messages."""
        conversation = Conversation(tenant_id=uuid4())
        conversation.message_count = 5
        user_id = uuid4()
        conversation.add_participant(user_id)
        
        count = conversation.get_unread_count(user_id)
        
        assert count == 5

    def test_unread_count_all_read(self) -> None:
        """Test unread count when all messages are read."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        conversation.add_participant(user_id)
        conversation.update_last_message(uuid4(), "Test")
        
        # Mark as read after last message
        participant = conversation.get_participant(user_id)
        assert participant is not None
        participant.last_read_at = datetime.now(UTC)
        
        count = conversation.get_unread_count(user_id)
        
        assert count == 0


class TestConversationCanSendMessage:
    """Tests for can_send_message method."""

    def test_non_participant_cannot_send(self) -> None:
        """Test non-participant cannot send message."""
        conversation = Conversation(tenant_id=uuid4())
        user_id = uuid4()
        
        result = conversation.can_send_message(user_id)
        
        assert result is False

    def test_participant_can_send_with_all_permission(self) -> None:
        """Test participant can send with 'all' permission."""
        conversation = Conversation(
            tenant_id=uuid4(),
            send_permission="all",
        )
        user_id = uuid4()
        conversation.add_participant(user_id)
        
        result = conversation.can_send_message(user_id)
        
        assert result is True

    def test_member_cannot_send_with_admins_permission(self) -> None:
        """Test member cannot send with 'admins' permission."""
        conversation = Conversation(
            tenant_id=uuid4(),
            send_permission="admins",
        )
        user_id = uuid4()
        conversation.add_participant(user_id, role="member")
        
        result = conversation.can_send_message(user_id)
        
        assert result is False

    def test_admin_can_send_with_admins_permission(self) -> None:
        """Test admin can send with 'admins' permission."""
        conversation = Conversation(
            tenant_id=uuid4(),
            send_permission="admins",
        )
        user_id = uuid4()
        conversation.add_participant(user_id, role="admin")
        
        result = conversation.can_send_message(user_id)
        
        assert result is True

    def test_owner_can_send_with_admins_permission(self) -> None:
        """Test owner can send with 'admins' permission."""
        conversation = Conversation(
            tenant_id=uuid4(),
            send_permission="admins",
        )
        user_id = uuid4()
        conversation.add_participant(user_id, role="owner")
        
        result = conversation.can_send_message(user_id)
        
        assert result is True
