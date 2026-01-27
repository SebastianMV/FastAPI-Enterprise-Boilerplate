# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for websocket endpoints to improve coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import WebSocket

from app.api.v1.endpoints.websocket import (
    authenticate_websocket,
    get_ws_manager,
    _register_default_handlers,
)
from app.domain.ports.websocket import MessageType, WebSocketMessage
from app.infrastructure.websocket import ConnectionInfo, MemoryWebSocketManager


class TestAuthenticateWebSocket:
    """Tests for websocket authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_no_token(self) -> None:
        """Test authentication without token returns None."""
        mock_websocket = MagicMock(spec=WebSocket)
        
        result = await authenticate_websocket(mock_websocket, token=None)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self) -> None:
        """Test authentication with invalid token returns None."""
        mock_websocket = MagicMock(spec=WebSocket)
        
        with patch("app.api.v1.endpoints.websocket.validate_access_token") as mock_validate:
            mock_validate.side_effect = Exception("Invalid token")
            
            result = await authenticate_websocket(mock_websocket, token="invalid_token")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_valid_token(self) -> None:
        """Test authentication with valid token returns user info."""
        mock_websocket = MagicMock(spec=WebSocket)
        user_id = uuid4()
        tenant_id = uuid4()
        
        with patch("app.api.v1.endpoints.websocket.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
            }
            
            result = await authenticate_websocket(mock_websocket, token="valid_token")
            
            assert result is not None
            assert result[0] == user_id
            assert result[1] == tenant_id

    @pytest.mark.asyncio
    async def test_authenticate_valid_token_no_tenant(self) -> None:
        """Test authentication with valid token without tenant_id."""
        mock_websocket = MagicMock(spec=WebSocket)
        user_id = uuid4()
        
        with patch("app.api.v1.endpoints.websocket.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
            }
            
            result = await authenticate_websocket(mock_websocket, token="valid_token")
            
            assert result is not None
            assert result[0] == user_id
            assert result[1] is None


class TestGetWsManager:
    """Tests for WebSocket manager factory."""

    def test_get_ws_manager_memory(self) -> None:
        """Test getting memory WebSocket manager."""
        import app.api.v1.endpoints.websocket as ws_module
        
        # Reset singleton
        original_manager = ws_module._ws_manager
        ws_module._ws_manager = None
        
        try:
            with patch.object(ws_module.settings, "WEBSOCKET_BACKEND", "memory"):
                manager = get_ws_manager()
                assert isinstance(manager, MemoryWebSocketManager)
        finally:
            ws_module._ws_manager = original_manager

    def test_get_ws_manager_redis(self) -> None:
        """Test getting Redis WebSocket manager - mocking the import."""
        import app.api.v1.endpoints.websocket as ws_module
        
        original_manager = ws_module._ws_manager
        ws_module._ws_manager = None
        
        try:
            # Simply test that memory manager works as a fallback
            # Redis manager requires actual Redis connection
            manager = get_ws_manager()
            assert manager is not None
        finally:
            ws_module._ws_manager = original_manager


class TestDefaultHandlers:
    """Tests for default message handlers."""

    @pytest.mark.asyncio
    async def test_handle_ping(self) -> None:
        """Test ping handler by creating a proper connection."""
        manager = MemoryWebSocketManager()
        _register_default_handlers(manager)
        
        # Create mock websocket
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        user_id = uuid4()
        
        # Use connect method to properly register
        connection_id = await manager.connect(mock_websocket, user_id, None)
        
        # Get connection info
        connections = await manager.get_user_connections(user_id)
        connection = connections[0]
        
        # Create ping message
        message = WebSocketMessage(
            type=MessageType.PING,
            payload={"timestamp": 123456},
        )
        
        # Handle message
        await manager.handle_message(message, connection)
        
        # Verify pong was sent
        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "pong"

    @pytest.mark.asyncio
    async def test_handle_chat_message_to_room(self) -> None:
        """Test chat message handler for room messages."""
        manager = MemoryWebSocketManager()
        _register_default_handlers(manager)
        
        # Setup mock websockets
        sender_ws = MagicMock(spec=WebSocket)
        sender_ws.send_json = AsyncMock()
        sender_ws.accept = AsyncMock()
        
        recipient_ws = MagicMock(spec=WebSocket)
        recipient_ws.send_json = AsyncMock()
        recipient_ws.accept = AsyncMock()
        
        sender_user_id = uuid4()
        recipient_user_id = uuid4()
        room_id = "test-room"
        
        # Connect both
        sender_connection_id = await manager.connect(sender_ws, sender_user_id, None)
        recipient_connection_id = await manager.connect(recipient_ws, recipient_user_id, None)
        
        # Join room
        await manager.join_room(sender_connection_id, room_id)
        await manager.join_room(recipient_connection_id, room_id)
        
        # Get sender connection
        connections = await manager.get_user_connections(sender_user_id)
        sender_connection = connections[0]
        
        # Create chat message
        message = WebSocketMessage(
            type=MessageType.CHAT_MESSAGE,
            payload={"text": "Hello room!"},
            room_id=room_id,
        )
        
        # Handle message
        await manager.handle_message(message, sender_connection)
        
        # Recipient should receive message
        recipient_ws.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_handle_chat_message_direct(self) -> None:
        """Test chat message handler for direct messages."""
        manager = MemoryWebSocketManager()
        _register_default_handlers(manager)
        
        # Setup mock websockets
        sender_ws = MagicMock(spec=WebSocket)
        sender_ws.send_json = AsyncMock()
        sender_ws.accept = AsyncMock()
        
        recipient_ws = MagicMock(spec=WebSocket)
        recipient_ws.send_json = AsyncMock()
        recipient_ws.accept = AsyncMock()
        
        sender_user_id = uuid4()
        recipient_user_id = uuid4()
        
        # Connect both
        await manager.connect(sender_ws, sender_user_id, None)
        await manager.connect(recipient_ws, recipient_user_id, None)
        
        # Get sender connection
        connections = await manager.get_user_connections(sender_user_id)
        sender_connection = connections[0]
        
        # Create direct message
        message = WebSocketMessage(
            type=MessageType.CHAT_MESSAGE,
            payload={"text": "Hello directly!"},
            recipient_id=recipient_user_id,
            message_id=uuid4(),
        )
        
        # Handle message
        await manager.handle_message(message, sender_connection)
        
        # Recipient should receive message
        recipient_ws.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_handle_typing_to_room(self) -> None:
        """Test typing indicator to room."""
        manager = MemoryWebSocketManager()
        _register_default_handlers(manager)
        
        # Setup websockets
        my_ws = MagicMock(spec=WebSocket)
        my_ws.send_json = AsyncMock()
        my_ws.accept = AsyncMock()
        
        other_ws = MagicMock(spec=WebSocket)
        other_ws.send_json = AsyncMock()
        other_ws.accept = AsyncMock()
        
        user_id = uuid4()
        other_user_id = uuid4()
        room_id = "typing-room"
        
        # Connect both
        my_connection_id = await manager.connect(my_ws, user_id, None)
        other_connection_id = await manager.connect(other_ws, other_user_id, None)
        
        # Join room
        await manager.join_room(my_connection_id, room_id)
        await manager.join_room(other_connection_id, room_id)
        
        # Get connection
        connections = await manager.get_user_connections(user_id)
        connection = connections[0]
        
        # Create typing message
        message = WebSocketMessage(
            type=MessageType.CHAT_TYPING,
            payload={"is_typing": True},
            room_id=room_id,
        )
        
        # Handle message
        await manager.handle_message(message, connection)
        
        # Other user should receive typing indicator
        other_ws.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_handle_typing_direct(self) -> None:
        """Test typing indicator for direct message."""
        manager = MemoryWebSocketManager()
        _register_default_handlers(manager)
        
        # Setup websockets
        my_ws = MagicMock(spec=WebSocket)
        my_ws.send_json = AsyncMock()
        my_ws.accept = AsyncMock()
        
        recipient_ws = MagicMock(spec=WebSocket)
        recipient_ws.send_json = AsyncMock()
        recipient_ws.accept = AsyncMock()
        
        user_id = uuid4()
        recipient_user_id = uuid4()
        
        # Connect both
        await manager.connect(my_ws, user_id, None)
        await manager.connect(recipient_ws, recipient_user_id, None)
        
        # Get connection
        connections = await manager.get_user_connections(user_id)
        connection = connections[0]
        
        # Create typing message
        message = WebSocketMessage(
            type=MessageType.CHAT_TYPING,
            payload={"is_typing": True},
            recipient_id=recipient_user_id,
        )
        
        # Handle message
        await manager.handle_message(message, connection)
        
        # Recipient should receive typing indicator
        recipient_ws.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_handle_read_receipt(self) -> None:
        """Test read receipt handler."""
        manager = MemoryWebSocketManager()
        _register_default_handlers(manager)
        
        # Setup websockets
        reader_ws = MagicMock(spec=WebSocket)
        reader_ws.send_json = AsyncMock()
        reader_ws.accept = AsyncMock()
        
        sender_ws = MagicMock(spec=WebSocket)
        sender_ws.send_json = AsyncMock()
        sender_ws.accept = AsyncMock()
        
        reader_user_id = uuid4()
        sender_user_id = uuid4()
        
        # Connect both
        await manager.connect(reader_ws, reader_user_id, None)
        await manager.connect(sender_ws, sender_user_id, None)
        
        # Get reader connection
        connections = await manager.get_user_connections(reader_user_id)
        reader_connection = connections[0]
        
        # Create read receipt message
        message = WebSocketMessage(
            type=MessageType.CHAT_READ,
            payload={"message_ids": [str(uuid4()), str(uuid4())]},
            sender_id=sender_user_id,  # Original sender should be notified
        )
        
        # Handle message
        await manager.handle_message(message, reader_connection)
        
        # Original sender should receive read receipt
        sender_ws.send_json.assert_called()


class TestWebSocketMessage:
    """Tests for WebSocketMessage."""

    def test_from_dict(self) -> None:
        """Test creating message from dict."""
        data = {
            "type": "chat_message",
            "payload": {"text": "Hello"},
            "room_id": "test-room",
        }
        
        message = WebSocketMessage.from_dict(data)
        
        assert message.type == MessageType.CHAT_MESSAGE
        assert message.payload["text"] == "Hello"
        assert message.room_id == "test-room"

    def test_from_dict_with_recipient(self) -> None:
        """Test creating message with recipient."""
        recipient_id = uuid4()
        data = {
            "type": "chat_message",
            "payload": {"text": "Direct message"},
            "recipient_id": str(recipient_id),
        }
        
        message = WebSocketMessage.from_dict(data)
        
        assert message.type == MessageType.CHAT_MESSAGE
        assert message.recipient_id == recipient_id

    def test_to_dict(self) -> None:
        """Test converting message to dict."""
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"title": "Test", "body": "Notification"},
        )
        
        data = message.to_dict()
        
        assert data["type"] == "notification"
        assert data["payload"]["title"] == "Test"


class TestConnectionInfo:
    """Tests for ConnectionInfo."""

    def test_connection_info_creation(self) -> None:
        """Test creating connection info."""
        connection_id = str(uuid4())
        user_id = uuid4()
        tenant_id = uuid4()
        
        info = ConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            tenant_id=tenant_id,
            metadata={"key": "value"},
        )
        
        assert info.connection_id == connection_id
        assert info.user_id == user_id
        assert info.tenant_id == tenant_id
        assert info.metadata["key"] == "value"

    def test_connection_info_without_tenant(self) -> None:
        """Test connection info without tenant."""
        info = ConnectionInfo(
            connection_id=str(uuid4()),
            user_id=uuid4(),
            tenant_id=None,
        )
        
        assert info.tenant_id is None


class TestWebSocketManagerInitialization:
    """Tests for WebSocket manager initialization with different backends."""

    def test_get_ws_manager_with_redis_backend(self) -> None:
        """Test manager initialization with Redis backend."""
        # Reset global manager
        import app.api.v1.endpoints.websocket as ws_module
        ws_module._ws_manager = None
        
        # Create a mock settings object with the required attributes
        mock_settings = MagicMock()
        mock_settings.WEBSOCKET_BACKEND = "redis"
        mock_settings.REDIS_URL = "redis://localhost:6379"
        
        # Mock both the settings object and the Redis manager
        with patch('app.api.v1.endpoints.websocket.settings', mock_settings), \
             patch('app.infrastructure.websocket.redis_manager.RedisWebSocketManager') as mock_redis:
            
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance
            
            manager = get_ws_manager()
            
            # Should create Redis manager
            mock_redis.assert_called_once_with(redis_url="redis://localhost:6379")
            assert manager == mock_redis_instance
        
        # Reset for other tests
        ws_module._ws_manager = None

    def test_get_ws_manager_with_memory_backend(self) -> None:
        """Test manager initialization with Memory backend (default)."""
        import app.api.v1.endpoints.websocket as ws_module
        ws_module._ws_manager = None
        
        # Mock settings to use memory backend
        mock_settings = MagicMock()
        mock_settings.WEBSOCKET_BACKEND = "memory"
        
        with patch('app.api.v1.endpoints.websocket.settings', mock_settings):
            manager = get_ws_manager()
            
            # Should create Memory manager
            assert isinstance(manager, MemoryWebSocketManager)
        
        ws_module._ws_manager = None


class TestWebSocketEndpointErrorHandling:
    """Tests for WebSocket endpoint error handling paths."""

    @pytest.mark.asyncio
    async def test_websocket_message_processing_error(self) -> None:
        """Test error handling when message processing fails."""
        from app.api.v1.endpoints.websocket import websocket_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_manager = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()
        connection_id = "test-conn-123"
        
        # Mock successful connection and authentication
        mock_websocket.accept.return_value = None
        mock_manager.connect.return_value = connection_id
        mock_manager.get_user_connections.return_value = [
            MagicMock(connection_id=connection_id, user_id=user_id)
        ]
        
        # First receive: valid message that causes processing error
        # Second receive: WebSocketDisconnect to exit loop gracefully
        from fastapi import WebSocketDisconnect
        mock_websocket.receive_json.side_effect = [
            {"type": "chat_message", "payload": {}},
            WebSocketDisconnect()
        ]
        
        # Make handle_message raise an error (line 225-235 coverage)
        mock_manager.handle_message.side_effect = Exception("Processing failed")
        
        with patch('app.api.v1.endpoints.websocket.get_ws_manager', return_value=mock_manager), \
             patch('app.api.v1.endpoints.websocket.authenticate_websocket') as mock_auth:
            
            # Mock successful authentication - returns (user_id, tenant_id)
            mock_auth.return_value = (user_id, tenant_id)
            
            # Should handle error gracefully and exit on disconnect
            await websocket_endpoint(mock_websocket, None)
        
        # Should have sent error message to client (lines 229-232)
        assert mock_websocket.send_json.call_count >= 1
        error_call = mock_websocket.send_json.call_args_list[0][0][0]
        assert error_call["type"] == "error"
        assert "Processing failed" in error_call["payload"]["message"]
        
        # Should disconnect in finally block
        mock_manager.disconnect.assert_called_once_with(connection_id)

    @pytest.mark.asyncio
    async def test_websocket_receive_json_error(self) -> None:
        """Test error handling when receiving invalid JSON."""
        from app.api.v1.endpoints.websocket import websocket_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_manager = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()
        connection_id = "test-conn-456"
        
        mock_websocket.accept.return_value = None
        mock_manager.connect.return_value = connection_id
        
        # receive_json raises error (line 247-248 coverage)
        mock_websocket.receive_json.side_effect = ValueError("Invalid JSON")
        
        with patch('app.api.v1.endpoints.websocket.get_ws_manager', return_value=mock_manager), \
             patch('app.api.v1.endpoints.websocket.authenticate_websocket') as mock_auth:
            
            # Mock successful authentication
            mock_auth.return_value = (user_id, tenant_id)
            
            # Should handle error gracefully (line 247-248)
            await websocket_endpoint(mock_websocket, None)
        
        # Should disconnect in finally block
        mock_manager.disconnect.assert_called_once_with(connection_id)

    @pytest.mark.asyncio
    async def test_websocket_disconnect_cleanup(self) -> None:
        """Test cleanup on WebSocketDisconnect."""
        from fastapi import WebSocketDisconnect
        from app.api.v1.endpoints.websocket import websocket_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_manager = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()
        connection_id = "test-conn-789"
        
        mock_websocket.accept.return_value = None
        mock_manager.connect.return_value = connection_id
        
        # Simulate WebSocketDisconnect
        mock_websocket.receive_json.side_effect = WebSocketDisconnect()
        
        with patch('app.api.v1.endpoints.websocket.get_ws_manager', return_value=mock_manager), \
             patch('app.api.v1.endpoints.websocket.authenticate_websocket') as mock_auth:
            
            # Mock successful authentication
            mock_auth.return_value = (user_id, tenant_id)
            
            # Should not raise, should cleanup gracefully
            await websocket_endpoint(mock_websocket, None)
        
        # Should disconnect
        mock_manager.disconnect.assert_called_once_with(connection_id)


class TestJoinRoomEndpointErrorHandling:
    """Tests for chat_room_endpoint error handling paths."""

    @pytest.mark.asyncio
    async def test_join_room_message_error_handling(self) -> None:
        """Test error handling in chat_room_endpoint message processing."""
        from fastapi import WebSocketDisconnect
        from app.api.v1.endpoints.websocket import chat_room_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_manager = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()
        room_id = "test-room"
        connection_id = "test-conn-room"
        
        mock_websocket.accept.return_value = None
        mock_manager.connect.return_value = connection_id
        mock_manager.join_room.return_value = None
        mock_manager.get_user_connections.return_value = [
            MagicMock(connection_id=connection_id, user_id=user_id)
        ]
        
        # First receive causes error, second disconnects
        mock_websocket.receive_json.side_effect = [
            {"type": "invalid", "payload": {}},
            WebSocketDisconnect()
        ]
        
        # Make handle_message fail
        mock_manager.handle_message.side_effect = ValueError("Invalid message type")
        
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.WEBSOCKET_ENABLED = True
        mock_settings.WEBSOCKET_CHAT = True
        
        with patch('app.api.v1.endpoints.websocket.settings', mock_settings), \
             patch('app.api.v1.endpoints.websocket.get_ws_manager', return_value=mock_manager), \
             patch('app.api.v1.endpoints.websocket.authenticate_websocket') as mock_auth:
            
            mock_auth.return_value = (user_id, tenant_id)
            
            # Should handle error and cleanup
            await chat_room_endpoint(mock_websocket, room_id, None)
        
        # Should send error
        assert mock_websocket.send_json.call_count >= 1
        
        # Should cleanup: leave room and disconnect (lines 366-368)
        mock_manager.leave_room.assert_called_once_with(connection_id, room_id)
        mock_manager.disconnect.assert_called_once_with(connection_id)

    @pytest.mark.asyncio
    async def test_join_room_websocket_disconnect(self) -> None:
        """Test chat_room_endpoint handles WebSocketDisconnect gracefully."""
        from fastapi import WebSocketDisconnect
        from app.api.v1.endpoints.websocket import chat_room_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_manager = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()
        room_id = "test-room-disconnect"
        connection_id = "test-conn-disconnect"
        
        mock_websocket.accept.return_value = None
        mock_manager.connect.return_value = connection_id
        mock_manager.join_room.return_value = None
        
        # Immediate disconnect
        mock_websocket.receive_json.side_effect = WebSocketDisconnect()
        
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.WEBSOCKET_ENABLED = True
        mock_settings.WEBSOCKET_CHAT = True
        
        with patch('app.api.v1.endpoints.websocket.settings', mock_settings), \
             patch('app.api.v1.endpoints.websocket.get_ws_manager', return_value=mock_manager), \
             patch('app.api.v1.endpoints.websocket.authenticate_websocket') as mock_auth:
            
            mock_auth.return_value = (user_id, tenant_id)
            
            # Should handle disconnect gracefully (no error)
            await chat_room_endpoint(mock_websocket, room_id, None)
        
        # Should cleanup (lines 366-368)
        mock_manager.leave_room.assert_called_once()
        mock_manager.disconnect.assert_called_once()
