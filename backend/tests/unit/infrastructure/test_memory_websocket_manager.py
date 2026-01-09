# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for MemoryWebSocketManager.

Tests for the in-memory WebSocket connection manager.
"""

from datetime import datetime, timezone, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMemoryWebSocketManagerInit:
    """Tests for MemoryWebSocketManager initialization."""

    def test_init_creates_empty_collections(self) -> None:
        """Test that init creates empty collections."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()

        assert len(manager._connections) == 0
        assert len(manager._user_connections) == 0
        assert len(manager._tenant_connections) == 0
        assert len(manager._rooms) == 0
        assert len(manager._handlers) == 0

    def test_backend_name(self) -> None:
        """Test backend_name property."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        assert manager.backend_name == "memory"


class TestMemoryWebSocketManagerConnect:
    """Tests for connect method."""

    @pytest.mark.asyncio
    async def test_connect_returns_connection_id(self) -> None:
        """Test that connect returns a connection ID."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        mock_websocket = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()

        connection_id = await manager.connect(
            websocket=mock_websocket,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert connection_id is not None
        assert len(connection_id) > 0

    @pytest.mark.asyncio
    async def test_connect_stores_connection(self) -> None:
        """Test that connect stores the connection."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        mock_websocket = AsyncMock()
        user_id = uuid4()

        connection_id = await manager.connect(
            websocket=mock_websocket,
            user_id=user_id,
        )

        assert connection_id in manager._connections
        ws, info = manager._connections[connection_id]
        assert info.user_id == user_id

    @pytest.mark.asyncio
    async def test_connect_indexes_by_user(self) -> None:
        """Test that connect indexes connection by user."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        mock_websocket = AsyncMock()
        user_id = uuid4()

        connection_id = await manager.connect(
            websocket=mock_websocket,
            user_id=user_id,
        )

        assert user_id in manager._user_connections
        assert connection_id in manager._user_connections[user_id]

    @pytest.mark.asyncio
    async def test_connect_indexes_by_tenant(self) -> None:
        """Test that connect indexes connection by tenant."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        mock_websocket = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()

        connection_id = await manager.connect(
            websocket=mock_websocket,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert tenant_id in manager._tenant_connections
        assert connection_id in manager._tenant_connections[tenant_id]

    @pytest.mark.asyncio
    async def test_connect_sends_confirmation(self) -> None:
        """Test that connect sends confirmation message."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        mock_websocket = AsyncMock()
        user_id = uuid4()

        connection_id = await manager.connect(
            websocket=mock_websocket,
            user_id=user_id,
        )

        # Check that send_json was called with connection confirmation
        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connected"

    @pytest.mark.asyncio
    async def test_connect_multiple_users(self) -> None:
        """Test connecting multiple different users."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user1 = uuid4()
        user2 = uuid4()

        conn1 = await manager.connect(
            websocket=AsyncMock(),
            user_id=user1,
        )
        conn2 = await manager.connect(
            websocket=AsyncMock(),
            user_id=user2,
        )

        assert conn1 != conn2
        assert len(manager._connections) == 2

    @pytest.mark.asyncio
    async def test_connect_same_user_multiple_times(self) -> None:
        """Test same user can have multiple connections."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user_id = uuid4()

        conn1 = await manager.connect(
            websocket=AsyncMock(),
            user_id=user_id,
        )
        conn2 = await manager.connect(
            websocket=AsyncMock(),
            user_id=user_id,
        )

        assert conn1 != conn2
        assert len(manager._user_connections[user_id]) == 2


class TestMemoryWebSocketManagerDisconnect:
    """Tests for disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self) -> None:
        """Test that disconnect removes the connection."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        mock_websocket = AsyncMock()
        user_id = uuid4()

        connection_id = await manager.connect(
            websocket=mock_websocket,
            user_id=user_id,
        )
        await manager.disconnect(connection_id)

        assert connection_id not in manager._connections

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_user_index(self) -> None:
        """Test that disconnect removes from user index."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user_id = uuid4()

        connection_id = await manager.connect(
            websocket=AsyncMock(),
            user_id=user_id,
        )
        await manager.disconnect(connection_id)

        # User should have no connections
        if user_id in manager._user_connections:
            assert connection_id not in manager._user_connections[user_id]

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self) -> None:
        """Test disconnecting non-existent connection doesn't error."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()

        # Should not raise
        await manager.disconnect("nonexistent-id")


class TestMemoryWebSocketManagerRooms:
    """Tests for room functionality."""

    @pytest.mark.asyncio
    async def test_join_room(self) -> None:
        """Test joining a room."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user_id = uuid4()

        connection_id = await manager.connect(
            websocket=AsyncMock(),
            user_id=user_id,
        )
        await manager.join_room(connection_id, "test-room")

        assert "test-room" in manager._rooms
        assert connection_id in manager._rooms["test-room"]

    @pytest.mark.asyncio
    async def test_leave_room(self) -> None:
        """Test leaving a room."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user_id = uuid4()

        connection_id = await manager.connect(
            websocket=AsyncMock(),
            user_id=user_id,
        )
        await manager.join_room(connection_id, "test-room")
        await manager.leave_room(connection_id, "test-room")

        if "test-room" in manager._rooms:
            assert connection_id not in manager._rooms["test-room"]

    @pytest.mark.asyncio
    async def test_get_room_connections(self) -> None:
        """Test getting connections in a room via _rooms dict."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user1 = uuid4()
        user2 = uuid4()

        conn1 = await manager.connect(
            websocket=AsyncMock(),
            user_id=user1,
        )
        conn2 = await manager.connect(
            websocket=AsyncMock(),
            user_id=user2,
        )

        await manager.join_room(conn1, "room-1")
        await manager.join_room(conn2, "room-1")

        # Check via internal _rooms dict
        assert len(manager._rooms["room-1"]) == 2


class TestMemoryWebSocketManagerMessageHandlers:
    """Tests for message handler registration."""

    def test_register_handler(self) -> None:
        """Test registering a message handler."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager
        from app.domain.ports.websocket import MessageType

        manager = MemoryWebSocketManager()

        async def test_handler(msg, conn):
            pass

        manager.register_handler(MessageType.PING, test_handler)

        assert MessageType.PING in manager._handlers
        assert test_handler in manager._handlers[MessageType.PING]

    def test_register_multiple_handlers_same_type(self) -> None:
        """Test registering multiple handlers for same message type."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager
        from app.domain.ports.websocket import MessageType

        manager = MemoryWebSocketManager()

        async def handler1(msg, conn):
            pass

        async def handler2(msg, conn):
            pass

        manager.register_handler(MessageType.CHAT_MESSAGE, handler1)
        manager.register_handler(MessageType.CHAT_MESSAGE, handler2)

        assert len(manager._handlers[MessageType.CHAT_MESSAGE]) == 2


class TestMemoryWebSocketManagerSendMethods:
    """Tests for send methods."""

    @pytest.mark.asyncio
    async def test_send_to_connection(self) -> None:
        """Test sending message to specific connection."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager
        from app.domain.ports.websocket import MessageType, WebSocketMessage

        manager = MemoryWebSocketManager()
        mock_websocket = AsyncMock()
        user_id = uuid4()

        connection_id = await manager.connect(
            websocket=mock_websocket,
            user_id=user_id,
        )

        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"text": "Hello"},
        )
        await manager.send_to_connection(connection_id, message)

        # Check send_json was called
        assert mock_websocket.send_json.call_count >= 2  # connect + send

    @pytest.mark.asyncio
    async def test_send_to_user(self) -> None:
        """Test sending message to all user connections."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager
        from app.domain.ports.websocket import MessageType, WebSocketMessage

        manager = MemoryWebSocketManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        user_id = uuid4()

        await manager.connect(websocket=mock_ws1, user_id=user_id)
        await manager.connect(websocket=mock_ws2, user_id=user_id)

        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"text": "Broadcast to user"},
        )
        await manager.send_to_user(user_id, message)

        # Both connections should receive the message
        assert mock_ws1.send_json.call_count >= 2
        assert mock_ws2.send_json.call_count >= 2


class TestMemoryWebSocketManagerGetters:
    """Tests for getter methods."""

    @pytest.mark.asyncio
    async def test_get_user_connections(self) -> None:
        """Test getting all connections for a user."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user_id = uuid4()

        await manager.connect(websocket=AsyncMock(), user_id=user_id)
        await manager.connect(websocket=AsyncMock(), user_id=user_id)

        connections = await manager.get_user_connections(user_id)
        assert len(connections) == 2

    @pytest.mark.asyncio
    async def test_get_user_connections_empty(self) -> None:
        """Test getting connections for user with none."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user_id = uuid4()

        connections = await manager.get_user_connections(user_id)
        assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_get_online_users(self) -> None:
        """Test getting list of online users."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user1 = uuid4()
        user2 = uuid4()
        tenant_id = uuid4()

        await manager.connect(
            websocket=AsyncMock(),
            user_id=user1,
            tenant_id=tenant_id,
        )
        await manager.connect(
            websocket=AsyncMock(),
            user_id=user2,
            tenant_id=tenant_id,
        )

        online_users = await manager.get_online_users(tenant_id)
        assert user1 in online_users
        assert user2 in online_users


class TestMemoryWebSocketManagerEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_connect_without_tenant(self) -> None:
        """Test connecting without tenant context."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user_id = uuid4()

        connection_id = await manager.connect(
            websocket=AsyncMock(),
            user_id=user_id,
            tenant_id=None,
        )

        assert connection_id is not None
        ws, info = manager._connections[connection_id]
        assert info.tenant_id is None

    @pytest.mark.asyncio
    async def test_connect_with_metadata(self) -> None:
        """Test connecting with metadata."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

        manager = MemoryWebSocketManager()
        user_id = uuid4()
        metadata = {"device": "mobile", "version": "1.0"}

        connection_id = await manager.connect(
            websocket=AsyncMock(),
            user_id=user_id,
            metadata=metadata,
        )

        ws, info = manager._connections[connection_id]
        assert info.metadata["device"] == "mobile"

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_user(self) -> None:
        """Test sending to non-existent user doesn't error."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager
        from app.domain.ports.websocket import MessageType, WebSocketMessage

        manager = MemoryWebSocketManager()
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"text": "Hello"},
        )

        # Should not raise
        await manager.send_to_user(uuid4(), message)
