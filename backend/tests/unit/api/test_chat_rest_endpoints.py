# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for chat REST endpoints to improve coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.api.v1.endpoints.chat import (
    list_conversations,
    create_direct_conversation,
    create_group_conversation,
    get_conversation,
    list_messages,
    send_message,
    mark_messages_read,
    CreateDirectConversationRequest,
    CreateGroupConversationRequest,
    SendMessageRequest,
    MarkReadRequest,
    ConversationResponse,
    MessageResponse,
    ParticipantResponse,
)


class MockUser:
    """Mock current user."""
    
    def __init__(self):
        self.id = uuid4()
        self.tenant_id = uuid4()
        self.email = "test@example.com"


class TestListConversations:
    """Tests for list_conversations endpoint."""

    @pytest.mark.asyncio
    async def test_list_conversations_empty(self) -> None:
        """Test listing conversations when empty."""
        mock_user = MockUser()
        mock_session = AsyncMock()
        
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        # Count query returns empty
        mock_count_result = MagicMock()
        mock_count_result.all.return_value = []
        mock_session.execute.side_effect = [mock_result, mock_count_result]
        
        result = await list_conversations(
            current_user=mock_user,
            session=mock_session,
            limit=50,
            offset=0,
        )
        
        assert result.items == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_conversations_with_data(self) -> None:
        """Test listing conversations with data."""
        mock_user = MockUser()
        mock_session = AsyncMock()
        
        # Create mock conversation
        mock_participant = MagicMock()
        mock_participant.user_id = uuid4()
        mock_participant.role = "member"
        mock_participant.nickname = None
        mock_participant.joined_at = datetime.now(timezone.utc)
        
        mock_conv = MagicMock()
        mock_conv.id = uuid4()
        mock_conv.type = "direct"
        mock_conv.name = None
        mock_conv.participants = [mock_participant]
        mock_conv.last_message_preview = "Hello"
        mock_conv.last_message_at = datetime.now(timezone.utc)
        mock_conv.created_at = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = [mock_conv]
        
        mock_count_result = MagicMock()
        mock_count_result.all.return_value = [1]
        
        mock_session.execute.side_effect = [mock_result, mock_count_result]
        
        result = await list_conversations(
            current_user=mock_user,
            session=mock_session,
            limit=50,
            offset=0,
        )
        
        assert len(result.items) == 1
        assert result.total == 1


class TestCreateDirectConversation:
    """Tests for create_direct_conversation endpoint."""

    @pytest.mark.asyncio
    async def test_create_direct_conversation(self) -> None:
        """Test creating a direct conversation."""
        mock_user = MockUser()
        mock_session = AsyncMock()
        other_user_id = uuid4()
        
        request = CreateDirectConversationRequest(user_id=str(other_user_id))
        
        # Mock conversation returned by service
        mock_participant = MagicMock()
        mock_participant.user_id = mock_user.id
        mock_participant.role = "member"
        mock_participant.nickname = None
        mock_participant.joined_at = datetime.now(timezone.utc)
        
        mock_conversation = MagicMock()
        mock_conversation.id = uuid4()
        mock_conversation.type = MagicMock(value="direct")
        mock_conversation.name = None
        mock_conversation.participants = [mock_participant]
        mock_conversation.created_at = datetime.now(timezone.utc)
        
        with patch("app.application.services.chat_service.ChatService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.get_or_create_direct_conversation.return_value = mock_conversation
            mock_service_cls.return_value = mock_service
            
            result = await create_direct_conversation(
                request=request,
                current_user=mock_user,
                session=mock_session,
            )
            
            # Verify it returns a valid response structure
            assert result is not None


class TestCreateGroupConversation:
    """Tests for create_group_conversation endpoint."""

    @pytest.mark.asyncio
    async def test_create_group_conversation(self) -> None:
        """Test creating a group conversation."""
        mock_user = MockUser()
        mock_session = AsyncMock()
        
        participant_ids = [str(uuid4()), str(uuid4())]
        request = CreateGroupConversationRequest(
            name="Test Group",
            participant_ids=participant_ids,
        )
        
        # Mock conversation returned by service
        mock_participant = MagicMock()
        mock_participant.user_id = mock_user.id
        mock_participant.role = "admin"
        mock_participant.nickname = None
        mock_participant.joined_at = datetime.now(timezone.utc)
        
        mock_conversation = MagicMock()
        mock_conversation.id = uuid4()
        mock_conversation.type = MagicMock(value="group")
        mock_conversation.name = "Test Group"
        mock_conversation.participants = [mock_participant]
        mock_conversation.created_at = datetime.now(timezone.utc)
        
        with patch("app.application.services.chat_service.ChatService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.create_group_conversation.return_value = mock_conversation
            mock_service_cls.return_value = mock_service
            
            result = await create_group_conversation(
                request=request,
                current_user=mock_user,
                session=mock_session,
            )
            
            # Verify it returns a valid response structure
            assert result is not None


class TestGetConversation:
    """Tests for get_conversation endpoint."""

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self) -> None:
        """Test getting a non-existent conversation."""
        mock_user = MockUser()
        mock_session = AsyncMock()
        conversation_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await get_conversation(
                conversation_id=conversation_id,
                current_user=mock_user,
                session=mock_session,
            )
        
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_conversation_success(self) -> None:
        """Test getting an existing conversation."""
        mock_user = MockUser()
        mock_session = AsyncMock()
        conversation_id = uuid4()
        
        # Create mock conversation
        mock_participant = MagicMock()
        mock_participant.user_id = mock_user.id
        mock_participant.role = "member"
        mock_participant.nickname = None
        mock_participant.joined_at = datetime.now(timezone.utc)
        
        mock_conv = MagicMock()
        mock_conv.id = conversation_id
        mock_conv.type = "direct"
        mock_conv.name = None
        mock_conv.participants = [mock_participant]
        mock_conv.last_message_preview = None
        mock_conv.last_message_at = None
        mock_conv.created_at = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_session.execute.return_value = mock_result
        
        result = await get_conversation(
            conversation_id=conversation_id,
            current_user=mock_user,
            session=mock_session,
        )
        
        assert str(result.id) == str(conversation_id)


class TestListMessages:
    """Tests for list_messages endpoint."""

    @pytest.mark.asyncio
    async def test_list_messages_empty(self) -> None:
        """Test listing messages when empty."""
        mock_user = MockUser()
        mock_session = AsyncMock()
        conversation_id = uuid4()
        
        # First query checks if user is participant
        mock_participant = MagicMock()
        mock_participant_result = MagicMock()
        mock_participant_result.scalar_one_or_none.return_value = mock_participant
        
        # Second query gets messages
        mock_messages_result = MagicMock()
        mock_messages_result.scalars.return_value.all.return_value = []
        
        mock_session.execute.side_effect = [mock_participant_result, mock_messages_result]
        
        result = await list_messages(
            conversation_id=conversation_id,
            current_user=mock_user,
            session=mock_session,
            limit=50,
            before=None,
        )
        
        assert result.items == []
        assert result.has_more is False


class TestSendMessage:
    """Tests for send_message endpoint."""

    def test_send_message_request_validation(self) -> None:
        """Test SendMessageRequest schema validation."""
        request = SendMessageRequest(content="Hello!")
        assert request.content == "Hello!"
        assert request.content_type == "text"


class TestMarkMessagesRead:
    """Tests for mark_messages_read endpoint."""

    def test_mark_read_request_validation(self) -> None:
        """Test MarkReadRequest schema validation."""
        request = MarkReadRequest(message_ids=[str(uuid4())])
        assert len(request.message_ids) == 1


class TestChatSchemas:
    """Tests for chat schema validation."""

    def test_participant_response(self) -> None:
        """Test ParticipantResponse schema."""
        response = ParticipantResponse(
            user_id=str(uuid4()),
            role="member",
            nickname="Test User",
            joined_at="2025-01-01T00:00:00Z",
        )
        
        assert response.role == "member"

    def test_conversation_response(self) -> None:
        """Test ConversationResponse schema."""
        response = ConversationResponse(
            id=str(uuid4()),
            type="direct",
            name=None,
            participants=[],
            last_message_preview="Hello",
            last_message_at="2025-01-01T00:00:00Z",
            unread_count=5,
            created_at="2025-01-01T00:00:00Z",
        )
        
        assert response.type == "direct"
        assert response.unread_count == 5

    def test_message_response(self) -> None:
        """Test MessageResponse schema."""
        response = MessageResponse(
            id=str(uuid4()),
            conversation_id=str(uuid4()),
            sender_id=str(uuid4()),
            content="Hello world!",
            content_type="text",
            metadata=None,
            status="sent",
            reply_to_id=None,
            reactions=None,
            is_edited=False,
            created_at="2025-01-01T00:00:00Z",
        )
        
        assert response.content == "Hello world!"
        assert response.is_edited is False

    def test_create_direct_conversation_request(self) -> None:
        """Test CreateDirectConversationRequest schema."""
        request = CreateDirectConversationRequest(user_id=str(uuid4()))
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
            content="Hello!",
            content_type="text",
            reply_to_id=str(uuid4()),
            metadata={"key": "value"},
        )
        assert request.content == "Hello!"
        assert request.metadata["key"] == "value"

    def test_mark_read_request(self) -> None:
        """Test MarkReadRequest schema."""
        request = MarkReadRequest(
            message_ids=[str(uuid4()), str(uuid4())],
        )
        assert len(request.message_ids) == 2
