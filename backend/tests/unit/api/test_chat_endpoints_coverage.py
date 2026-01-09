# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for chat endpoints to improve coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.api.v1.endpoints.chat import (
    ConversationResponse,
    MessageResponse,
    ParticipantResponse,
    CreateDirectConversationRequest,
    CreateGroupConversationRequest,
    SendMessageRequest,
    MarkReadRequest,
    ConversationListResponse,
    MessageListResponse,
)


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.tenant_id = uuid4()
    return user


class TestChatSchemas:
    """Tests for chat schema validation."""

    def test_participant_response(self) -> None:
        """Test ParticipantResponse schema."""
        response = ParticipantResponse(
            user_id=str(uuid4()),
            role="member",
            nickname="TestUser",
            joined_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.role == "member"
        assert response.nickname == "TestUser"

    def test_conversation_response(self) -> None:
        """Test ConversationResponse schema."""
        response = ConversationResponse(
            id=str(uuid4()),
            type="direct",
            name=None,
            participants=[],
            last_message_preview="Hello!",
            last_message_at=datetime.now(timezone.utc).isoformat(),
            unread_count=5,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.type == "direct"
        assert response.unread_count == 5

    def test_message_response(self) -> None:
        """Test MessageResponse schema."""
        response = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sender_id=str(uuid4()),
            content="Test message",
            content_type="text",
            metadata=None,
            status="sent",
            reply_to_id=None,
            reactions=None,
            is_edited=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.content == "Test message"
        assert response.status == "sent"

    def test_create_direct_conversation_request(self) -> None:
        """Test CreateDirectConversationRequest schema."""
        request = CreateDirectConversationRequest(
            user_id=str(uuid4()),
        )
        
        assert request.user_id is not None

    def test_create_group_conversation_request(self) -> None:
        """Test CreateGroupConversationRequest schema."""
        request = CreateGroupConversationRequest(
            name="Test Group",
            participant_ids=[str(uuid4()), str(uuid4())],
        )
        
        assert request.name == "Test Group"
        assert len(request.participant_ids) == 2

    def test_send_message_request(self) -> None:
        """Test SendMessageRequest schema."""
        request = SendMessageRequest(
            content="Hello world!",
            content_type="text",
            reply_to_id=None,
            metadata={"key": "value"},
        )
        
        assert request.content == "Hello world!"
        assert request.metadata == {"key": "value"}

    def test_send_message_request_with_reply(self) -> None:
        """Test SendMessageRequest with reply."""
        reply_id = str(uuid4())
        request = SendMessageRequest(
            content="Reply message",
            content_type="text",
            reply_to_id=reply_id,
        )
        
        assert request.reply_to_id == reply_id

    def test_mark_read_request(self) -> None:
        """Test MarkReadRequest schema."""
        request = MarkReadRequest(
            message_ids=[str(uuid4()), str(uuid4())],
        )
        
        assert len(request.message_ids) == 2

    def test_conversation_list_response(self) -> None:
        """Test ConversationListResponse schema."""
        response = ConversationListResponse(
            items=[
                ConversationResponse(
                    id=str(uuid4()),
                    type="group",
                    name="Team Chat",
                    participants=[],
                    unread_count=0,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            ],
            total=1,
        )
        
        assert response.total == 1
        assert len(response.items) == 1

    def test_message_list_response(self) -> None:
        """Test MessageListResponse schema."""
        response = MessageListResponse(
            items=[
                MessageResponse(
                    id=str(uuid4()),
                    conversation_id=str(uuid4()),
                    sender_id=str(uuid4()),
                    content="Message 1",
                    content_type="text",
                    status="delivered",
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            ],
            has_more=True,
        )
        
        assert response.has_more is True
        assert len(response.items) == 1


class TestConversationResponseVariations:
    """Test various ConversationResponse configurations."""

    def test_group_conversation(self) -> None:
        """Test group conversation response."""
        participants = [
            ParticipantResponse(
                user_id=str(uuid4()),
                role="admin",
                nickname="Admin",
                joined_at=datetime.now(timezone.utc).isoformat(),
            ),
            ParticipantResponse(
                user_id=str(uuid4()),
                role="member",
                nickname="Member",
                joined_at=datetime.now(timezone.utc).isoformat(),
            ),
        ]
        
        response = ConversationResponse(
            id=str(uuid4()),
            type="group",
            name="Project Team",
            participants=participants,
            last_message_preview="Latest update",
            last_message_at=datetime.now(timezone.utc).isoformat(),
            unread_count=3,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.type == "group"
        assert len(response.participants) == 2
        assert response.name == "Project Team"

    def test_direct_conversation(self) -> None:
        """Test direct conversation response."""
        response = ConversationResponse(
            id=str(uuid4()),
            type="direct",
            name=None,
            participants=[],
            last_message_preview=None,
            last_message_at=None,
            unread_count=0,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.type == "direct"
        assert response.name is None
        assert response.unread_count == 0


class TestMessageResponseVariations:
    """Test various MessageResponse configurations."""

    def test_text_message(self) -> None:
        """Test text message response."""
        response = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sender_id=str(uuid4()),
            content="Plain text message",
            content_type="text",
            status="read",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.content_type == "text"
        assert response.is_edited is False

    def test_edited_message(self) -> None:
        """Test edited message response."""
        response = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sender_id=str(uuid4()),
            content="Edited message",
            content_type="text",
            status="delivered",
            is_edited=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.is_edited is True

    def test_message_with_reactions(self) -> None:
        """Test message with reactions."""
        response = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sender_id=str(uuid4()),
            content="Popular message",
            content_type="text",
            status="read",
            reactions={"👍": 5, "❤️": 2},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.reactions is not None
        assert response.reactions["👍"] == 5

    def test_reply_message(self) -> None:
        """Test reply message response."""
        original_id = str(uuid4())
        response = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sender_id=str(uuid4()),
            content="This is a reply",
            content_type="text",
            status="sent",
            reply_to_id=original_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.reply_to_id == original_id

    def test_message_with_metadata(self) -> None:
        """Test message with metadata."""
        response = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sender_id=str(uuid4()),
            content="File shared",
            content_type="file",
            status="delivered",
            metadata={
                "filename": "document.pdf",
                "size": 1024,
                "mimetype": "application/pdf",
            },
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.content_type == "file"
        assert response.metadata["filename"] == "document.pdf"


class TestRequestValidation:
    """Test request validation edge cases."""

    def test_send_message_min_content(self) -> None:
        """Test send message with minimum content."""
        request = SendMessageRequest(
            content="a",  # Minimum 1 character
        )
        
        assert len(request.content) == 1

    def test_create_group_min_participants(self) -> None:
        """Test create group with minimum participants."""
        request = CreateGroupConversationRequest(
            name="Small Group",
            participant_ids=[str(uuid4())],  # Minimum 1 participant
        )
        
        assert len(request.participant_ids) == 1

    def test_mark_read_single_message(self) -> None:
        """Test mark read with single message."""
        request = MarkReadRequest(
            message_ids=[str(uuid4())],
        )
        
        assert len(request.message_ids) == 1

    def test_mark_read_multiple_messages(self) -> None:
        """Test mark read with multiple messages."""
        request = MarkReadRequest(
            message_ids=[str(uuid4()) for _ in range(10)],
        )
        
        assert len(request.message_ids) == 10
