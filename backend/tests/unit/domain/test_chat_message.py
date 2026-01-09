# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for ChatMessage domain entity.

Tests for chat message functionality and methods.
"""

from datetime import datetime, UTC
from uuid import uuid4

import pytest

from app.domain.entities.chat_message import (
    ChatMessage,
    MessageStatus,
    MessageContentType,
)


class TestMessageStatus:
    """Tests for MessageStatus enum."""

    def test_pending_status(self) -> None:
        """Test PENDING status."""
        assert MessageStatus.PENDING.value == "pending"

    def test_sent_status(self) -> None:
        """Test SENT status."""
        assert MessageStatus.SENT.value == "sent"

    def test_delivered_status(self) -> None:
        """Test DELIVERED status."""
        assert MessageStatus.DELIVERED.value == "delivered"

    def test_read_status(self) -> None:
        """Test READ status."""
        assert MessageStatus.READ.value == "read"


class TestMessageContentType:
    """Tests for MessageContentType enum."""

    def test_text_type(self) -> None:
        """Test TEXT content type."""
        assert MessageContentType.TEXT.value == "text"

    def test_image_type(self) -> None:
        """Test IMAGE content type."""
        assert MessageContentType.IMAGE.value == "image"

    def test_file_type(self) -> None:
        """Test FILE content type."""
        assert MessageContentType.FILE.value == "file"

    def test_audio_type(self) -> None:
        """Test AUDIO content type."""
        assert MessageContentType.AUDIO.value == "audio"

    def test_video_type(self) -> None:
        """Test VIDEO content type."""
        assert MessageContentType.VIDEO.value == "video"

    def test_location_type(self) -> None:
        """Test LOCATION content type."""
        assert MessageContentType.LOCATION.value == "location"

    def test_system_type(self) -> None:
        """Test SYSTEM content type."""
        assert MessageContentType.SYSTEM.value == "system"


class TestChatMessage:
    """Tests for ChatMessage entity."""

    def test_create_text_message(self) -> None:
        """Test creating a text message."""
        tenant_id = uuid4()
        conversation_id = uuid4()
        sender_id = uuid4()
        
        message = ChatMessage(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            sender_id=sender_id,
            content="Hello, world!",
        )
        
        assert message.tenant_id == tenant_id
        assert message.conversation_id == conversation_id
        assert message.sender_id == sender_id
        assert message.content == "Hello, world!"
        assert message.content_type == MessageContentType.TEXT

    def test_default_values(self) -> None:
        """Test default values."""
        message = ChatMessage(tenant_id=uuid4())
        
        assert message.content == ""
        assert message.content_type == MessageContentType.TEXT
        assert message.metadata == {}
        assert message.status == MessageStatus.PENDING
        assert message.delivered_at is None
        assert message.read_at is None
        assert message.reply_to_id is None
        assert message.reactions == {}
        assert message.is_edited is False
        assert message.edited_at is None

    def test_create_image_message(self) -> None:
        """Test creating an image message."""
        message = ChatMessage(
            tenant_id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="",
            content_type=MessageContentType.IMAGE,
            metadata={
                "url": "https://example.com/image.jpg",
                "name": "photo.jpg",
                "size": 12345,
            },
        )
        
        assert message.content_type == MessageContentType.IMAGE
        assert message.metadata["url"] == "https://example.com/image.jpg"
        assert message.metadata["size"] == 12345

    def test_create_location_message(self) -> None:
        """Test creating a location message."""
        message = ChatMessage(
            tenant_id=uuid4(),
            content_type=MessageContentType.LOCATION,
            metadata={
                "lat": 40.7128,
                "lng": -74.0060,
                "address": "New York, NY",
            },
        )
        
        assert message.content_type == MessageContentType.LOCATION
        assert message.metadata["lat"] == 40.7128
        assert message.metadata["lng"] == -74.0060

    def test_create_reply_message(self) -> None:
        """Test creating a reply message."""
        reply_to = uuid4()
        message = ChatMessage(
            tenant_id=uuid4(),
            content="This is a reply",
            reply_to_id=reply_to,
        )
        
        assert message.reply_to_id == reply_to


class TestChatMessageMarkSent:
    """Tests for mark_sent method."""

    def test_mark_sent(self) -> None:
        """Test marking message as sent."""
        message = ChatMessage(tenant_id=uuid4())
        
        assert message.status == MessageStatus.PENDING
        
        message.mark_sent()
        
        assert message.status == MessageStatus.SENT


class TestChatMessageMarkDelivered:
    """Tests for mark_delivered method."""

    def test_mark_delivered(self) -> None:
        """Test marking message as delivered."""
        message = ChatMessage(tenant_id=uuid4())
        message.mark_sent()
        
        before = datetime.now(UTC)
        message.mark_delivered()
        after = datetime.now(UTC)
        
        assert message.status == MessageStatus.DELIVERED
        assert message.delivered_at is not None  # Type narrowing
        assert before <= message.delivered_at <= after


class TestChatMessageMarkRead:
    """Tests for mark_read method."""

    def test_mark_read(self) -> None:
        """Test marking message as read."""
        message = ChatMessage(tenant_id=uuid4())
        message.mark_sent()
        message.mark_delivered()
        
        before = datetime.now(UTC)
        message.mark_read()
        after = datetime.now(UTC)
        
        assert message.status == MessageStatus.READ
        assert message.read_at is not None  # Type narrowing
        assert before <= message.read_at <= after


class TestChatMessageReactions:
    """Tests for reaction methods."""

    def test_add_reaction(self) -> None:
        """Test adding a reaction."""
        message = ChatMessage(tenant_id=uuid4())
        user_id = uuid4()
        
        message.add_reaction("👍", user_id)
        
        assert "👍" in message.reactions
        assert user_id in message.reactions["👍"]

    def test_add_reaction_multiple_users(self) -> None:
        """Test multiple users adding same reaction."""
        message = ChatMessage(tenant_id=uuid4())
        user1 = uuid4()
        user2 = uuid4()
        
        message.add_reaction("❤️", user1)
        message.add_reaction("❤️", user2)
        
        assert len(message.reactions["❤️"]) == 2
        assert user1 in message.reactions["❤️"]
        assert user2 in message.reactions["❤️"]

    def test_add_reaction_same_user_twice(self) -> None:
        """Test same user adding same reaction twice."""
        message = ChatMessage(tenant_id=uuid4())
        user_id = uuid4()
        
        message.add_reaction("👍", user_id)
        message.add_reaction("👍", user_id)
        
        assert len(message.reactions["👍"]) == 1

    def test_add_multiple_reactions(self) -> None:
        """Test user adding multiple different reactions."""
        message = ChatMessage(tenant_id=uuid4())
        user_id = uuid4()
        
        message.add_reaction("👍", user_id)
        message.add_reaction("❤️", user_id)
        message.add_reaction("😂", user_id)
        
        assert len(message.reactions) == 3

    def test_remove_reaction(self) -> None:
        """Test removing a reaction."""
        message = ChatMessage(tenant_id=uuid4())
        user_id = uuid4()
        
        message.add_reaction("👍", user_id)
        message.remove_reaction("👍", user_id)
        
        assert "👍" not in message.reactions

    def test_remove_reaction_keeps_others(self) -> None:
        """Test removing reaction keeps other users' reactions."""
        message = ChatMessage(tenant_id=uuid4())
        user1 = uuid4()
        user2 = uuid4()
        
        message.add_reaction("👍", user1)
        message.add_reaction("👍", user2)
        message.remove_reaction("👍", user1)
        
        assert "👍" in message.reactions
        assert user2 in message.reactions["👍"]
        assert user1 not in message.reactions["👍"]

    def test_remove_nonexistent_reaction(self) -> None:
        """Test removing a reaction that doesn't exist."""
        message = ChatMessage(tenant_id=uuid4())
        user_id = uuid4()
        
        # Should not raise error
        message.remove_reaction("👍", user_id)
        
        assert message.reactions == {}

    def test_remove_reaction_wrong_user(self) -> None:
        """Test removing reaction that user didn't add."""
        message = ChatMessage(tenant_id=uuid4())
        user1 = uuid4()
        user2 = uuid4()
        
        message.add_reaction("👍", user1)
        message.remove_reaction("👍", user2)
        
        assert user1 in message.reactions["👍"]


class TestChatMessageEdit:
    """Tests for edit method."""

    def test_edit_message(self) -> None:
        """Test editing a message."""
        message = ChatMessage(
            tenant_id=uuid4(),
            content="Original content",
        )
        
        before = datetime.now(UTC)
        message.edit("Edited content")
        after = datetime.now(UTC)
        
        assert message.content == "Edited content"
        assert message.edited_at is not None  # Type narrowing
        assert message.is_edited is True
        assert before <= message.edited_at <= after

    def test_edit_message_multiple_times(self) -> None:
        """Test editing a message multiple times."""
        message = ChatMessage(
            tenant_id=uuid4(),
            content="Original",
        )
        
        message.edit("First edit")
        first_edit_time = message.edited_at
        assert first_edit_time is not None  # Type narrowing
        
        message.edit("Second edit")
        assert message.edited_at is not None  # Type narrowing
        
        assert message.content == "Second edit"
        assert message.edited_at >= first_edit_time

    def test_edit_empty_content(self) -> None:
        """Test editing to empty content."""
        message = ChatMessage(
            tenant_id=uuid4(),
            content="Original content",
        )
        
        message.edit("")
        
        assert message.content == ""
        assert message.is_edited is True


class TestChatMessageStatusFlow:
    """Tests for message status flow."""

    def test_full_status_flow(self) -> None:
        """Test complete status flow from pending to read."""
        message = ChatMessage(tenant_id=uuid4(), content="Test")
        
        assert message.status == MessageStatus.PENDING
        assert message.delivered_at is None
        assert message.read_at is None
        
        message.mark_sent()
        assert message.status == MessageStatus.SENT
        
        message.mark_delivered()
        assert message.status == MessageStatus.DELIVERED
        assert message.delivered_at is not None
        
        message.mark_read()
        assert message.status == MessageStatus.READ
        assert message.read_at is not None
        assert message.read_at >= message.delivered_at
