# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for WebSocket infrastructure module init.

Tests for WebSocket module initialization and lazy loading.
"""




class TestWebSocketModule:
    """Tests for WebSocket module initialization."""

    def test_exports_connection_info(self) -> None:
        """Test ConnectionInfo is exported."""
        from app.infrastructure.websocket import ConnectionInfo

        assert ConnectionInfo is not None

    def test_exports_message_handler(self) -> None:
        """Test MessageHandler is exported."""
        from app.infrastructure.websocket import MessageHandler

        assert MessageHandler is not None

    def test_exports_message_type(self) -> None:
        """Test MessageType is exported."""
        from app.infrastructure.websocket import MessageType

        assert MessageType is not None

    def test_exports_websocket_message(self) -> None:
        """Test WebSocketMessage is exported."""
        from app.infrastructure.websocket import WebSocketMessage

        assert WebSocketMessage is not None

    def test_exports_websocket_port(self) -> None:
        """Test WebSocketPort is exported."""
        from app.infrastructure.websocket import WebSocketPort

        assert WebSocketPort is not None

    def test_exports_memory_manager(self) -> None:
        """Test MemoryWebSocketManager is exported."""
        from app.infrastructure.websocket import MemoryWebSocketManager

        assert MemoryWebSocketManager is not None


class TestMessageTypeEnum:
    """Tests for MessageType enum values."""

    def test_connected_type(self) -> None:
        """Test CONNECTED message type."""
        from app.infrastructure.websocket import MessageType

        assert MessageType.CONNECTED.value == "connected"

    def test_disconnected_type(self) -> None:
        """Test DISCONNECTED message type."""
        from app.infrastructure.websocket import MessageType

        assert MessageType.DISCONNECTED.value == "disconnected"

    def test_notification_type(self) -> None:
        """Test NOTIFICATION message type."""
        from app.infrastructure.websocket import MessageType

        assert MessageType.NOTIFICATION.value == "notification"

    def test_broadcast_type(self) -> None:
        """Test BROADCAST message type."""
        from app.infrastructure.websocket import MessageType

        assert MessageType.BROADCAST.value == "broadcast"


class TestWebSocketMessage:
    """Tests for WebSocketMessage data class."""

    def test_create_message(self) -> None:
        """Test creating a WebSocket message."""
        from app.infrastructure.websocket import MessageType, WebSocketMessage

        message = WebSocketMessage(
            type=MessageType.NOTIFICATION, payload={"title": "Test", "body": "Message"}
        )

        assert message.type == MessageType.NOTIFICATION
        assert message.payload["title"] == "Test"

    def test_message_to_dict(self) -> None:
        """Test converting message to dict."""
        from app.infrastructure.websocket import MessageType, WebSocketMessage

        message = WebSocketMessage(
            type=MessageType.NOTIFICATION, payload={"content": "Hello"}
        )

        data = message.to_dict()

        assert "type" in data
        assert "payload" in data
        assert data["payload"]["content"] == "Hello"
