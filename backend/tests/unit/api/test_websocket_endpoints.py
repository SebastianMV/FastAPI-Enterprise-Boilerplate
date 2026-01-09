# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for WebSocket endpoint utilities and handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestAuthenticateWebsocket:
    """Tests for authenticate_websocket function."""

    @pytest.mark.asyncio
    async def test_authenticate_with_valid_token(self) -> None:
        """Test authentication with valid JWT token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket

        user_id = uuid4()
        tenant_id = uuid4()
        mock_websocket = MagicMock()

        with patch(
            "app.api.v1.endpoints.websocket.validate_access_token"
        ) as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
            }

            result = await authenticate_websocket(mock_websocket, "valid-token")

            assert result is not None
            assert result[0] == user_id
            assert result[1] == tenant_id

    @pytest.mark.asyncio
    async def test_authenticate_with_no_token(self) -> None:
        """Test authentication with no token returns None."""
        from app.api.v1.endpoints.websocket import authenticate_websocket

        mock_websocket = MagicMock()
        result = await authenticate_websocket(mock_websocket, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_token(self) -> None:
        """Test authentication with invalid token returns None."""
        from app.api.v1.endpoints.websocket import authenticate_websocket

        mock_websocket = MagicMock()

        with patch(
            "app.api.v1.endpoints.websocket.validate_access_token"
        ) as mock_validate:
            mock_validate.side_effect = Exception("Invalid token")

            result = await authenticate_websocket(mock_websocket, "invalid-token")
            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_with_no_tenant_id(self) -> None:
        """Test authentication with token that has no tenant_id."""
        from app.api.v1.endpoints.websocket import authenticate_websocket

        user_id = uuid4()
        mock_websocket = MagicMock()

        with patch(
            "app.api.v1.endpoints.websocket.validate_access_token"
        ) as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                # No tenant_id
            }

            result = await authenticate_websocket(mock_websocket, "valid-token")

            assert result is not None
            assert result[0] == user_id
            assert result[1] is None


class TestGetWsManager:
    """Tests for get_ws_manager function."""

    def test_get_ws_manager_creates_memory_manager(self) -> None:
        """Test that get_ws_manager creates memory manager when redis disabled."""
        from app.api.v1.endpoints import websocket as ws_module

        # Reset global manager
        ws_module._ws_manager = None

        with patch.object(ws_module.settings, "WEBSOCKET_BACKEND", "memory"):
            manager = ws_module.get_ws_manager()

            assert manager is not None
            from app.infrastructure.websocket import MemoryWebSocketManager

            assert isinstance(manager, MemoryWebSocketManager)

        # Reset again
        ws_module._ws_manager = None


class TestRegisterDefaultHandlers:
    """Tests for _register_default_handlers function."""

    def test_register_default_handlers(self) -> None:
        """Test registering default message handlers."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.domain.ports.websocket import MessageType

        mock_manager = MagicMock()
        _register_default_handlers(mock_manager)

        # Verify handlers were registered
        assert mock_manager.register_handler.call_count >= 4
        registered_types = [call[0][0] for call in mock_manager.register_handler.call_args_list]
        assert MessageType.PING in registered_types
        assert MessageType.CHAT_MESSAGE in registered_types
        assert MessageType.CHAT_TYPING in registered_types
        assert MessageType.CHAT_READ in registered_types


class TestDefaultMessageHandlers:
    """Tests for default message handler functions."""

    @pytest.mark.asyncio
    async def test_handle_ping_sends_pong(self) -> None:
        """Test ping handler sends pong response."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.domain.ports.websocket import MessageType, WebSocketMessage
        from app.infrastructure.websocket import ConnectionInfo

        mock_manager = MagicMock()
        mock_manager.send_to_connection = AsyncMock()

        # Capture handlers
        handlers = {}
        def capture_handler(msg_type, handler):
            handlers[msg_type] = handler
        mock_manager.register_handler = capture_handler

        _register_default_handlers(mock_manager)

        # Call ping handler
        connection = ConnectionInfo(
            connection_id="conn-123",
            user_id=uuid4(),
            tenant_id=uuid4(),
        )
        message = WebSocketMessage(
            type=MessageType.PING,
            payload={"timestamp": 12345},
        )

        await handlers[MessageType.PING](message, connection)

        mock_manager.send_to_connection.assert_called_once()
        call_args = mock_manager.send_to_connection.call_args
        assert call_args[0][0] == "conn-123"
        assert call_args[0][1].type == MessageType.PONG

    @pytest.mark.asyncio
    async def test_handle_chat_message_to_room(self) -> None:
        """Test chat message handler sends to room."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.domain.ports.websocket import MessageType, WebSocketMessage
        from app.infrastructure.websocket import ConnectionInfo

        mock_manager = MagicMock()
        mock_manager.send_to_room = AsyncMock()

        handlers = {}
        mock_manager.register_handler = lambda t, h: handlers.update({t: h})

        _register_default_handlers(mock_manager)

        connection = ConnectionInfo(
            connection_id="conn-123",
            user_id=uuid4(),
            tenant_id=uuid4(),
        )
        message = WebSocketMessage(
            type=MessageType.CHAT_MESSAGE,
            payload={"content": "Hello"},
            room_id="room-1",
        )

        await handlers[MessageType.CHAT_MESSAGE](message, connection)

        mock_manager.send_to_room.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_chat_message_to_user(self) -> None:
        """Test chat message handler sends direct message."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.domain.ports.websocket import MessageType, WebSocketMessage
        from app.infrastructure.websocket import ConnectionInfo

        mock_manager = MagicMock()
        mock_manager.send_to_user = AsyncMock()
        mock_manager.send_to_connection = AsyncMock()

        handlers = {}
        mock_manager.register_handler = lambda t, h: handlers.update({t: h})

        _register_default_handlers(mock_manager)

        recipient_id = uuid4()
        connection = ConnectionInfo(
            connection_id="conn-123",
            user_id=uuid4(),
            tenant_id=uuid4(),
        )
        message = WebSocketMessage(
            type=MessageType.CHAT_MESSAGE,
            payload={"content": "Hello"},
            recipient_id=recipient_id,
            message_id=uuid4(),
        )

        await handlers[MessageType.CHAT_MESSAGE](message, connection)

        mock_manager.send_to_user.assert_called_once()
        mock_manager.send_to_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_typing_to_room(self) -> None:
        """Test typing indicator to room."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.domain.ports.websocket import MessageType, WebSocketMessage
        from app.infrastructure.websocket import ConnectionInfo

        mock_manager = MagicMock()
        mock_manager.send_to_room = AsyncMock()

        handlers = {}
        mock_manager.register_handler = lambda t, h: handlers.update({t: h})

        _register_default_handlers(mock_manager)

        connection = ConnectionInfo(
            connection_id="conn-123",
            user_id=uuid4(),
            tenant_id=uuid4(),
        )
        message = WebSocketMessage(
            type=MessageType.CHAT_TYPING,
            payload={"is_typing": True},
            room_id="room-1",
        )

        await handlers[MessageType.CHAT_TYPING](message, connection)

        mock_manager.send_to_room.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_typing_to_user(self) -> None:
        """Test typing indicator to direct message recipient."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.domain.ports.websocket import MessageType, WebSocketMessage
        from app.infrastructure.websocket import ConnectionInfo

        mock_manager = MagicMock()
        mock_manager.send_to_user = AsyncMock()

        handlers = {}
        mock_manager.register_handler = lambda t, h: handlers.update({t: h})

        _register_default_handlers(mock_manager)

        recipient_id = uuid4()
        connection = ConnectionInfo(
            connection_id="conn-123",
            user_id=uuid4(),
            tenant_id=uuid4(),
        )
        message = WebSocketMessage(
            type=MessageType.CHAT_TYPING,
            payload={"is_typing": True},
            recipient_id=recipient_id,
        )

        await handlers[MessageType.CHAT_TYPING](message, connection)

        mock_manager.send_to_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_read_receipt(self) -> None:
        """Test read receipt handler."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.domain.ports.websocket import MessageType, WebSocketMessage
        from app.infrastructure.websocket import ConnectionInfo

        mock_manager = MagicMock()
        mock_manager.send_to_user = AsyncMock()

        handlers = {}
        mock_manager.register_handler = lambda t, h: handlers.update({t: h})

        _register_default_handlers(mock_manager)

        sender_id = uuid4()
        connection = ConnectionInfo(
            connection_id="conn-123",
            user_id=uuid4(),
            tenant_id=uuid4(),
        )
        message = WebSocketMessage(
            type=MessageType.CHAT_READ,
            payload={"message_ids": ["msg-1", "msg-2"]},
            sender_id=sender_id,
        )

        await handlers[MessageType.CHAT_READ](message, connection)

        mock_manager.send_to_user.assert_called_once_with(
            sender_id,
            mock_manager.send_to_user.call_args[0][1],
        )


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_message_from_dict(self) -> None:
        """Test creating message from dictionary."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType

        data = {
            "type": "ping",
            "payload": {"timestamp": 123},
        }
        message = WebSocketMessage.from_dict(data)

        assert message.type == MessageType.PING
        assert message.payload == {"timestamp": 123}

    def test_message_to_dict(self) -> None:
        """Test converting message to dictionary."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType

        message = WebSocketMessage(
            type=MessageType.CHAT_MESSAGE,
            payload={"content": "Hello"},
            room_id="room-1",
        )
        data = message.to_dict()

        assert data["type"] == "chat_message"
        assert data["payload"] == {"content": "Hello"}
        assert data["room_id"] == "room-1"

    def test_message_with_recipient(self) -> None:
        """Test message with recipient_id."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType

        recipient = uuid4()
        message = WebSocketMessage(
            type=MessageType.CHAT_MESSAGE,
            payload={},
            recipient_id=recipient,
        )

        assert message.recipient_id == recipient


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""

    def test_connection_info_creation(self) -> None:
        """Test creating ConnectionInfo."""
        from app.infrastructure.websocket import ConnectionInfo

        user_id = uuid4()
        tenant_id = uuid4()

        info = ConnectionInfo(
            connection_id="conn-123",
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert info.connection_id == "conn-123"
        assert info.user_id == user_id
        assert info.tenant_id == tenant_id
        assert info.metadata == {}
        assert info.rooms == set()

    def test_connection_info_with_metadata(self) -> None:
        """Test ConnectionInfo with metadata."""
        from app.infrastructure.websocket import ConnectionInfo

        info = ConnectionInfo(
            connection_id="conn-123",
            user_id=uuid4(),
            tenant_id=uuid4(),
            metadata={"type": "notifications"},
        )

        assert info.metadata == {"type": "notifications"}

    def test_connection_info_rooms(self) -> None:
        """Test ConnectionInfo with rooms."""
        from app.infrastructure.websocket import ConnectionInfo

        info = ConnectionInfo(
            connection_id="conn-123",
            user_id=uuid4(),
            tenant_id=uuid4(),
            rooms={"room-1", "room-2"},
        )

        assert "room-1" in info.rooms
        assert "room-2" in info.rooms


class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_type_values(self) -> None:
        """Test MessageType enum values."""
        from app.domain.ports.websocket import MessageType

        assert MessageType.PING.value == "ping"
        assert MessageType.PONG.value == "pong"
        assert MessageType.CHAT_MESSAGE.value == "chat_message"
        assert MessageType.NOTIFICATION.value == "notification"

    def test_message_type_from_string(self) -> None:
        """Test creating MessageType from string."""
        from app.domain.ports.websocket import MessageType

        assert MessageType("ping") == MessageType.PING
        assert MessageType("chat_message") == MessageType.CHAT_MESSAGE
