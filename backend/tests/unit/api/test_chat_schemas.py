# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for chat endpoint schemas."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from app.api.v1.endpoints.chat import (
    ParticipantResponse,
    ConversationResponse,
    MessageResponse,
    CreateDirectConversationRequest,
    CreateGroupConversationRequest,
    SendMessageRequest,
)


class TestParticipantResponse:
    """Tests for ParticipantResponse schema."""

    def test_participant_response_valid(self):
        """Test valid participant response."""
        participant = ParticipantResponse(
            user_id=str(uuid4()),
            role="member",
            nickname="John",
            joined_at=datetime.now(timezone.utc).isoformat()
        )
        assert participant.role == "member"
        assert participant.nickname == "John"

    def test_participant_response_no_nickname(self):
        """Test participant without nickname."""
        participant = ParticipantResponse(
            user_id=str(uuid4()),
            role="admin",
            joined_at=datetime.now(timezone.utc).isoformat()
        )
        assert participant.nickname is None

    def test_participant_response_different_roles(self):
        """Test different participant roles."""
        for role in ["admin", "member", "moderator"]:
            participant = ParticipantResponse(
                user_id=str(uuid4()),
                role=role,
                joined_at="2025-01-01T00:00:00Z"
            )
            assert participant.role == role


class TestConversationResponse:
    """Tests for ConversationResponse schema."""

    def test_conversation_response_minimal(self):
        """Test conversation response with minimal fields."""
        conversation = ConversationResponse(
            id=str(uuid4()),
            type="direct",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        assert conversation.type == "direct"
        assert conversation.participants == []
        assert conversation.unread_count == 0

    def test_conversation_response_full(self):
        """Test conversation response with all fields."""
        now = datetime.now(timezone.utc).isoformat()
        participant = ParticipantResponse(
            user_id=str(uuid4()),
            role="member",
            joined_at=now
        )
        conversation = ConversationResponse(
            id=str(uuid4()),
            type="group",
            name="Team Chat",
            participants=[participant],
            last_message_preview="Hello everyone!",
            last_message_at=now,
            unread_count=5,
            created_at=now
        )
        assert conversation.name == "Team Chat"
        assert len(conversation.participants) == 1
        assert conversation.unread_count == 5

    def test_conversation_types(self):
        """Test different conversation types."""
        for conv_type in ["direct", "group", "channel"]:
            conv = ConversationResponse(
                id=str(uuid4()),
                type=conv_type,
                created_at="2025-01-01T00:00:00Z"
            )
            assert conv.type == conv_type


class TestMessageResponse:
    """Tests for MessageResponse schema."""

    def test_message_response_minimal(self):
        """Test message response with minimal fields."""
        message = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sender_id=str(uuid4()),
            content="Hello!",
            content_type="text",
            status="sent",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        assert message.content == "Hello!"
        assert message.is_edited is False

    def test_message_response_full(self):
        """Test message response with all fields."""
        message = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sender_id=str(uuid4()),
            content="Check this file",
            content_type="file",
            metadata={"filename": "doc.pdf", "size": 1024},
            status="delivered",
            reply_to_id=str(uuid4()),
            reactions={"👍": 2, "❤️": 1},
            is_edited=True,
            created_at="2025-01-01T00:00:00Z"
        )
        assert message.content_type == "file"
        assert message.is_edited is True
        assert message.reactions == {"👍": 2, "❤️": 1}

    def test_message_statuses(self):
        """Test different message statuses."""
        for status in ["sent", "delivered", "read", "failed"]:
            message = MessageResponse(
                id=str(uuid4()),
                conversation_id=str(uuid4()),
                sender_id=str(uuid4()),
                content="Test",
                content_type="text",
                status=status,
                created_at="2025-01-01T00:00:00Z"
            )
            assert message.status == status


class TestCreateDirectConversationRequest:
    """Tests for CreateDirectConversationRequest schema."""

    def test_create_direct_valid(self):
        """Test valid direct conversation request."""
        request = CreateDirectConversationRequest(user_id=str(uuid4()))
        assert request.user_id is not None

    def test_create_direct_requires_user_id(self):
        """Test user_id is required."""
        with pytest.raises(ValidationError):
            CreateDirectConversationRequest()  # type: ignore[call-arg]


class TestCreateGroupConversationRequest:
    """Tests for CreateGroupConversationRequest schema."""

    def test_create_group_valid(self):
        """Test valid group conversation request."""
        request = CreateGroupConversationRequest(
            name="Project Team",
            participant_ids=[str(uuid4()), str(uuid4())]
        )
        assert request.name == "Project Team"
        assert len(request.participant_ids) == 2

    def test_create_group_requires_name(self):
        """Test name is required."""
        with pytest.raises(ValidationError):
            CreateGroupConversationRequest(participant_ids=[str(uuid4())])  # type: ignore[call-arg]

    def test_create_group_name_min_length(self):
        """Test name minimum length."""
        with pytest.raises(ValidationError):
            CreateGroupConversationRequest(name="", participant_ids=[str(uuid4())])

    def test_create_group_name_max_length(self):
        """Test name maximum length."""
        with pytest.raises(ValidationError):
            CreateGroupConversationRequest(
                name="x" * 101,
                participant_ids=[str(uuid4())]
            )

    def test_create_group_requires_participants(self):
        """Test participants are required."""
        with pytest.raises(ValidationError):
            CreateGroupConversationRequest(name="Team", participant_ids=[])


class TestSendMessageRequest:
    """Tests for SendMessageRequest schema."""

    def test_send_message_minimal(self):
        """Test minimal send message request."""
        request = SendMessageRequest(content="Hello!")
        assert request.content == "Hello!"
        assert request.content_type == "text"
        assert request.reply_to_id is None
        assert request.metadata is None

    def test_send_message_full(self):
        """Test send message with all fields."""
        request = SendMessageRequest(
            content="Check this attachment",
            content_type="file",
            reply_to_id=str(uuid4()),
            metadata={"filename": "report.pdf"}
        )
        assert request.content_type == "file"
        assert request.metadata == {"filename": "report.pdf"}

    def test_send_message_content_required(self):
        """Test content is required."""
        with pytest.raises(ValidationError):
            SendMessageRequest(content_type="text")  # type: ignore[call-arg]

    def test_send_message_content_min_length(self):
        """Test content minimum length."""
        with pytest.raises(ValidationError):
            SendMessageRequest(content="")

    def test_send_message_content_max_length(self):
        """Test content maximum length."""
        with pytest.raises(ValidationError):
            SendMessageRequest(content="x" * 10001)

    def test_send_message_content_types(self):
        """Test different content types."""
        for content_type in ["text", "image", "file", "audio", "video"]:
            request = SendMessageRequest(
                content="Test content",
                content_type=content_type
            )
            assert request.content_type == content_type
