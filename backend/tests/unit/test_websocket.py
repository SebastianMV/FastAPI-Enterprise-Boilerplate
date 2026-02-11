# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit Tests - WebSocket Manager.

Tests for WebSocket connection management and message handling.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio

from app.domain.ports.websocket import (
    ConnectionInfo,
    MessageType,
    WebSocketMessage,
)
from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_message_to_dict(self) -> None:
        """Test message serialization to dict."""
        user_id = uuid4()
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"text": "Hello"},
            sender_id=user_id,
        )

        data = message.to_dict()

        assert data["type"] == "notification"
        assert data["payload"]["text"] == "Hello"
        assert data["sender_id"] == str(user_id)
        assert "timestamp" in data

    def test_message_from_dict(self) -> None:
        """Test message deserialization from dict."""
        user_id = uuid4()
        data = {
            "type": "notification",
            "payload": {"title": "Test"},
            "sender_id": str(user_id),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        message = WebSocketMessage.from_dict(data)

        assert message.type == MessageType.NOTIFICATION
        assert message.payload["title"] == "Test"
        assert message.sender_id == user_id

    def test_message_from_dict_minimal(self) -> None:
        """Test message deserialization with minimal data."""
        data = {"type": "ping", "payload": {}}

        message = WebSocketMessage.from_dict(data)

        assert message.type == MessageType.PING
        assert message.payload == {}
        assert message.sender_id is None
        assert message.recipient_id is None

    def test_message_types_enum(self) -> None:
        """Test all message types are accessible."""
        types = [
            MessageType.CONNECTED,
            MessageType.DISCONNECTED,
            MessageType.PING,
            MessageType.PONG,
            MessageType.NOTIFICATION,
            MessageType.PRESENCE_ONLINE,
            MessageType.PRESENCE_OFFLINE,
        ]

        for msg_type in types:
            assert isinstance(msg_type.value, str)


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""

    def test_connection_info_creation(self) -> None:
        """Test creating connection info."""
        user_id = uuid4()
        tenant_id = uuid4()

        info = ConnectionInfo(
            user_id=user_id,
            tenant_id=tenant_id,
            connection_id="conn_123",
        )

        assert info.user_id == user_id
        assert info.tenant_id == tenant_id
        assert info.connection_id == "conn_123"
        assert isinstance(info.rooms, set)
        assert isinstance(info.metadata, dict)

    def test_connection_info_rooms(self) -> None:
        """Test connection info with rooms."""
        info = ConnectionInfo(
            user_id=uuid4(),
            tenant_id=uuid4(),
            connection_id="conn_123",
            rooms={"room1", "room2"},
        )

        assert "room1" in info.rooms
        assert "room2" in info.rooms


class TestMemoryWebSocketManager:
    """Tests for in-memory WebSocket manager."""

    @pytest_asyncio.fixture
    async def manager(self) -> MemoryWebSocketManager:
        """Create a fresh manager for each test."""
        return MemoryWebSocketManager()

    @pytest.fixture
    def mock_websocket(self) -> MagicMock:
        """Create a mock WebSocket."""
        ws = MagicMock()
        ws.send_json = AsyncMock()
        ws.receive_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_manager_backend_name(self, manager: MemoryWebSocketManager) -> None:
        """Test manager backend name."""
        assert manager.backend_name == "memory"

    @pytest.mark.asyncio
    async def test_connect(
        self, manager: MemoryWebSocketManager, mock_websocket: MagicMock
    ) -> None:
        """Test WebSocket connection registration."""
        user_id = uuid4()
        tenant_id = uuid4()

        connection_id = await manager.connect(
            mock_websocket,
            user_id,
            tenant_id,
        )

        assert connection_id is not None
        assert isinstance(connection_id, str)

        # Verify connected message was sent
        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connected"

    @pytest.mark.asyncio
    async def test_disconnect(
        self, manager: MemoryWebSocketManager, mock_websocket: MagicMock
    ) -> None:
        """Test WebSocket disconnection."""
        user_id = uuid4()

        connection_id = await manager.connect(mock_websocket, user_id)

        # User should be online
        assert await manager.is_user_online(user_id)

        await manager.disconnect(connection_id)

        # User should be offline
        assert not await manager.is_user_online(user_id)

    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(
        self, manager: MemoryWebSocketManager
    ) -> None:
        """Test multiple connections from same user."""
        user_id = uuid4()

        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()

        conn1 = await manager.connect(ws1, user_id)
        conn2 = await manager.connect(ws2, user_id)

        assert conn1 != conn2

        connections = await manager.get_user_connections(user_id)
        assert len(connections) == 2

        # Disconnect one, user still online
        await manager.disconnect(conn1)
        assert await manager.is_user_online(user_id)

        # Disconnect other, user offline
        await manager.disconnect(conn2)
        assert not await manager.is_user_online(user_id)

    @pytest.mark.asyncio
    async def test_send_to_user(
        self, manager: MemoryWebSocketManager, mock_websocket: MagicMock
    ) -> None:
        """Test sending message to specific user."""
        user_id = uuid4()

        await manager.connect(mock_websocket, user_id)

        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"title": "Test Notification"},
        )

        await manager.send_to_user(user_id, message)

        # Verify message was sent (connected + notification)
        assert mock_websocket.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_user(
        self, manager: MemoryWebSocketManager
    ) -> None:
        """Test sending to user with no connections."""
        user_id = uuid4()

        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"title": "Test"},
        )

        # Should not raise, just log warning
        await manager.send_to_user(user_id, message)

    @pytest.mark.asyncio
    async def test_join_room(
        self, manager: MemoryWebSocketManager, mock_websocket: MagicMock
    ) -> None:
        """Test joining a room."""
        user_id = uuid4()
        room_id = "test-room"

        conn_id = await manager.connect(mock_websocket, user_id)

        await manager.join_room(conn_id, room_id)

        # Verify user is in room
        members = await manager.get_room_members(room_id)
        assert len(members) == 1
        assert members[0].connection_id == conn_id

    @pytest.mark.asyncio
    async def test_leave_room(
        self, manager: MemoryWebSocketManager, mock_websocket: MagicMock
    ) -> None:
        """Test leaving a room."""
        user_id = uuid4()
        room_id = "test-room"

        conn_id = await manager.connect(mock_websocket, user_id)
        await manager.join_room(conn_id, room_id)

        await manager.leave_room(conn_id, room_id)

        members = await manager.get_room_members(room_id)
        assert len(members) == 0

    @pytest.mark.asyncio
    async def test_send_to_room(self, manager: MemoryWebSocketManager) -> None:
        """Test broadcasting to room."""
        user1 = uuid4()
        user2 = uuid4()
        room_id = "chat-room"

        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()

        conn1 = await manager.connect(ws1, user1)
        conn2 = await manager.connect(ws2, user2)

        await manager.join_room(conn1, room_id)
        await manager.join_room(conn2, room_id)

        message = WebSocketMessage(
            type=MessageType.BROADCAST,
            payload={"text": "Hello room!"},
            sender_id=user1,
            room_id=room_id,
        )

        await manager.send_to_room(room_id, message)

        # Both should receive the message
        assert ws1.send_json.call_count >= 2  # connected + message
        assert ws2.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_send_to_room_exclude_sender(
        self, manager: MemoryWebSocketManager
    ) -> None:
        """Test broadcasting to room excluding sender."""
        user1 = uuid4()
        user2 = uuid4()
        room_id = "chat-room"

        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()

        conn1 = await manager.connect(ws1, user1)
        conn2 = await manager.connect(ws2, user2)

        await manager.join_room(conn1, room_id)
        await manager.join_room(conn2, room_id)

        # Reset counts after connection messages
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()

        message = WebSocketMessage(
            type=MessageType.BROADCAST,
            payload={"text": "Hello room!"},
        )

        await manager.send_to_room(room_id, message, exclude_connection=conn1)

        # Only ws2 should receive
        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_broadcast_to_tenant(self, manager: MemoryWebSocketManager) -> None:
        """Test broadcasting to all users in tenant."""
        tenant_id = uuid4()
        user1 = uuid4()
        user2 = uuid4()

        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, user1, tenant_id)
        await manager.connect(ws2, user2, tenant_id)

        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()

        message = WebSocketMessage(
            type=MessageType.TENANT_BROADCAST,
            payload={"announcement": "System maintenance"},
        )

        await manager.broadcast_to_tenant(tenant_id, message)

        # Both should receive
        ws1.send_json.assert_called()
        ws2.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_register_message_handler(
        self, manager: MemoryWebSocketManager, mock_websocket: MagicMock
    ) -> None:
        """Test registering custom message handlers."""
        user_id = uuid4()
        handled = []

        async def custom_handler(
            message: WebSocketMessage, connection: ConnectionInfo
        ) -> None:
            handled.append(message)

        manager.register_handler(MessageType.PING, custom_handler)

        conn_id = await manager.connect(mock_websocket, user_id)

        connections = await manager.get_user_connections(user_id)
        connection = connections[0]

        message = WebSocketMessage(type=MessageType.PING, payload={})

        await manager.handle_message(message, connection)

        assert len(handled) == 1
        assert handled[0].type == MessageType.PING

    @pytest.mark.asyncio
    async def test_get_online_users(self, manager: MemoryWebSocketManager) -> None:
        """Test getting online users for tenant."""
        tenant_id = uuid4()
        user1 = uuid4()
        user2 = uuid4()

        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, user1, tenant_id)
        await manager.connect(ws2, user2, tenant_id)

        online_users = await manager.get_online_users(tenant_id)

        assert user1 in online_users
        assert user2 in online_users

    @pytest.mark.asyncio
    async def test_connection_count(self, manager: MemoryWebSocketManager) -> None:
        """Test getting connection count via online users."""
        tenant_id = uuid4()
        user1 = uuid4()
        user2 = uuid4()

        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()

        conn1 = await manager.connect(ws1, user1, tenant_id)
        await manager.connect(ws2, user2, tenant_id)

        # Use get_online_users to verify connections
        online_users = await manager.get_online_users(tenant_id)
        assert len(online_users) == 2

        await manager.disconnect(conn1)

        online_users = await manager.get_online_users(tenant_id)
        assert len(online_users) == 1

    @pytest.mark.asyncio
    async def test_send_to_connection(
        self, manager: MemoryWebSocketManager, mock_websocket: MagicMock
    ) -> None:
        """Test sending to specific connection."""
        user_id = uuid4()

        conn_id = await manager.connect(mock_websocket, user_id)

        mock_websocket.send_json.reset_mock()

        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"direct": True},
        )

        await manager.send_to_connection(conn_id, message)

        mock_websocket.send_json.assert_called_once()
        call_data = mock_websocket.send_json.call_args[0][0]
        assert call_data["type"] == "notification"
        assert call_data["payload"]["direct"] is True


class TestMessageHandlers:
    """Tests for message handler functionality."""

    @pytest_asyncio.fixture
    async def manager(self) -> MemoryWebSocketManager:
        """Create a fresh manager for each test."""
        return MemoryWebSocketManager()

    @pytest.mark.asyncio
    async def test_multiple_handlers_same_type(
        self, manager: MemoryWebSocketManager
    ) -> None:
        """Test multiple handlers for same message type."""
        results = []

        async def handler1(msg, conn):
            results.append("handler1")

        async def handler2(msg, conn):
            results.append("handler2")

        manager.register_handler(MessageType.PING, handler1)
        manager.register_handler(MessageType.PING, handler2)

        ws = MagicMock()
        ws.send_json = AsyncMock()

        await manager.connect(ws, uuid4())
        connections = list(manager._connections.values())
        connection = connections[0][1]

        message = WebSocketMessage(type=MessageType.PING, payload={})
        await manager.handle_message(message, connection)

        assert "handler1" in results
        assert "handler2" in results

    @pytest.mark.asyncio
    async def test_handler_exception_isolated(
        self, manager: MemoryWebSocketManager
    ) -> None:
        """Test that handler exceptions don't affect other handlers."""
        results = []

        async def failing_handler(msg, conn):
            raise ValueError("Handler failed")

        async def good_handler(msg, conn):
            results.append("success")

        manager.register_handler(MessageType.PING, failing_handler)
        manager.register_handler(MessageType.PING, good_handler)

        ws = MagicMock()
        ws.send_json = AsyncMock()

        await manager.connect(ws, uuid4())
        connections = list(manager._connections.values())
        connection = connections[0][1]

        message = WebSocketMessage(type=MessageType.PING, payload={})

        # Should not raise
        await manager.handle_message(message, connection)

        # Good handler should still run
        assert "success" in results
