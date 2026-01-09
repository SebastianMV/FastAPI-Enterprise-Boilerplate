# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for chat endpoints module."""

from datetime import datetime, timezone as tz
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

# Import schemas from chat endpoints
from app.api.v1.endpoints.chat import (
    ParticipantResponse,
    ConversationResponse,
    MessageResponse,
    CreateDirectConversationRequest,
    CreateGroupConversationRequest,
    SendMessageRequest,
)


class TestParticipantResponseSchema:
    """Tests for ParticipantResponse schema."""

    def test_participant_response_minimal(self) -> None:
        """Test participant response with minimal fields."""
        response = ParticipantResponse(
            user_id="user-123",
            role="member",
            joined_at="2024-01-01T00:00:00Z",
        )
        assert response.user_id == "user-123"
        assert response.role == "member"
        assert response.nickname is None

    def test_participant_response_full(self) -> None:
        """Test participant response with all fields."""
        response = ParticipantResponse(
            user_id="user-456",
            role="admin",
            nickname="JohnD",
            joined_at="2024-01-01T00:00:00Z",
        )
        assert response.nickname == "JohnD"
        assert response.role == "admin"


class TestConversationResponseSchema:
    """Tests for ConversationResponse schema."""

    def test_conversation_response_minimal(self) -> None:
        """Test conversation response with minimal fields."""
        response = ConversationResponse(
            id="conv-123",
            type="direct",
            created_at="2024-01-01T00:00:00Z",
        )
        assert response.id == "conv-123"
        assert response.type == "direct"
        assert response.name is None
        assert response.unread_count == 0

    def test_conversation_response_full(self) -> None:
        """Test conversation response with all fields."""
        participants = [
            ParticipantResponse(
                user_id="user-1",
                role="admin",
                joined_at="2024-01-01T00:00:00Z",
            )
        ]
        response = ConversationResponse(
            id="conv-456",
            type="group",
            name="Dev Team",
            participants=participants,
            last_message_preview="Hello!",
            last_message_at="2024-01-02T00:00:00Z",
            unread_count=5,
            created_at="2024-01-01T00:00:00Z",
        )
        assert response.name == "Dev Team"
        assert len(response.participants) == 1
        assert response.unread_count == 5


class TestMessageResponseSchema:
    """Tests for MessageResponse schema."""

    def test_message_response_minimal(self) -> None:
        """Test message response with minimal fields."""
        response = MessageResponse(
            id="msg-123",
            conversation_id="conv-123",
            sender_id="user-123",
            content="Hello!",
            content_type="text",
            status="sent",
            created_at="2024-01-01T00:00:00Z",
        )
        assert response.id == "msg-123"
        assert response.content == "Hello!"
        assert response.is_edited is False

    def test_message_response_full(self) -> None:
        """Test message response with all fields."""
        response = MessageResponse(
            id="msg-456",
            conversation_id="conv-123",
            sender_id="user-123",
            content="Reply to your message",
            content_type="text",
            metadata={"key": "value"},
            status="delivered",
            reply_to_id="msg-100",
            reactions={"👍": ["user-1", "user-2"]},
            is_edited=True,
            created_at="2024-01-01T00:00:00Z",
        )
        assert response.reply_to_id == "msg-100"
        assert response.is_edited is True
        assert response.metadata == {"key": "value"}


class TestCreateDirectConversationRequestSchema:
    """Tests for CreateDirectConversationRequest schema."""

    def test_create_direct_conversation(self) -> None:
        """Test create direct conversation request."""
        request = CreateDirectConversationRequest(user_id="user-123")
        assert request.user_id == "user-123"


class TestCreateGroupConversationRequestSchema:
    """Tests for CreateGroupConversationRequest schema."""

    def test_create_group_conversation(self) -> None:
        """Test create group conversation request."""
        request = CreateGroupConversationRequest(
            name="Team Chat",
            participant_ids=["user-1", "user-2", "user-3"],
        )
        assert request.name == "Team Chat"
        assert len(request.participant_ids) == 3

    def test_create_group_name_too_short_fails(self) -> None:
        """Test create group with empty name fails."""
        with pytest.raises(ValidationError):
            CreateGroupConversationRequest(
                name="",
                participant_ids=["user-1"],
            )

    def test_create_group_name_too_long_fails(self) -> None:
        """Test create group with name too long fails."""
        with pytest.raises(ValidationError):
            CreateGroupConversationRequest(
                name="x" * 101,
                participant_ids=["user-1"],
            )

    def test_create_group_no_participants_fails(self) -> None:
        """Test create group without participants fails."""
        with pytest.raises(ValidationError):
            CreateGroupConversationRequest(
                name="Group",
                participant_ids=[],
            )


class TestSendMessageRequestSchema:
    """Tests for SendMessageRequest schema."""

    def test_send_message_minimal(self) -> None:
        """Test send message with minimal fields."""
        request = SendMessageRequest(content="Hello!")
        assert request.content == "Hello!"
        assert request.content_type == "text"
        assert request.reply_to_id is None

    def test_send_message_full(self) -> None:
        """Test send message with all fields."""
        request = SendMessageRequest(
            content="Check this out",
            content_type="text/markdown",
            reply_to_id="msg-100",
            metadata={"mentions": ["user-1"]},
        )
        assert request.content_type == "text/markdown"
        assert request.reply_to_id == "msg-100"
        assert request.metadata == {"mentions": ["user-1"]}

    def test_send_message_empty_content_fails(self) -> None:
        """Test send message with empty content fails."""
        with pytest.raises(ValidationError):
            SendMessageRequest(content="")

    def test_send_message_content_too_long_fails(self) -> None:
        """Test send message with content too long fails."""
        with pytest.raises(ValidationError):
            SendMessageRequest(content="x" * 10001)


class TestChatEdgeCases:
    """Edge case tests for chat schemas."""

    def test_conversation_with_many_participants(self) -> None:
        """Test conversation with many participants."""
        participants = [
            ParticipantResponse(
                user_id=f"user-{i}",
                role="member",
                joined_at="2024-01-01T00:00:00Z",
            )
            for i in range(50)
        ]
        response = ConversationResponse(
            id="conv-1",
            type="group",
            name="Large Group",
            participants=participants,
            created_at="2024-01-01T00:00:00Z",
        )
        assert len(response.participants) == 50

    def test_message_with_reactions(self) -> None:
        """Test message with multiple reactions."""
        reactions = {
            "👍": ["user-1", "user-2"],
            "❤️": ["user-3"],
            "😂": ["user-1", "user-4", "user-5"],
        }
        response = MessageResponse(
            id="msg-1",
            conversation_id="conv-1",
            sender_id="user-1",
            content="Funny message",
            content_type="text",
            status="sent",
            reactions=reactions,
            created_at="2024-01-01T00:00:00Z",
        )
        assert len(response.reactions) == 3
        assert len(response.reactions["👍"]) == 2

    def test_message_max_content_length(self) -> None:
        """Test message with maximum content length."""
        request = SendMessageRequest(content="x" * 10000)
        assert len(request.content) == 10000

    def test_group_conversation_many_participants(self) -> None:
        """Test group with many participant IDs."""
        participant_ids = [f"user-{i}" for i in range(100)]
        request = CreateGroupConversationRequest(
            name="Large Team",
            participant_ids=participant_ids,
        )
        assert len(request.participant_ids) == 100

    def test_message_with_complex_metadata(self) -> None:
        """Test message with complex nested metadata."""
        metadata = {
            "attachments": [
                {"type": "image", "url": "https://example.com/img.png"},
                {"type": "file", "url": "https://example.com/doc.pdf"},
            ],
            "mentions": ["user-1", "user-2"],
            "formatting": {"bold": True, "links": 2},
        }
        request = SendMessageRequest(
            content="Check these files",
            metadata=metadata,
        )
        assert len(request.metadata["attachments"]) == 2

    def test_participant_admin_role(self) -> None:
        """Test participant with admin role."""
        response = ParticipantResponse(
            user_id="admin-user",
            role="admin",
            nickname="Admin",
            joined_at="2024-01-01T00:00:00Z",
        )
        assert response.role == "admin"

    def test_conversation_direct_type(self) -> None:
        """Test direct conversation type."""
        response = ConversationResponse(
            id="conv-direct",
            type="direct",
            created_at="2024-01-01T00:00:00Z",
        )
        assert response.type == "direct"

    def test_conversation_group_type(self) -> None:
        """Test group conversation type."""
        response = ConversationResponse(
            id="conv-group",
            type="group",
            name="Team",
            created_at="2024-01-01T00:00:00Z",
        )
        assert response.type == "group"
