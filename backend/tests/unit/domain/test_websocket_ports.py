# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for WebSocket domain ports.

Tests for WebSocket message and connection info structures.
"""

from datetime import datetime, UTC
from uuid import uuid4

import pytest

from app.domain.ports.websocket import (
    MessageType,
    WebSocketMessage,
    ConnectionInfo,
)


class TestMessageType:
    """Tests for MessageType enum."""

    def test_system_messages(self) -> None:
        """Test system message types."""
        assert MessageType.CONNECTED.value == "connected"
        assert MessageType.DISCONNECTED.value == "disconnected"
        assert MessageType.ERROR.value == "error"
        assert MessageType.PING.value == "ping"
        assert MessageType.PONG.value == "pong"

    def test_notification_messages(self) -> None:
        """Test notification message types."""
        assert MessageType.NOTIFICATION.value == "notification"
        assert MessageType.NOTIFICATION_READ.value == "notification_read"

    def test_presence_messages(self) -> None:
        """Test presence message types."""
        assert MessageType.PRESENCE_ONLINE.value == "presence_online"
        assert MessageType.PRESENCE_OFFLINE.value == "presence_offline"
        assert MessageType.PRESENCE_AWAY.value == "presence_away"

    def test_broadcast_messages(self) -> None:
        """Test broadcast message types."""
        assert MessageType.BROADCAST.value == "broadcast"
        assert MessageType.TENANT_BROADCAST.value == "tenant_broadcast"


class TestWebSocketMessage:
    """Tests for WebSocketMessage dataclass."""

    def test_create_basic_message(self) -> None:
        """Test creating basic message."""
        message = WebSocketMessage(type=MessageType.PING)
        
        assert message.type == MessageType.PING
        assert message.payload == {}
        assert message.sender_id is None
        assert message.recipient_id is None
        assert message.room_id is None
        assert message.timestamp is not None
        assert message.message_id is None

    def test_create_NOTIFICATION(self) -> None:
        """Test creating chat message."""
        sender_id = uuid4()
        recipient_id = uuid4()
        message_id = uuid4()
        
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"content": "Hello!"},
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_id=message_id,
        )
        
        assert message.type == MessageType.NOTIFICATION
        assert message.payload["content"] == "Hello!"
        assert message.sender_id == sender_id
        assert message.recipient_id == recipient_id
        assert message.message_id == message_id

    def test_create_room_message(self) -> None:
        """Test creating room message."""
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            room_id="room_123",
        )
        
        assert message.room_id == "room_123"

    def test_create_notification_message(self) -> None:
        """Test creating notification message."""
        recipient = uuid4()
        
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={
                "title": "New message",
                "body": "You have a new message",
            },
            recipient_id=recipient,
        )
        
        assert message.type == MessageType.NOTIFICATION
        assert message.payload["title"] == "New message"


class TestWebSocketMessageToDict:
    """Tests for to_dict method."""

    def test_to_dict_basic(self) -> None:
        """Test basic to_dict conversion."""
        message = WebSocketMessage(type=MessageType.PONG)
        
        result = message.to_dict()
        
        assert result["type"] == "pong"
        assert result["payload"] == {}
        assert result["sender_id"] is None
        assert result["recipient_id"] is None
        assert result["room_id"] is None
        assert "timestamp" in result
        assert result["message_id"] is None

    def test_to_dict_with_ids(self) -> None:
        """Test to_dict with UUIDs."""
        sender = uuid4()
        recipient = uuid4()
        msg_id = uuid4()
        
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            sender_id=sender,
            recipient_id=recipient,
            message_id=msg_id,
        )
        
        result = message.to_dict()
        
        assert result["sender_id"] == str(sender)
        assert result["recipient_id"] == str(recipient)
        assert result["message_id"] == str(msg_id)

    def test_to_dict_with_payload(self) -> None:
        """Test to_dict with payload."""
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={
                "title": "Test",
                "data": {"key": "value"},
            },
        )
        
        result = message.to_dict()
        
        assert result["payload"]["title"] == "Test"
        assert result["payload"]["data"]["key"] == "value"

    def test_to_dict_with_room(self) -> None:
        """Test to_dict with room."""
        message = WebSocketMessage(
            type=MessageType.TENANT_BROADCAST,
            room_id="tenant_123",
        )
        
        result = message.to_dict()
        
        assert result["room_id"] == "tenant_123"


class TestWebSocketMessageFromDict:
    """Tests for from_dict class method."""

    def test_from_dict_basic(self) -> None:
        """Test basic from_dict creation."""
        data = {
            "type": "ping",
            "payload": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        message = WebSocketMessage.from_dict(data)
        
        assert message.type == MessageType.PING
        assert message.payload == {}

    def test_from_dict_with_ids(self) -> None:
        """Test from_dict with UUIDs."""
        sender = uuid4()
        recipient = uuid4()
        msg_id = uuid4()
        
        data = {
            "type": "notification",
            "payload": {"content": "Hello"},
            "sender_id": str(sender),
            "recipient_id": str(recipient),
            "message_id": str(msg_id),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        message = WebSocketMessage.from_dict(data)
        
        assert message.sender_id == sender
        assert message.recipient_id == recipient
        assert message.message_id == msg_id

    def test_from_dict_with_room(self) -> None:
        """Test from_dict with room."""
        data = {
            "type": "broadcast",
            "room_id": "room_456",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        message = WebSocketMessage.from_dict(data)
        
        assert message.room_id == "room_456"

    def test_from_dict_null_ids(self) -> None:
        """Test from_dict handles null IDs."""
        data = {
            "type": "pong",
            "sender_id": None,
            "recipient_id": None,
            "message_id": None,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        message = WebSocketMessage.from_dict(data)
        
        assert message.sender_id is None
        assert message.recipient_id is None
        assert message.message_id is None

    def test_from_dict_no_timestamp(self) -> None:
        """Test from_dict without timestamp."""
        data = {
            "type": "ping",
        }
        
        message = WebSocketMessage.from_dict(data)
        
        assert message.timestamp is not None

    def test_roundtrip_conversion(self) -> None:
        """Test converting to dict and back."""
        original = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"content": "Hello world"},
            sender_id=uuid4(),
            recipient_id=uuid4(),
            room_id="room_123",
            message_id=uuid4(),
        )
        
        data = original.to_dict()
        restored = WebSocketMessage.from_dict(data)
        
        assert restored.type == original.type
        assert restored.payload == original.payload
        assert restored.sender_id == original.sender_id
        assert restored.recipient_id == original.recipient_id
        assert restored.room_id == original.room_id
        assert restored.message_id == original.message_id


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""

    def test_create_basic_connection_info(self) -> None:
        """Test creating basic connection info."""
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
        assert info.connected_at is not None

    def test_default_values(self) -> None:
        """Test default values."""
        info = ConnectionInfo(
            user_id=uuid4(),
            tenant_id=None,
            connection_id="conn_456",
        )
        
        assert info.tenant_id is None
        assert info.rooms == set()
        assert info.metadata == {}

    def test_with_rooms(self) -> None:
        """Test connection with rooms."""
        info = ConnectionInfo(
            user_id=uuid4(),
            tenant_id=uuid4(),
            connection_id="conn_789",
            rooms={"room1", "room2", "room3"},
        )
        
        assert len(info.rooms) == 3
        assert "room1" in info.rooms
        assert "room2" in info.rooms

    def test_with_metadata(self) -> None:
        """Test connection with metadata."""
        info = ConnectionInfo(
            user_id=uuid4(),
            tenant_id=uuid4(),
            connection_id="conn_abc",
            metadata={
                "user_agent": "Mozilla/5.0",
                "ip_address": "192.168.1.1",
            },
        )
        
        assert info.metadata["user_agent"] == "Mozilla/5.0"
        assert info.metadata["ip_address"] == "192.168.1.1"

    def test_connected_at_timestamp(self) -> None:
        """Test connected_at timestamp is set."""
        before = datetime.now(UTC)
        info = ConnectionInfo(
            user_id=uuid4(),
            tenant_id=uuid4(),
            connection_id="conn_def",
        )
        after = datetime.now(UTC)
        
        assert before <= info.connected_at <= after

    def test_rooms_are_mutable(self) -> None:
        """Test rooms set can be modified."""
        info = ConnectionInfo(
            user_id=uuid4(),
            tenant_id=uuid4(),
            connection_id="conn_ghi",
        )
        
        info.rooms.add("new_room")
        
        assert "new_room" in info.rooms

    def test_without_tenant(self) -> None:
        """Test connection without tenant."""
        info = ConnectionInfo(
            user_id=uuid4(),
            tenant_id=None,
            connection_id="conn_jkl",
        )
        
        assert info.tenant_id is None

