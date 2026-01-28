# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for WebSocket endpoint module.

Tests for WebSocket authentication and message handling.
"""

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetWsManager:
    """Tests for get_ws_manager function."""

    def test_get_ws_manager_returns_manager(self) -> None:
        """Test getting WebSocket manager returns a manager instance."""
        from app.api.v1.endpoints.websocket import get_ws_manager
        
        # Reset global manager
        import app.api.v1.endpoints.websocket as ws_module
        ws_module._ws_manager = None
        
        with patch.object(ws_module.settings, 'WEBSOCKET_BACKEND', 'memory'):
            manager = get_ws_manager()
        
        assert manager is not None
        # Cleanup
        ws_module._ws_manager = None

    def test_get_ws_manager_singleton(self) -> None:
        """Test that get_ws_manager returns same instance."""
        from app.api.v1.endpoints.websocket import get_ws_manager
        
        import app.api.v1.endpoints.websocket as ws_module
        ws_module._ws_manager = None
        
        with patch.object(ws_module.settings, 'WEBSOCKET_BACKEND', 'memory'):
            manager1 = get_ws_manager()
            manager2 = get_ws_manager()
        
        assert manager1 is manager2
        ws_module._ws_manager = None


class TestAuthenticateWebsocket:
    """Tests for authenticate_websocket function."""

    @pytest.mark.asyncio
    async def test_authenticate_no_token(self) -> None:
        """Test authentication fails without token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket

        mock_websocket = AsyncMock()
        result = await authenticate_websocket(mock_websocket, token=None)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_valid_token(self) -> None:
        """Test authentication with valid token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket

        mock_websocket = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()

        with patch(
            "app.api.v1.endpoints.websocket.validate_access_token"
        ) as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
            }
            
            result = await authenticate_websocket(mock_websocket, token="valid-token")
        
        assert result is not None
        assert result[0] == user_id
        assert result[1] == tenant_id

    @pytest.mark.asyncio
    async def test_authenticate_valid_token_no_tenant(self) -> None:
        """Test authentication with token without tenant."""
        from app.api.v1.endpoints.websocket import authenticate_websocket

        mock_websocket = AsyncMock()
        user_id = uuid4()

        with patch(
            "app.api.v1.endpoints.websocket.validate_access_token"
        ) as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": None,
            }
            
            result = await authenticate_websocket(mock_websocket, token="valid-token")
        
        assert result is not None
        assert result[0] == user_id
        assert result[1] is None

    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self) -> None:
        """Test authentication with invalid token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket

        mock_websocket = AsyncMock()

        with patch(
            "app.api.v1.endpoints.websocket.validate_access_token"
        ) as mock_validate:
            mock_validate.side_effect = Exception("Invalid token")
            
            result = await authenticate_websocket(mock_websocket, token="invalid-token")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_expired_token(self) -> None:
        """Test authentication with expired token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket

        mock_websocket = AsyncMock()

        with patch(
            "app.api.v1.endpoints.websocket.validate_access_token"
        ) as mock_validate:
            mock_validate.side_effect = Exception("Token expired")
            
            result = await authenticate_websocket(mock_websocket, token="expired-token")
        
        assert result is None


class TestRegisterDefaultHandlers:
    """Tests for _register_default_handlers function."""

    def test_register_handlers(self) -> None:
        """Test that default handlers are registered."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.domain.ports.websocket import MessageType

        mock_manager = MagicMock()
        mock_manager.register_handler = MagicMock()

        _register_default_handlers(mock_manager)

        # Should register handler for PING only (chat removed)
        assert mock_manager.register_handler.call_count == 1

        # Check registered message types
        registered_types = [
            call[0][0] for call in mock_manager.register_handler.call_args_list
        ]
        assert MessageType.PING in registered_types


class TestDefaultMessageHandlers:
    """Tests for default message handler functions."""

    @pytest.mark.asyncio
    async def test_handle_ping(self) -> None:
        """Test ping handler sends pong response."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.domain.ports.websocket import (
            ConnectionInfo,
            MessageType,
            WebSocketMessage,
        )

        # Capture the registered handler
        handlers = {}
        
        def mock_register(msg_type, handler):
            handlers[msg_type] = handler

        mock_manager = MagicMock()
        mock_manager.register_handler = mock_register
        mock_manager.send_to_connection = AsyncMock()

        _register_default_handlers(mock_manager)

        # Call ping handler
        ping_message = WebSocketMessage(
            type=MessageType.PING,
            payload={"timestamp": 1234567890},
        )
        connection = ConnectionInfo(
            connection_id="conn-1",
            user_id=uuid4(),
            tenant_id=uuid4(),
        )

        await handlers[MessageType.PING](ping_message, connection)

        mock_manager.send_to_connection.assert_called_once()
        call_args = mock_manager.send_to_connection.call_args
        assert call_args[0][0] == "conn-1"
        assert call_args[0][1].type == MessageType.PONG


class TestWebSocketMessageTypes:
    """Tests for WebSocket message types."""

    def test_message_type_values(self) -> None:
        """Test MessageType enum values."""
        from app.domain.ports.websocket import MessageType

        assert MessageType.PING.value == "ping"
        assert MessageType.PONG.value == "pong"
        assert MessageType.NOTIFICATION.value == "notification"
        assert MessageType.NOTIFICATION_READ.value == "notification_read"
        assert MessageType.BROADCAST.value == "broadcast"

    def test_websocket_message_creation(self) -> None:
        """Test creating WebSocketMessage."""
        from app.domain.ports.websocket import MessageType, WebSocketMessage

        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"text": "Hello"},
        )

        assert message.type == MessageType.NOTIFICATION
        assert message.payload == {"text": "Hello"}
        assert message.timestamp is not None

    def test_websocket_message_with_recipient(self) -> None:
        """Test WebSocketMessage with recipient."""
        from app.domain.ports.websocket import MessageType, WebSocketMessage

        recipient_id = uuid4()
        sender_id = uuid4()
        
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"text": "DM"},
            recipient_id=recipient_id,
            sender_id=sender_id,
        )

        assert message.recipient_id == recipient_id
        assert message.sender_id == sender_id

    def test_websocket_message_with_room(self) -> None:
        """Test WebSocketMessage with room."""
        from app.domain.ports.websocket import MessageType, WebSocketMessage

        message = WebSocketMessage(
            type=MessageType.BROADCAST,
            payload={"text": "Room message"},
            room_id="general",
        )

        assert message.room_id == "general"

    def test_websocket_message_from_dict(self) -> None:
        """Test creating WebSocketMessage from dict."""
        from app.domain.ports.websocket import WebSocketMessage

        data = {
            "type": "notification",
            "payload": {"text": "Hello from dict"},
        }

        message = WebSocketMessage.from_dict(data)

        assert message.payload == {"text": "Hello from dict"}


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""

    def test_connection_info_creation(self) -> None:
        """Test creating ConnectionInfo."""
        from app.domain.ports.websocket import ConnectionInfo

        user_id = uuid4()
        tenant_id = uuid4()

        conn = ConnectionInfo(
            connection_id="conn-abc",
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert conn.connection_id == "conn-abc"
        assert conn.user_id == user_id
        assert conn.tenant_id == tenant_id
        # rooms is a set by default
        assert len(conn.rooms) == 0

    def test_connection_info_with_rooms(self) -> None:
        """Test ConnectionInfo with rooms."""
        from app.domain.ports.websocket import ConnectionInfo

        conn = ConnectionInfo(
            connection_id="conn-xyz",
            user_id=uuid4(),
            tenant_id=uuid4(),
            rooms=["room1", "room2"],
        )

        assert len(conn.rooms) == 2
        assert "room1" in conn.rooms
        assert "room2" in conn.rooms

    def test_connection_info_without_tenant(self) -> None:
        """Test ConnectionInfo without tenant."""
        from app.domain.ports.websocket import ConnectionInfo

        conn = ConnectionInfo(
            connection_id="conn-no-tenant",
            user_id=uuid4(),
            tenant_id=None,
        )

        assert conn.tenant_id is None


class TestWebSocketEndpointFlow:
    """Tests for WebSocket endpoint connection flow."""

    @pytest.mark.asyncio
    async def test_websocket_disabled(self) -> None:
        """Test WebSocket connection when disabled."""
        from app.api.v1.endpoints.websocket import websocket_endpoint
        import app.api.v1.endpoints.websocket as ws_module

        mock_websocket = AsyncMock()
        mock_websocket.close = AsyncMock()

        with patch.object(ws_module.settings, 'WEBSOCKET_ENABLED', False):
            await websocket_endpoint(mock_websocket, token="some-token")

        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_no_auth(self) -> None:
        """Test WebSocket connection without authentication."""
        from app.api.v1.endpoints.websocket import websocket_endpoint
        import app.api.v1.endpoints.websocket as ws_module

        mock_websocket = AsyncMock()
        mock_websocket.close = AsyncMock()

        with patch.object(ws_module.settings, 'WEBSOCKET_ENABLED', True):
            with patch(
                "app.api.v1.endpoints.websocket.authenticate_websocket",
                return_value=None,
            ):
                await websocket_endpoint(mock_websocket, token=None)

        mock_websocket.close.assert_called_once()


class TestWebSocketModuleImports:
    """Tests for websocket module imports."""

    def test_memory_manager_import(self) -> None:
        """Test MemoryWebSocketManager can be imported."""
        from app.infrastructure.websocket import MemoryWebSocketManager
        assert MemoryWebSocketManager is not None

    def test_connection_info_import(self) -> None:
        """Test ConnectionInfo can be imported."""
        from app.infrastructure.websocket import ConnectionInfo
        assert ConnectionInfo is not None

    def test_message_type_import(self) -> None:
        """Test MessageType can be imported."""
        from app.infrastructure.websocket import MessageType
        assert MessageType is not None

    def test_websocket_message_import(self) -> None:
        """Test WebSocketMessage can be imported."""
        from app.infrastructure.websocket import WebSocketMessage
        assert WebSocketMessage is not None

    def test_websocket_port_import(self) -> None:
        """Test WebSocketPort can be imported."""
        from app.infrastructure.websocket import WebSocketPort
        assert WebSocketPort is not None

    def test_get_redis_manager_function(self) -> None:
        """Test get_redis_manager function exists."""
        from app.infrastructure.websocket import get_redis_manager
        assert callable(get_redis_manager)

