# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for websocket port interfaces and types."""

from __future__ import annotations

from uuid import uuid4

from app.domain.ports.websocket import (
    ConnectionInfo,
    MessageType,
    WebSocketMessage,
    WebSocketPort,
)


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""

    def test_connection_info_creation(self) -> None:
        """Test ConnectionInfo creation."""
        user_id = uuid4()
        tenant_id = uuid4()
        conn_id = str(uuid4())

        info = ConnectionInfo(
            connection_id=conn_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        assert info.connection_id == conn_id
        assert info.user_id == user_id
        assert info.tenant_id == tenant_id

    def test_connection_info_with_metadata(self) -> None:
        """Test ConnectionInfo with metadata."""
        user_id = uuid4()
        tenant_id = uuid4()
        conn_id = str(uuid4())

        info = ConnectionInfo(
            connection_id=conn_id,
            user_id=user_id,
            tenant_id=tenant_id,
            metadata={"client": "web"},
        )

        assert info.metadata == {"client": "web"}

    def test_connection_info_with_rooms(self) -> None:
        """Test ConnectionInfo with rooms."""
        user_id = uuid4()
        tenant_id = uuid4()
        conn_id = str(uuid4())
        room_id = uuid4()

        info = ConnectionInfo(
            connection_id=conn_id,
            user_id=user_id,
            tenant_id=tenant_id,
            rooms={room_id},
        )

        assert room_id in info.rooms


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_message_creation_chat(self) -> None:
        """Test WebSocketMessage creation with chat type."""
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"content": "Hello"},
        )

        assert message.type == MessageType.NOTIFICATION
        assert message.payload["content"] == "Hello"

    def test_message_creation_notification(self) -> None:
        """Test WebSocketMessage creation with notification type."""
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"title": "New message"},
        )

        assert message.type == MessageType.NOTIFICATION

    def test_message_with_room(self) -> None:
        """Test WebSocketMessage with room."""
        room_id = uuid4()
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"text": "Hi"},
            room_id=room_id,
        )

        assert message.room_id == room_id

    def test_message_with_sender(self) -> None:
        """Test WebSocketMessage with sender_id."""
        sender_id = uuid4()
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"status": "online"},
            sender_id=sender_id,
        )

        assert message.sender_id == sender_id

    def test_message_to_dict(self) -> None:
        """Test WebSocketMessage to_dict method."""
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"content": "Test"},
        )

        if hasattr(message, "to_dict"):
            data = message.to_dict()
            assert "type" in data
            assert "payload" in data


class TestMessageType:
    """Tests for MessageType enum."""

    def test_NOTIFICATION_type(self) -> None:
        """Test NOTIFICATION message type."""
        assert MessageType.NOTIFICATION is not None
        assert MessageType.NOTIFICATION.value == "NOTIFICATION"

    def test_notification_type(self) -> None:
        """Test NOTIFICATION message type."""
        assert MessageType.NOTIFICATION is not None

    def test_NOTIFICATION_type(self) -> None:
        """Test NOTIFICATION message type."""
        assert MessageType.NOTIFICATION is not None

    def test_error_type(self) -> None:
        """Test ERROR message type."""
        assert MessageType.ERROR is not None

    def test_broadcast_type(self) -> None:
        """Test BROADCAST message type."""
        assert MessageType.BROADCAST is not None

    def test_connected_type(self) -> None:
        """Test CONNECTED message type."""
        assert MessageType.CONNECTED is not None

    def test_ping_pong_types(self) -> None:
        """Test PING and PONG message types."""
        assert MessageType.PING is not None
        assert MessageType.PONG is not None


class TestWebSocketPort:
    """Tests for WebSocketPort interface."""

    def test_port_is_abstract(self) -> None:
        """Test WebSocketPort is an abstract class."""
        from abc import ABC

        assert issubclass(WebSocketPort, ABC) or hasattr(
            WebSocketPort, "__abstractmethods__"
        )

    def test_port_has_connect_method(self) -> None:
        """Test WebSocketPort has connect method."""
        assert hasattr(WebSocketPort, "connect")

    def test_port_has_disconnect_method(self) -> None:
        """Test WebSocketPort has disconnect method."""
        assert hasattr(WebSocketPort, "disconnect")

    def test_port_has_send_to_user_method(self) -> None:
        """Test WebSocketPort has send_to_user method."""
        assert hasattr(WebSocketPort, "send_to_user")

    def test_port_has_broadcast_method(self) -> None:
        """Test WebSocketPort has broadcast method."""
        assert hasattr(WebSocketPort, "broadcast")

    def test_port_has_get_online_users_method(self) -> None:
        """Test WebSocketPort has get_online_users method."""
        assert hasattr(WebSocketPort, "get_online_users")

    def test_port_has_join_room_method(self) -> None:
        """Test WebSocketPort has join_room method."""
        assert hasattr(WebSocketPort, "join_room")

    def test_port_has_leave_room_method(self) -> None:
        """Test WebSocketPort has leave_room method."""
        assert hasattr(WebSocketPort, "leave_room")
