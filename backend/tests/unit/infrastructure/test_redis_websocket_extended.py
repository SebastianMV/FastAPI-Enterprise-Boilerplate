# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for Redis WebSocket manager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestRedisWebSocketManagerInit:
    """Tests for RedisWebSocketManager initialization."""

    def test_manager_creation_without_redis_raises(self) -> None:
        """Test that creating manager without redis package raises ImportError."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", False):
            # Need to reimport after patching
            import importlib
            from app.infrastructure.websocket import redis_manager
            
            # Since HAS_REDIS is checked at init time
            if not redis_manager.HAS_REDIS:
                with pytest.raises(ImportError):
                    redis_manager.RedisWebSocketManager()

    def test_manager_backend_name(self) -> None:
        """Test manager backend name property."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._instance_id = "test"
                
                assert manager.backend_name == "redis"

    def test_manager_key_prefixes(self) -> None:
        """Test manager has correct key prefixes."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager

        assert RedisWebSocketManager.PREFIX == "ws:"
        assert RedisWebSocketManager.CONNECTIONS_KEY == "ws:connections"
        assert RedisWebSocketManager.ONLINE_KEY == "ws:online"


class TestRedisWebSocketManagerStart:
    """Tests for start/stop methods."""

    @pytest.mark.asyncio
    async def test_start_creates_redis_connection(self) -> None:
        """Test that start creates Redis connection."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub.psubscribe = AsyncMock()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch(
                "app.infrastructure.websocket.redis_manager.redis.from_url",
                return_value=mock_redis,
            ):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager

                manager = RedisWebSocketManager(redis_url="redis://localhost")
                
                # Start should create connection and test it
                await manager.start()

                mock_redis.ping.assert_called_once()
                assert manager._running is True

                # Cleanup
                manager._running = False
                if manager._subscriber_task:
                    manager._subscriber_task.cancel()
                    try:
                        await manager._subscriber_task
                    except:
                        pass

    @pytest.mark.asyncio
    async def test_stop_closes_connections(self) -> None:
        """Test that stop closes Redis connections."""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub.close = AsyncMock()

        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager

                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._redis = mock_redis
                manager._pubsub = mock_pubsub
                manager._running = True
                manager._subscriber_task = None
                manager._instance_id = "test"

                await manager.stop()

                assert manager._running is False
                mock_pubsub.close.assert_called_once()
                mock_redis.close.assert_called_once()


class TestRedisManagerHelpers:
    """Tests for helper methods and properties."""

    def test_channel_templates(self) -> None:
        """Test channel template formats."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager

        assert "{user_id}" in RedisWebSocketManager.USER_CHANNEL
        assert "{tenant_id}" in RedisWebSocketManager.TENANT_CHANNEL
        assert "{room_id}" in RedisWebSocketManager.ROOM_CHANNEL


class TestRedisConnectionInfo:
    """Tests for connection info serialization."""

    def test_connection_info_to_dict(self) -> None:
        """Test ConnectionInfo can be serialized."""
        from app.domain.ports.websocket import ConnectionInfo

        user_id = uuid4()
        tenant_id = uuid4()

        info = ConnectionInfo(
            connection_id="conn-123",
            user_id=user_id,
            tenant_id=tenant_id,
            metadata={"key": "value"},
        )

        # Should be serializable
        import json
        data = {
            "connection_id": info.connection_id,
            "user_id": str(info.user_id),
            "tenant_id": str(info.tenant_id) if info.tenant_id else None,
            "metadata": info.metadata,
        }
        serialized = json.dumps(data)
        assert serialized is not None

    def test_connection_info_with_rooms(self) -> None:
        """Test ConnectionInfo with rooms."""
        from app.domain.ports.websocket import ConnectionInfo

        info = ConnectionInfo(
            connection_id="conn-123",
            user_id=uuid4(),
            tenant_id=uuid4(),
            rooms={"room-1", "room-2", "room-3"},
        )

        assert len(info.rooms) == 3
        assert "room-1" in info.rooms


class TestWebSocketMessageSerialization:
    """Tests for WebSocketMessage serialization for Redis."""

    def test_message_to_dict_for_redis(self) -> None:
        """Test message can be serialized to JSON for Redis."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        import json

        user_id = uuid4()
        message = WebSocketMessage(
            type=MessageType.CHAT_MESSAGE,
            payload={"content": "Hello"},
            sender_id=user_id,
            room_id="room-1",
        )

        data = message.to_dict()
        serialized = json.dumps(data)
        
        deserialized = json.loads(serialized)
        assert deserialized["type"] == "chat_message"
        assert deserialized["payload"]["content"] == "Hello"

    def test_message_from_dict_for_redis(self) -> None:
        """Test message can be deserialized from Redis JSON."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        import json

        data = {
            "type": "notification",
            "payload": {"title": "New message"},
            "message_id": str(uuid4()),
        }
        
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        
        message = WebSocketMessage.from_dict(deserialized)
        assert message.type == MessageType.NOTIFICATION
        assert message.payload["title"] == "New message"


class TestMessageHandlerRegistration:
    """Tests for message handler registration."""

    def test_register_handler(self) -> None:
        """Test registering a message handler."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                from app.domain.ports.websocket import MessageType

                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._handlers = {}

                async def test_handler(message, connection):
                    pass

                manager.register_handler(MessageType.PING, test_handler)

                assert MessageType.PING in manager._handlers
                assert test_handler in manager._handlers[MessageType.PING]

    def test_register_multiple_handlers(self) -> None:
        """Test registering multiple handlers for same type."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                from app.domain.ports.websocket import MessageType

                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._handlers = {}

                async def handler1(message, connection):
                    pass

                async def handler2(message, connection):
                    pass

                manager.register_handler(MessageType.PING, handler1)
                manager.register_handler(MessageType.PING, handler2)

                assert len(manager._handlers[MessageType.PING]) == 2
