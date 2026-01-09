# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Chat Service and Chat entities.

Tests for chat messages, conversations, and related functionality.
"""

from uuid import uuid4
from datetime import datetime, UTC

import pytest

from app.domain.entities.chat_message import (
    ChatMessage,
    MessageContentType,
    MessageStatus,
)
from app.domain.entities.conversation import (
    Conversation,
    ConversationParticipant,
    ConversationType,
)


class TestMessageStatus:
    """Tests for MessageStatus enum."""

    def test_status_values(self) -> None:
        """Test message status values."""
        assert MessageStatus.PENDING.value == "pending"
        assert MessageStatus.SENT.value == "sent"
        assert MessageStatus.DELIVERED.value == "delivered"
        assert MessageStatus.READ.value == "read"


class TestMessageContentType:
    """Tests for MessageContentType enum."""

    def test_content_type_values(self) -> None:
        """Test content type values."""
        assert MessageContentType.TEXT.value == "text"
        assert MessageContentType.IMAGE.value == "image"
        assert MessageContentType.FILE.value == "file"
        assert MessageContentType.AUDIO.value == "audio"
        assert MessageContentType.VIDEO.value == "video"
        assert MessageContentType.LOCATION.value == "location"
        assert MessageContentType.SYSTEM.value == "system"


class TestChatMessage:
    """Tests for ChatMessage entity."""

    def test_create_text_message(self) -> None:
        """Test creating a text message."""
        sender_id = uuid4()
        conversation_id = uuid4()
        
        message = ChatMessage(
            id=uuid4(),
            tenant_id=uuid4(),
            conversation_id=conversation_id,
            sender_id=sender_id,
            content="Hello, world!",
            content_type=MessageContentType.TEXT,
        )
        
        assert message.sender_id == sender_id
        assert message.conversation_id == conversation_id
        assert message.content == "Hello, world!"
        assert message.content_type == MessageContentType.TEXT

    def test_message_default_status_pending(self) -> None:
        """Test that message default status is pending."""
        message = ChatMessage(
            id=uuid4(),
            tenant_id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Test",
        )
        
        assert message.status == MessageStatus.PENDING

    def test_mark_message_sent(self) -> None:
        """Test marking message as sent."""
        message = ChatMessage(
            id=uuid4(),
            tenant_id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Test",
        )
        
        message.mark_sent()
        
        assert message.status == MessageStatus.SENT

    def test_mark_message_delivered(self) -> None:
        """Test marking message as delivered."""
        message = ChatMessage(
            id=uuid4(),
            tenant_id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Test",
        )
        
        message.mark_delivered()
        
        assert message.status == MessageStatus.DELIVERED
        assert message.delivered_at is not None

    def test_mark_message_read(self) -> None:
        """Test marking message as read."""
        message = ChatMessage(
            id=uuid4(),
            tenant_id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Test",
        )
        
        message.mark_read()
        
        assert message.status == MessageStatus.READ
        assert message.read_at is not None

    def test_message_with_reply(self) -> None:
        """Test message replying to another."""
        original_id = uuid4()
        
        reply = ChatMessage(
            id=uuid4(),
            tenant_id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="This is a reply",
            reply_to_id=original_id,
        )
        
        assert reply.reply_to_id == original_id

    def test_message_with_metadata(self) -> None:
        """Test message with metadata (for files/images)."""
        message = ChatMessage(
            id=uuid4(),
            tenant_id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="",
            content_type=MessageContentType.IMAGE,
            metadata={
                "url": "https://example.com/image.jpg",
                "name": "photo.jpg",
                "size": 1024000,
                "width": 1920,
                "height": 1080,
            },
        )
        
        assert message.content_type == MessageContentType.IMAGE
        assert message.metadata["url"] == "https://example.com/image.jpg"
        assert message.metadata["size"] == 1024000

    def test_message_reactions(self) -> None:
        """Test message with reactions."""
        user1 = uuid4()
        user2 = uuid4()
        
        message = ChatMessage(
            id=uuid4(),
            tenant_id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Great news!",
            reactions={"👍": [user1, user2], "❤️": [user1]},
        )
        
        assert "👍" in message.reactions
        assert len(message.reactions["👍"]) == 2
        assert user1 in message.reactions["❤️"]

    def test_message_edit_tracking(self) -> None:
        """Test message edit tracking."""
        message = ChatMessage(
            id=uuid4(),
            tenant_id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Original message",
            is_edited=False,
        )
        
        # Simulate edit
        message.content = "Edited message"
        message.is_edited = True
        message.edited_at = datetime.now(UTC)
        
        assert message.is_edited is True
        assert message.edited_at is not None


class TestConversationType:
    """Tests for ConversationType enum."""

    def test_type_values(self) -> None:
        """Test conversation type values."""
        assert ConversationType.DIRECT.value == "direct"
        assert ConversationType.GROUP.value == "group"


class TestConversationParticipant:
    """Tests for ConversationParticipant."""

    def test_create_participant(self) -> None:
        """Test creating a participant."""
        user_id = uuid4()
        
        participant = ConversationParticipant(user_id=user_id)
        
        assert participant.user_id == user_id
        assert participant.is_muted is False
        assert participant.role == "member"

    def test_participant_is_admin(self) -> None:
        """Test participant admin check."""
        admin = ConversationParticipant(user_id=uuid4(), role="admin")
        owner = ConversationParticipant(user_id=uuid4(), role="owner")
        member = ConversationParticipant(user_id=uuid4(), role="member")
        
        assert admin.is_admin() is True
        assert owner.is_admin() is True
        assert member.is_admin() is False

    def test_participant_mute(self) -> None:
        """Test muting a participant."""
        participant = ConversationParticipant(user_id=uuid4())
        
        participant.is_muted = True
        participant.muted_until = datetime(2026, 12, 31, tzinfo=UTC)
        
        assert participant.is_muted is True
        assert participant.muted_until is not None

    def test_participant_nickname(self) -> None:
        """Test participant nickname in group."""
        participant = ConversationParticipant(
            user_id=uuid4(),
            nickname="TeamLead",
        )
        
        assert participant.nickname == "TeamLead"

    def test_participant_read_tracking(self) -> None:
        """Test participant read tracking."""
        message_id = uuid4()
        
        participant = ConversationParticipant(user_id=uuid4())
        participant.last_read_message_id = message_id
        participant.last_read_at = datetime.now(UTC)
        
        assert participant.last_read_message_id == message_id
        assert participant.last_read_at is not None


class TestConversation:
    """Tests for Conversation entity."""

    def test_create_direct_conversation(self) -> None:
        """Test creating a direct conversation."""
        user1 = uuid4()
        user2 = uuid4()
        
        conversation = Conversation(
            id=uuid4(),
            tenant_id=uuid4(),
            type=ConversationType.DIRECT,
            participants=[
                ConversationParticipant(user_id=user1),
                ConversationParticipant(user_id=user2),
            ],
        )
        
        assert conversation.type == ConversationType.DIRECT
        assert len(conversation.participants) == 2
        assert conversation.name is None  # Direct chats don't have names

    def test_create_group_conversation(self) -> None:
        """Test creating a group conversation."""
        users = [uuid4() for _ in range(5)]
        
        conversation = Conversation(
            id=uuid4(),
            tenant_id=uuid4(),
            type=ConversationType.GROUP,
            name="Project Team",
            description="Discussion for the project",
            participants=[ConversationParticipant(user_id=uid) for uid in users],
        )
        
        assert conversation.type == ConversationType.GROUP
        assert conversation.name == "Project Team"
        assert conversation.description == "Discussion for the project"
        assert len(conversation.participants) == 5

    def test_conversation_with_avatar(self) -> None:
        """Test group conversation with avatar."""
        conversation = Conversation(
            id=uuid4(),
            tenant_id=uuid4(),
            type=ConversationType.GROUP,
            name="Team Chat",
            avatar_url="https://example.com/avatar.jpg",
        )
        
        assert conversation.avatar_url == "https://example.com/avatar.jpg"

    def test_conversation_last_message_info(self) -> None:
        """Test conversation with last message info."""
        last_msg_id = uuid4()
        last_msg_time = datetime.now(UTC)
        
        conversation = Conversation(
            id=uuid4(),
            tenant_id=uuid4(),
            type=ConversationType.DIRECT,
            last_message_id=last_msg_id,
            last_message_at=last_msg_time,
            last_message_preview="Hey, how are you?",
        )
        
        assert conversation.last_message_id == last_msg_id
        assert conversation.last_message_at == last_msg_time
        assert conversation.last_message_preview == "Hey, how are you?"

    def test_conversation_message_count(self) -> None:
        """Test conversation message count."""
        conversation = Conversation(
            id=uuid4(),
            tenant_id=uuid4(),
            type=ConversationType.DIRECT,
            message_count=42,
        )
        
        assert conversation.message_count == 42

    def test_conversation_default_values(self) -> None:
        """Test conversation default values."""
        conversation = Conversation(
            id=uuid4(),
            tenant_id=uuid4(),
        )
        
        assert conversation.type == ConversationType.DIRECT
        assert conversation.participants == []
        assert conversation.message_count == 0
        assert conversation.last_message_id is None


# =========================================
# ChatService Unit Tests
# =========================================

from unittest.mock import AsyncMock, MagicMock, patch


class TestChatServiceInit:
    """Tests for ChatService initialization."""

    def test_init_with_session_only(self) -> None:
        """Test ChatService can be initialized with session only."""
        from app.application.services.chat_service import ChatService
        
        mock_session = AsyncMock()
        service = ChatService(session=mock_session)
        
        assert service._session == mock_session
        assert service._ws_manager is None

    def test_init_with_ws_manager(self) -> None:
        """Test ChatService can be initialized with WebSocket manager."""
        from app.application.services.chat_service import ChatService
        
        mock_session = AsyncMock()
        mock_ws = MagicMock()
        service = ChatService(session=mock_session, ws_manager=mock_ws)
        
        assert service._session == mock_session
        assert service._ws_manager == mock_ws


class TestChatServiceConversations:
    """Tests for ChatService conversation methods."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def chat_service(self, mock_session: AsyncMock):
        """Create ChatService with mock session."""
        from app.application.services.chat_service import ChatService
        return ChatService(session=mock_session)

    @pytest.mark.asyncio
    async def test_create_group_conversation_adds_to_session(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test creating group conversation adds to session."""
        result = await chat_service.create_group_conversation(
            name="Test Group",
            creator_id=uuid4(),
            participant_ids=[uuid4(), uuid4()],
            tenant_id=uuid4(),
            description="Test description",
        )
        
        assert result.name == "Test Group"
        assert result.type == ConversationType.GROUP
        assert result.description == "Test description"
        # Verify session.add was called (conversation + participants)
        assert mock_session.add.call_count >= 1
        mock_session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_get_or_create_direct_creates_new(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test get_or_create_direct creates new when not exists."""
        # Mock execute to return no existing conversation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        user1 = uuid4()
        user2 = uuid4()
        tenant = uuid4()
        
        result = await chat_service.get_or_create_direct_conversation(
            user_id=user1,
            other_user_id=user2,
            tenant_id=tenant,
        )
        
        assert result.type == ConversationType.DIRECT
        assert result.tenant_id == tenant
        assert len(result.participants) == 2
        mock_session.flush.assert_awaited()


class TestChatServiceMessageHelpers:
    """Tests for ChatService message helper methods."""

    def test_message_entity_creation(self) -> None:
        """Test creating a ChatMessage entity."""
        message = ChatMessage(
            id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Hello, World!",
            content_type=MessageContentType.TEXT,
            status=MessageStatus.PENDING,
        )
        
        assert message.content == "Hello, World!"
        assert message.content_type == MessageContentType.TEXT
        assert message.status == MessageStatus.PENDING

    def test_conversation_participant_roles(self) -> None:
        """Test participant role checking."""
        owner = ConversationParticipant(
            user_id=uuid4(),
            role="owner",
        )
        admin = ConversationParticipant(
            user_id=uuid4(),
            role="admin",
        )
        member = ConversationParticipant(
            user_id=uuid4(),
            role="member",
        )
        
        assert owner.is_admin()  # owner should be admin
        assert admin.is_admin()
        assert not member.is_admin()


class TestChatServiceSendMessage:
    """Tests for ChatService.send_message method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_ws_manager(self) -> MagicMock:
        """Create a mock WebSocket manager."""
        manager = MagicMock()
        manager.send_to_room = AsyncMock()
        return manager

    @pytest.fixture
    def chat_service(self, mock_session: AsyncMock):
        """Create ChatService with mock session."""
        from app.application.services.chat_service import ChatService
        return ChatService(session=mock_session)

    @pytest.fixture
    def chat_service_with_ws(self, mock_session: AsyncMock, mock_ws_manager: MagicMock):
        """Create ChatService with WebSocket manager."""
        from app.application.services.chat_service import ChatService
        return ChatService(session=mock_session, ws_manager=mock_ws_manager)

    @pytest.mark.asyncio
    async def test_send_message_raises_when_no_conversation(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test send_message raises ValueError when conversation not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Conversation not found"):
            await chat_service.send_message(
                conversation_id=uuid4(),
                sender_id=uuid4(),
                content="Hello",
            )

    @pytest.mark.asyncio
    async def test_send_message_success(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test send_message creates message successfully."""
        conversation_id = uuid4()
        tenant_id = uuid4()
        sender_id = uuid4()

        # Mock conversation lookup
        mock_conv = MagicMock()
        mock_conv.tenant_id = tenant_id
        mock_conv.last_message_id = None
        mock_conv.last_message_at = None
        mock_conv.last_message_preview = None
        mock_conv.message_count = 0
        mock_conv.updated_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_session.execute.return_value = mock_result

        result = await chat_service.send_message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content="Hello, World!",
        )

        assert result.content == "Hello, World!"
        assert result.sender_id == sender_id
        assert result.conversation_id == conversation_id
        mock_session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_send_message_with_reply(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test send_message with reply_to_id."""
        reply_to = uuid4()
        mock_conv = MagicMock()
        mock_conv.tenant_id = uuid4()
        mock_conv.message_count = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_session.execute.return_value = mock_result

        result = await chat_service.send_message(
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Reply",
            reply_to_id=reply_to,
        )

        assert result.reply_to_id == reply_to

    @pytest.mark.asyncio
    async def test_send_message_with_metadata(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test send_message with metadata."""
        mock_conv = MagicMock()
        mock_conv.tenant_id = uuid4()
        mock_conv.message_count = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_session.execute.return_value = mock_result

        metadata = {"url": "https://example.com/file.pdf"}

        result = await chat_service.send_message(
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="file.pdf",
            content_type=MessageContentType.FILE,
            metadata=metadata,
        )

        assert result.metadata == metadata
        assert result.content_type == MessageContentType.FILE

    @pytest.mark.asyncio
    async def test_send_message_with_websocket(
        self, chat_service_with_ws, mock_session: AsyncMock, mock_ws_manager: MagicMock
    ) -> None:
        """Test send_message triggers WebSocket delivery."""
        mock_conv = MagicMock()
        mock_conv.tenant_id = uuid4()
        mock_conv.message_count = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_session.execute.return_value = mock_result

        await chat_service_with_ws.send_message(
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Hello via WebSocket",
        )

        mock_ws_manager.send_to_room.assert_awaited_once()


class TestChatServiceGetMessages:
    """Tests for ChatService.get_messages method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        return AsyncMock()

    @pytest.fixture
    def chat_service(self, mock_session: AsyncMock):
        """Create ChatService."""
        from app.application.services.chat_service import ChatService
        return ChatService(session=mock_session)

    @pytest.mark.asyncio
    async def test_get_messages_access_denied(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test get_messages raises when user not participant."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Access denied"):
            await chat_service.get_messages(
                conversation_id=uuid4(),
                user_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_get_messages_returns_messages(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test get_messages returns message list."""
        # First call: participant check
        participant = MagicMock()
        mock_result_participant = MagicMock()
        mock_result_participant.scalar_one_or_none.return_value = participant

        # Second call: messages
        mock_message = MagicMock()
        mock_message.id = uuid4()
        mock_message.tenant_id = uuid4()
        mock_message.conversation_id = uuid4()
        mock_message.sender_id = uuid4()
        mock_message.content = "Test message"
        mock_message.content_type = "text"
        mock_message.metadata = {}
        mock_message.status = "sent"
        mock_message.delivered_at = None
        mock_message.read_at = None
        mock_message.reply_to_id = None
        mock_message.reactions = {}
        mock_message.is_edited = False
        mock_message.edited_at = None
        mock_message.created_at = datetime.now(UTC)
        mock_message.updated_at = datetime.now(UTC)

        mock_result_messages = MagicMock()
        mock_result_messages.scalars.return_value.all.return_value = [mock_message]

        mock_session.execute.side_effect = [
            mock_result_participant,
            mock_result_messages,
        ]

        result = await chat_service.get_messages(
            conversation_id=uuid4(),
            user_id=uuid4(),
        )

        assert len(result) == 1
        assert result[0].content == "Test message"


class TestChatServiceMarkMessagesRead:
    """Tests for ChatService.mark_messages_read method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        return AsyncMock()

    @pytest.fixture
    def chat_service(self, mock_session: AsyncMock):
        """Create ChatService."""
        from app.application.services.chat_service import ChatService
        return ChatService(session=mock_session)

    @pytest.mark.asyncio
    async def test_mark_messages_read_without_ids_returns_zero(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test mark_messages_read without message_ids returns 0."""
        result = await chat_service.mark_messages_read(
            conversation_id=uuid4(),
            user_id=uuid4(),
        )

        assert result == 0
        mock_session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_mark_messages_read_with_ids(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test mark_messages_read with specific message_ids."""
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 3
        mock_session.execute.return_value = mock_update_result

        result = await chat_service.mark_messages_read(
            conversation_id=uuid4(),
            user_id=uuid4(),
            message_ids=[uuid4(), uuid4(), uuid4()],
        )

        assert result == 3


class TestChatServiceDeliverMessage:
    """Tests for ChatService._deliver_message method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        return AsyncMock()

    @pytest.fixture
    def mock_ws_manager(self) -> MagicMock:
        """Create a mock WebSocket manager."""
        manager = MagicMock()
        manager.send_to_room = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_deliver_message_without_ws_manager(
        self, mock_session: AsyncMock
    ) -> None:
        """Test _deliver_message does nothing without ws_manager."""
        from app.application.services.chat_service import ChatService

        service = ChatService(session=mock_session, ws_manager=None)

        message = ChatMessage(
            id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Test",
        )
        conv = MagicMock()

        # Should not raise
        await service._deliver_message(message, conv)

    @pytest.mark.asyncio
    async def test_deliver_message_sends_to_room(
        self, mock_session: AsyncMock, mock_ws_manager: MagicMock
    ) -> None:
        """Test _deliver_message sends WebSocket message to room."""
        from app.application.services.chat_service import ChatService

        service = ChatService(session=mock_session, ws_manager=mock_ws_manager)

        message = ChatMessage(
            id=uuid4(),
            conversation_id=uuid4(),
            sender_id=uuid4(),
            content="Hello!",
            created_at=datetime.now(UTC),
        )
        conv = MagicMock()

        await service._deliver_message(message, conv)

        mock_ws_manager.send_to_room.assert_awaited_once()
        call_args = mock_ws_manager.send_to_room.call_args
        assert call_args[0][0] == str(message.conversation_id)


class TestChatServiceConversationToEntity:
    """Tests for ChatService._conversation_to_entity method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        return AsyncMock()

    @pytest.fixture
    def chat_service(self, mock_session: AsyncMock):
        """Create ChatService."""
        from app.application.services.chat_service import ChatService
        return ChatService(session=mock_session)

    def test_conversation_to_entity_basic(self, chat_service) -> None:
        """Test _conversation_to_entity converts basic fields."""
        model = MagicMock()
        model.id = uuid4()
        model.tenant_id = uuid4()
        model.type = "direct"
        model.participants = []
        model.name = None
        model.description = None
        model.avatar_url = None
        model.last_message_id = None
        model.last_message_at = None
        model.last_message_preview = None
        model.message_count = 0
        model.is_archived = False
        model.send_permission = "all"
        model.created_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)

        result = chat_service._conversation_to_entity(model)

        assert result.id == model.id
        assert result.type == ConversationType.DIRECT
        assert result.participants == []

    def test_conversation_to_entity_with_participants(self, chat_service) -> None:
        """Test _conversation_to_entity converts participants."""
        model = MagicMock()
        model.id = uuid4()
        model.tenant_id = uuid4()
        model.type = "group"
        model.name = "Test Group"
        model.description = "A test group"
        model.avatar_url = "https://example.com/avatar.png"
        model.last_message_id = uuid4()
        model.last_message_at = datetime.now(UTC)
        model.last_message_preview = "Last message"
        model.message_count = 10
        model.is_archived = False
        model.send_permission = "all"
        model.created_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)

        # Mock participant
        participant = MagicMock()
        participant.user_id = uuid4()
        participant.joined_at = datetime.now(UTC)
        participant.is_muted = False
        participant.muted_until = None
        participant.last_read_message_id = None
        participant.last_read_at = None
        participant.role = "member"
        participant.nickname = "Nickname"
        model.participants = [participant]

        result = chat_service._conversation_to_entity(model)

        assert result.name == "Test Group"
        assert result.type == ConversationType.GROUP
        assert len(result.participants) == 1
        assert result.participants[0].nickname == "Nickname"


class TestChatServiceMessageToEntity:
    """Tests for ChatService._message_to_entity method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        return AsyncMock()

    @pytest.fixture
    def chat_service(self, mock_session: AsyncMock):
        """Create ChatService."""
        from app.application.services.chat_service import ChatService
        return ChatService(session=mock_session)

    def test_message_to_entity(self, chat_service) -> None:
        """Test _message_to_entity converts all fields."""
        model = MagicMock()
        model.id = uuid4()
        model.tenant_id = uuid4()
        model.conversation_id = uuid4()
        model.sender_id = uuid4()
        model.content = "Hello!"
        model.content_type = "text"
        model.metadata = {"key": "value"}
        model.status = "sent"
        model.delivered_at = datetime.now(UTC)
        model.read_at = None
        model.reply_to_id = None
        model.reactions = {"👍": []}
        model.is_edited = False
        model.edited_at = None
        model.created_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)

        result = chat_service._message_to_entity(model)

        assert result.content == "Hello!"
        assert result.content_type == MessageContentType.TEXT
        assert result.status == MessageStatus.SENT
        assert result.metadata == {"key": "value"}

    def test_message_to_entity_with_reply(self, chat_service) -> None:
        """Test _message_to_entity with reply_to_id."""
        reply_to = uuid4()
        model = MagicMock()
        model.id = uuid4()
        model.tenant_id = uuid4()
        model.conversation_id = uuid4()
        model.sender_id = uuid4()
        model.content = "Reply"
        model.content_type = "text"
        model.metadata = {}
        model.status = "sent"
        model.delivered_at = None
        model.read_at = None
        model.reply_to_id = reply_to
        model.reactions = {}
        model.is_edited = True
        model.edited_at = datetime.now(UTC)
        model.created_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)

        result = chat_service._message_to_entity(model)

        assert result.reply_to_id == reply_to
        assert result.is_edited is True


class TestChatServiceGetConversation:
    """Tests for ChatService.get_conversation method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        return AsyncMock()

    @pytest.fixture
    def chat_service(self, mock_session: AsyncMock):
        """Create ChatService."""
        from app.application.services.chat_service import ChatService
        return ChatService(session=mock_session)

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test get_conversation returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await chat_service.get_conversation(
            conversation_id=uuid4(),
            user_id=uuid4(),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_conversation_found(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test get_conversation returns conversation when found."""
        conv_id = uuid4()
        model = MagicMock()
        model.id = conv_id
        model.tenant_id = uuid4()
        model.type = "direct"
        model.participants = []
        model.name = None
        model.description = None
        model.avatar_url = None
        model.last_message_id = None
        model.last_message_at = None
        model.last_message_preview = None
        model.message_count = 0
        model.is_archived = False
        model.send_permission = "all"
        model.created_at = datetime.now(UTC)
        model.updated_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        result = await chat_service.get_conversation(
            conversation_id=conv_id,
            user_id=uuid4(),
        )

        assert result is not None
        assert result.id == conv_id


class TestChatServiceGetUserConversations:
    """Tests for ChatService.get_user_conversations method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        return AsyncMock()

    @pytest.fixture
    def chat_service(self, mock_session: AsyncMock):
        """Create ChatService."""
        from app.application.services.chat_service import ChatService
        return ChatService(session=mock_session)

    @pytest.mark.asyncio
    async def test_get_user_conversations_empty(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test get_user_conversations returns empty list."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await chat_service.get_user_conversations(
            user_id=uuid4(),
            tenant_id=uuid4(),
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_conversations_with_results(
        self, chat_service, mock_session: AsyncMock
    ) -> None:
        """Test get_user_conversations returns conversations."""
        model1 = MagicMock()
        model1.id = uuid4()
        model1.tenant_id = uuid4()
        model1.type = "direct"
        model1.participants = []
        model1.name = None
        model1.description = None
        model1.avatar_url = None
        model1.last_message_id = None
        model1.last_message_at = datetime.now(UTC)
        model1.last_message_preview = "Hello"
        model1.message_count = 5
        model1.is_archived = False
        model1.send_permission = "all"
        model1.created_at = datetime.now(UTC)
        model1.updated_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [model1]
        mock_session.execute.return_value = mock_result

        result = await chat_service.get_user_conversations(
            user_id=uuid4(),
            tenant_id=uuid4(),
            limit=10,
            offset=0,
        )

        assert len(result) == 1
        assert result[0].message_count == 5
