# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for Redis WebSocket manager."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC
import json


class TestRedisWebSocketManagerInit:
    """Tests for RedisWebSocketManager initialization."""
    
    def test_init_without_redis_raises_import_error(self):
        """Test that init without redis installed raises ImportError."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", False):
            # Re-import to get the class with patched HAS_REDIS
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            
            with pytest.raises(ImportError) as exc_info:
                RedisWebSocketManager(redis_url="redis://localhost:6379")
            
            assert "redis package is required" in str(exc_info.value)
    
    @patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True)
    def test_init_with_default_values(self):
        """Test initialization with default values."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            manager = RedisWebSocketManager(redis_url="redis://localhost:6379")
            
            assert manager._redis_url == "redis://localhost:6379"
            assert manager._instance_id is not None
            assert len(manager._instance_id) == 8
            assert manager._redis is None
            assert manager._pubsub is None
            assert manager._local_connections == {}
            assert manager._handlers == {}
            assert manager._running is False
    
    @patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True)
    def test_init_with_custom_instance_id(self):
        """Test initialization with custom instance ID."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        manager = RedisWebSocketManager(
            redis_url="redis://localhost:6379",
            instance_id="custom-id"
        )
        
        assert manager._instance_id == "custom-id"
    
    @patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True)
    def test_backend_name(self):
        """Test backend_name property returns 'redis'."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        manager = RedisWebSocketManager(redis_url="redis://localhost:6379")
        assert manager.backend_name == "redis"


class TestRedisWebSocketManagerStartStop:
    """Tests for start/stop methods."""
    
    @pytest.fixture
    def manager(self):
        """Create a manager instance with mocked Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            return RedisWebSocketManager(redis_url="redis://localhost:6379")
    
    @pytest.mark.asyncio
    async def test_start_creates_redis_connection(self, manager):
        """Test that start creates Redis connection."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_pubsub.psubscribe = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        with patch("app.infrastructure.websocket.redis_manager.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = mock_redis
            
            # Don't await since it starts a background task
            manager._redis = mock_redis
            manager._pubsub = mock_pubsub
            manager._running = True
            
            assert manager._running is True
            assert manager._redis is not None
    
    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, manager):
        """Test that calling start twice doesn't create duplicate connections."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        manager._running = True  # Simulate already started
        
        with patch("app.infrastructure.websocket.redis_manager.redis") as mock_redis_module:
            mock_redis_module.from_url.return_value = mock_redis
            
            await manager.start()
            
            # Should not create new connection
            mock_redis_module.from_url.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_stop_closes_connections(self, manager):
        """Test that stop closes Redis connections."""
        mock_redis = AsyncMock()
        mock_pubsub = AsyncMock()
        
        manager._redis = mock_redis
        manager._pubsub = mock_pubsub
        manager._running = True
        manager._subscriber_task = None  # No active task
        
        await manager.stop()
        
        assert manager._running is False
        mock_pubsub.close.assert_called_once()
        mock_redis.close.assert_called_once()


class TestRedisWebSocketManagerConnect:
    """Tests for connect method."""
    
    @pytest.fixture
    def manager(self):
        """Create a manager instance with mocked Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(redis_url="redis://localhost:6379")
            mgr._redis = AsyncMock()
            mgr._running = True
            return mgr
    
    @pytest.mark.asyncio
    async def test_connect_stores_connection_locally(self, manager):
        """Test that connect stores connection in local dict."""
        websocket = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()
        
        conn_id = await manager.connect(websocket, user_id, tenant_id)
        
        assert conn_id in manager._local_connections
        ws, info = manager._local_connections[conn_id]
        assert ws == websocket
        assert info.user_id == user_id
        assert info.tenant_id == tenant_id
    
    @pytest.mark.asyncio
    async def test_connect_stores_in_redis(self, manager):
        """Test that connect stores connection data in Redis."""
        websocket = AsyncMock()
        user_id = uuid4()
        tenant_id = uuid4()
        
        await manager.connect(websocket, user_id, tenant_id)
        
        manager._redis.hset.assert_called()
        manager._redis.sadd.assert_called()
    
    @pytest.mark.asyncio
    async def test_connect_sends_confirmation(self, manager):
        """Test that connect sends connection confirmation to client."""
        websocket = AsyncMock()
        user_id = uuid4()
        
        await manager.connect(websocket, user_id)
        
        websocket.send_json.assert_called()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connected"
    
    @pytest.mark.asyncio
    async def test_connect_with_metadata(self, manager):
        """Test connect with custom metadata."""
        websocket = AsyncMock()
        user_id = uuid4()
        metadata = {"device": "mobile", "app_version": "1.0"}
        
        conn_id = await manager.connect(websocket, user_id, metadata=metadata)
        
        _, info = manager._local_connections[conn_id]
        assert info.metadata == metadata


class TestRedisWebSocketManagerDisconnect:
    """Tests for disconnect method."""
    
    @pytest.fixture
    def manager(self):
        """Create a manager instance with mocked Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(redis_url="redis://localhost:6379")
            mgr._redis = AsyncMock()
            mgr._redis.scard = AsyncMock(return_value=0)
            mgr._running = True
            return mgr
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_local_connection(self, manager):
        """Test that disconnect removes connection from local dict."""
        websocket = AsyncMock()
        user_id = uuid4()
        
        conn_id = await manager.connect(websocket, user_id)
        assert conn_id in manager._local_connections
        
        await manager.disconnect(conn_id)
        assert conn_id not in manager._local_connections
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_from_redis(self, manager):
        """Test that disconnect removes connection data from Redis."""
        websocket = AsyncMock()
        user_id = uuid4()
        
        conn_id = await manager.connect(websocket, user_id)
        await manager.disconnect(conn_id)
        
        manager._redis.hdel.assert_called()
        manager._redis.srem.assert_called()
    
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self, manager):
        """Test disconnect with non-existent connection ID is safe."""
        # Should not raise
        await manager.disconnect("nonexistent-connection-id")


class TestRedisWebSocketManagerMessaging:
    """Tests for messaging methods."""
    
    @pytest.fixture
    def manager(self):
        """Create a manager instance with mocked Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(redis_url="redis://localhost:6379")
            mgr._redis = AsyncMock()
            mgr._running = True
            return mgr
    
    @pytest.mark.asyncio
    async def test_publish_message(self, manager):
        """Test publishing message to Redis channel."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"content": "Hello"}
        )
        
        await manager._publish(
            channel="ws:test",
            message=message,
            target_type="broadcast"
        )
        
        manager._redis.publish.assert_called_once()
        call_args = manager._redis.publish.call_args
        assert "ws:test" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_publish_without_redis_does_nothing(self, manager):
        """Test that publish without Redis connection does nothing."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        manager._redis = None
        
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"content": "Hello"}
        )
        
        # Should not raise
        await manager._publish(
            channel="ws:test",
            message=message,
            target_type="broadcast"
        )


class TestRedisWebSocketManagerConstants:
    """Tests for Redis key constants."""
    
    @patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True)
    def test_redis_key_prefixes(self):
        """Test Redis key prefix constants."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        assert RedisWebSocketManager.PREFIX == "ws:"
        assert RedisWebSocketManager.CONNECTIONS_KEY == "ws:connections"
        assert "ws:user:" in RedisWebSocketManager.USER_CONNS_KEY
        assert "ws:tenant:" in RedisWebSocketManager.TENANT_CONNS_KEY
        assert "ws:room:" in RedisWebSocketManager.ROOM_KEY
        assert RedisWebSocketManager.ONLINE_KEY == "ws:online"
    
    @patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True)
    def test_pubsub_channel_patterns(self):
        """Test Pub/Sub channel pattern constants."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        assert RedisWebSocketManager.BROADCAST_CHANNEL == "ws:broadcast"
        assert "{user_id}" in RedisWebSocketManager.USER_CHANNEL
        assert "{tenant_id}" in RedisWebSocketManager.TENANT_CHANNEL
        assert "{room_id}" in RedisWebSocketManager.ROOM_CHANNEL


class TestRedisWebSocketManagerPubSubHandler:
    """Tests for Pub/Sub message handling."""
    
    @pytest.fixture
    def manager(self):
        """Create a manager instance with mocked Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(
                redis_url="redis://localhost:6379",
                instance_id="test-instance"
            )
            mgr._redis = AsyncMock()
            mgr._running = True
            return mgr
    
    @pytest.mark.asyncio
    async def test_handle_pubsub_skips_own_messages(self, manager):
        """Test that handler skips messages from same instance."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        # Message from same instance
        data = json.dumps({
            "_instance": "test-instance",  # Same as manager's instance
            "message": WebSocketMessage(
                type=MessageType.NOTIFICATION,
                payload={"content": "Hello"}
            ).to_dict(),
            "target_type": "broadcast"
        })
        
        # Should not process (no local send)
        with patch.object(manager, "_local_broadcast", new_callable=AsyncMock) as mock_broadcast:
            await manager._handle_pubsub_message("ws:broadcast", data)
            mock_broadcast.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_pubsub_processes_other_instance_messages(self, manager):
        """Test that handler processes messages from other instances."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        # Message from different instance
        data = json.dumps({
            "_instance": "other-instance",
            "message": WebSocketMessage(
                type=MessageType.NOTIFICATION,
                payload={"content": "Hello"}
            ).to_dict(),
            "target_type": "broadcast"
        })
        
        with patch.object(manager, "_local_broadcast", new_callable=AsyncMock) as mock_broadcast:
            await manager._handle_pubsub_message("ws:broadcast", data)
            mock_broadcast.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_pubsub_routes_user_messages(self, manager):
        """Test that handler routes user-targeted messages."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        user_id = str(uuid4())
        data = json.dumps({
            "_instance": "other-instance",
            "message": WebSocketMessage(
                type=MessageType.NOTIFICATION,
                payload={"title": "Test"}
            ).to_dict(),
            "target_type": "user",
            "target_id": user_id
        })
        
        with patch.object(manager, "_local_send_to_user", new_callable=AsyncMock) as mock_send:
            await manager._handle_pubsub_message("ws:user:test", data)
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_pubsub_routes_tenant_messages(self, manager):
        """Test that handler routes tenant-targeted messages."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        tenant_id = str(uuid4())
        data = json.dumps({
            "_instance": "other-instance",
            "message": WebSocketMessage(
                type=MessageType.NOTIFICATION,
                payload={"content": "Hello"}
            ).to_dict(),
            "target_type": "tenant",
            "target_id": tenant_id
        })
        
        with patch.object(manager, "_local_broadcast_to_tenant", new_callable=AsyncMock) as mock_broadcast:
            await manager._handle_pubsub_message("ws:tenant:test", data)
            mock_broadcast.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_pubsub_routes_room_messages(self, manager):
        """Test that handler routes room-targeted messages."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        data = json.dumps({
            "_instance": "other-instance",
            "message": WebSocketMessage(
                type=MessageType.NOTIFICATION,
                payload={"content": "Hello room"}
            ).to_dict(),
            "target_type": "room",
            "target_id": "general"
        })
        
        with patch.object(manager, "_local_send_to_room", new_callable=AsyncMock) as mock_send:
            await manager._handle_pubsub_message("ws:room:general", data)
            mock_send.assert_called_once()


class TestRedisWebSocketManagerSendToUser:
    """Tests for send_to_user method."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance with mocked Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(redis_url="redis://localhost:6379")
            mgr._redis = AsyncMock()
            mgr._running = True
            return mgr

    @pytest.mark.asyncio
    async def test_send_to_user_sends_locally_and_publishes(self, manager):
        """Test send_to_user sends to local connections and publishes."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        websocket = AsyncMock()
        user_id = uuid4()
        
        await manager.connect(websocket, user_id)
        
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"title": "Test"}
        )
        
        count = await manager.send_to_user(user_id, message)
        
        assert count >= 1
        manager._redis.publish.assert_called()


class TestRedisWebSocketManagerSendToConnection:
    """Tests for send_to_connection method."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(redis_url="redis://localhost:6379")
            mgr._redis = AsyncMock()
            mgr._running = True
            return mgr

    @pytest.mark.asyncio
    async def test_send_to_connection_local_success(self, manager):
        """Test send_to_connection succeeds for local connection."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        websocket = AsyncMock()
        user_id = uuid4()
        
        conn_id = await manager.connect(websocket, user_id)
        
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"title": "Test"}
        )
        
        result = await manager.send_to_connection(conn_id, message)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_send_to_connection_nonexistent_returns_false(self, manager):
        """Test send_to_connection returns False for unknown connection."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            payload={"title": "Test"}
        )
        
        result = await manager.send_to_connection("unknown-conn", message)
        
        assert result is False


class TestRedisWebSocketManagerBroadcast:
    """Tests for broadcast method."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(redis_url="redis://localhost:6379")
            mgr._redis = AsyncMock()
            mgr._running = True
            return mgr

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_local(self, manager):
        """Test broadcast sends to all local connections."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        ws1, ws2 = AsyncMock(), AsyncMock()
        user1, user2 = uuid4(), uuid4()
        
        await manager.connect(ws1, user1)
        await manager.connect(ws2, user2)
        
        message = WebSocketMessage(
            type=MessageType.BROADCAST,
            payload={"announcement": "Test"}
        )
        
        count = await manager.broadcast(message)
        
        assert count == 2
        manager._redis.publish.assert_called()

    @pytest.mark.asyncio
    async def test_broadcast_excludes_user(self, manager):
        """Test broadcast excludes specified user."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        ws1, ws2 = AsyncMock(), AsyncMock()
        user1, user2 = uuid4(), uuid4()
        
        await manager.connect(ws1, user1)
        await manager.connect(ws2, user2)
        
        message = WebSocketMessage(
            type=MessageType.BROADCAST,
            payload={"announcement": "Test"}
        )
        
        count = await manager.broadcast(message, exclude_user=user1)
        
        assert count == 1  # Only user2 receives


class TestRedisWebSocketManagerBroadcastToTenant:
    """Tests for broadcast_to_tenant method."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(redis_url="redis://localhost:6379")
            mgr._redis = AsyncMock()
            mgr._running = True
            return mgr

    @pytest.mark.asyncio
    async def test_broadcast_to_tenant_filters_by_tenant(self, manager):
        """Test broadcast_to_tenant only sends to tenant connections."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        tenant_id = uuid4()
        other_tenant = uuid4()
        
        ws1, ws2 = AsyncMock(), AsyncMock()
        user1, user2 = uuid4(), uuid4()
        
        await manager.connect(ws1, user1, tenant_id)
        await manager.connect(ws2, user2, other_tenant)
        
        message = WebSocketMessage(
            type=MessageType.BROADCAST,
            payload={"message": "Tenant message"}
        )
        
        count = await manager.broadcast_to_tenant(tenant_id, message)
        
        assert count == 1  # Only user1 in tenant


class TestRedisWebSocketManagerRooms:
    """Tests for room management methods."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(redis_url="redis://localhost:6379")
            mgr._redis = AsyncMock()
            mgr._running = True
            return mgr

    @pytest.mark.asyncio
    async def test_join_room_adds_to_rooms(self, manager):
        """Test join_room adds connection to room set."""
        websocket = AsyncMock()
        user_id = uuid4()
        
        conn_id = await manager.connect(websocket, user_id)
        
        await manager.join_room(conn_id, "general")
        
        _, info = manager._local_connections[conn_id]
        assert "general" in info.rooms
        manager._redis.sadd.assert_called()

    @pytest.mark.asyncio
    async def test_join_room_nonexistent_connection(self, manager):
        """Test join_room with nonexistent connection is safe."""
        await manager.join_room("nonexistent", "general")
        # Should not raise

    @pytest.mark.asyncio
    async def test_leave_room_removes_from_rooms(self, manager):
        """Test leave_room removes connection from room set."""
        websocket = AsyncMock()
        user_id = uuid4()
        
        conn_id = await manager.connect(websocket, user_id)
        await manager.join_room(conn_id, "general")
        
        await manager.leave_room(conn_id, "general")
        
        _, info = manager._local_connections[conn_id]
        assert "general" not in info.rooms
        manager._redis.srem.assert_called()

    @pytest.mark.asyncio
    async def test_leave_room_nonexistent_connection(self, manager):
        """Test leave_room with nonexistent connection is safe."""
        await manager.leave_room("nonexistent", "general")
        # Should not raise


class TestRedisWebSocketManagerSubscriberLoop:
    """Tests for subscriber loop error handling."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            mgr = RedisWebSocketManager(redis_url="redis://localhost:6379")
            return mgr

    @pytest.mark.asyncio
    async def test_subscriber_loop_handles_cancelled_error(self, manager):
        """Test subscriber loop handles CancelledError gracefully."""
        mock_pubsub = AsyncMock()
        mock_pubsub.get_message = AsyncMock(side_effect=asyncio.CancelledError())
        
        manager._pubsub = mock_pubsub
        manager._running = True
        
        # Should exit cleanly on CancelledError
        await manager._subscriber_loop()

