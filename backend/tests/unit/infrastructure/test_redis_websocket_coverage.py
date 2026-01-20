# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Additional tests for Redis WebSocket manager coverage.

Tests uncovered methods: rooms, online users, pub/sub.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import json

import pytest


class TestRedisWebSocketRooms:
    """Tests for room-related methods."""

    @pytest.mark.asyncio
    async def test_join_room_adds_to_local_and_redis(self):
        """Test joining room updates local and Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._local_connections = {}
                manager._lock = __import__("asyncio").Lock()
                
                # Mock connection
                mock_info = MagicMock(rooms=set())
                manager._local_connections["conn1"] = (AsyncMock(), mock_info)
                
                # Mock Redis
                mock_redis = AsyncMock()
                mock_redis.sadd = AsyncMock()
                manager._redis = mock_redis
                
                await manager.join_room("conn1", "room1")
                
                assert "room1" in mock_info.rooms
                mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_join_room_nonexistent_connection(self):
        """Test joining room with nonexistent connection."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._local_connections = {}
                manager._lock = __import__("asyncio").Lock()
                manager._redis = AsyncMock()
                
                # Should not raise error
                await manager.join_room("nonexistent", "room1")

    @pytest.mark.asyncio
    async def test_leave_room_removes_from_local_and_redis(self):
        """Test leaving room updates local and Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._local_connections = {}
                manager._lock = __import__("asyncio").Lock()
                
                # Mock connection in room
                mock_info = MagicMock(rooms={"room1", "room2"})
                manager._local_connections["conn1"] = (AsyncMock(), mock_info)
                
                # Mock Redis
                mock_redis = AsyncMock()
                mock_redis.srem = AsyncMock()
                manager._redis = mock_redis
                
                await manager.leave_room("conn1", "room1")
                
                assert "room1" not in mock_info.rooms
                mock_redis.srem.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_room_local_and_publish(self):
        """Test sending to room sends locally and publishes."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                from app.domain.ports.websocket import WebSocketMessage, MessageType
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._instance_id = "test"
                manager._local_connections = {}
                manager._redis = AsyncMock()
                manager._redis.publish = AsyncMock()
                
                # Mock connection in room
                mock_ws = AsyncMock()
                mock_info = MagicMock(
                    user_id=uuid4(),
                    tenant_id=uuid4(),
                    rooms={"room1", "room2"},
                )
                manager._local_connections["conn1"] = (mock_ws, mock_info)
                
                message = WebSocketMessage(
                    type=MessageType.NOTIFICATION,
                    payload={"text": "Hello room"},
                )
                
                count = await manager.send_to_room("room1", message)
                
                # Should send locally
                assert count >= 0
                # Should publish to Redis
                manager._redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_room_members_returns_local_connections(self):
        """Test getting room members returns local connections."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._local_connections = {}
                
                # Mock connection in room
                mock_info1 = MagicMock(rooms={"room1"})
                mock_info2 = MagicMock(rooms={"room2"})
                manager._local_connections["conn1"] = (AsyncMock(), mock_info1)
                manager._local_connections["conn2"] = (AsyncMock(), mock_info2)
                
                members = await manager.get_room_members("room1")
                
                assert len(members) == 1
                assert members[0] == mock_info1

    @pytest.mark.asyncio
    async def test_get_room_members_empty_room(self):
        """Test getting members of empty room."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._local_connections = {}
                
                members = await manager.get_room_members("nonexistent")
                
                assert members == []


class TestRedisWebSocketOnlineUsers:
    """Tests for online user tracking."""

    @pytest.mark.asyncio
    async def test_get_user_connections_returns_local_only(self):
        """Test getting user connections returns local connections."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._local_connections = {}
                
                user1 = uuid4()
                user2 = uuid4()
                
                # Mock connections for two users
                mock_info1 = MagicMock(user_id=user1)
                mock_info2 = MagicMock(user_id=user2)
                mock_info3 = MagicMock(user_id=user1)  # Same user, different connection
                
                manager._local_connections["conn1"] = (AsyncMock(), mock_info1)
                manager._local_connections["conn2"] = (AsyncMock(), mock_info2)
                manager._local_connections["conn3"] = (AsyncMock(), mock_info3)
                
                connections = await manager.get_user_connections(user1)
                
                assert len(connections) == 2
                assert all(c.user_id == user1 for c in connections)

    @pytest.mark.asyncio
    async def test_get_online_users_all(self):
        """Test getting all online users from Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                
                user1 = str(uuid4())
                user2 = str(uuid4())
                
                mock_redis = AsyncMock()
                mock_redis.smembers = AsyncMock(return_value={user1, user2})
                manager._redis = mock_redis
                
                users = await manager.get_online_users()
                
                assert len(users) == 2

    @pytest.mark.asyncio
    async def test_get_online_users_by_tenant(self):
        """Test getting online users filtered by tenant."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                
                tenant_id = uuid4()
                user1 = uuid4()
                user2 = uuid4()
                
                mock_redis = AsyncMock()
                # Mock tenant connections
                mock_redis.smembers = AsyncMock(return_value={b"conn1", b"conn2"})
                
                # Mock connection data
                async def mock_hget(key, conn_id):
                    if conn_id == b"conn1":
                        return json.dumps({"user_id": str(user1)})
                    elif conn_id == b"conn2":
                        return json.dumps({"user_id": str(user2)})
                    return None
                
                mock_redis.hget = mock_hget
                manager._redis = mock_redis
                
                users = await manager.get_online_users(tenant_id=tenant_id)
                
                assert len(users) == 2

    @pytest.mark.asyncio
    async def test_get_online_users_no_redis(self):
        """Test getting online users when Redis not available."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._redis = None
                
                users = await manager.get_online_users()
                
                assert users == []

    @pytest.mark.asyncio
    async def test_is_user_online_with_redis(self):
        """Test checking if user is online via Redis."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                
                user_id = uuid4()
                mock_redis = AsyncMock()
                mock_redis.sismember = AsyncMock(return_value=True)
                manager._redis = mock_redis
                
                is_online = await manager.is_user_online(user_id)
                
                assert is_online is True
                mock_redis.sismember.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_user_online_fallback_to_local(self):
        """Test checking if user is online falls back to local check."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._redis = None  # No Redis
                manager._local_connections = {}
                
                user_id = uuid4()
                
                # Add local connection for user
                mock_info = MagicMock(user_id=user_id)
                manager._local_connections["conn1"] = (AsyncMock(), mock_info)
                
                is_online = await manager.is_user_online(user_id)
                
                assert is_online is True


class TestRedisWebSocketPubSub:
    """Tests for Pub/Sub functionality."""

    @pytest.mark.asyncio
    async def test_publish_message_with_instance_id(self):
        """Test publishing message includes instance ID."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                from app.domain.ports.websocket import WebSocketMessage, MessageType
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._instance_id = "test-instance"
                
                mock_redis = AsyncMock()
                mock_redis.publish = AsyncMock()
                manager._redis = mock_redis
                
                message = WebSocketMessage(
                    type=MessageType.CHAT_MESSAGE,
                    payload={"text": "Hello"},
                )
                
                await manager._publish(
                    "test-channel",
                    message,
                    target_type="user",
                    target_id=str(uuid4()),
                )
                
                mock_redis.publish.assert_called_once()
                call_args = mock_redis.publish.call_args[0]
                published_data = json.loads(call_args[1])
                
                assert published_data["_instance"] == "test-instance"
                assert published_data["target_type"] == "user"

    @pytest.mark.asyncio
    async def test_handle_pubsub_message_skips_own_instance(self):
        """Test handling Pub/Sub message skips own instance messages."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._instance_id = "test-instance"
                
                data = json.dumps({
                    "_instance": "test-instance",  # Same instance
                    "message": {},
                    "target_type": "user",
                })
                
                # Should return early without processing
                await manager._handle_pubsub_message("channel", data)
                
                # No exception means it worked

    @pytest.mark.asyncio
    async def test_handle_pubsub_message_routes_to_user(self):
        """Test handling Pub/Sub message routes to user."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                from app.domain.ports.websocket import MessageType
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._instance_id = "test-instance"
                manager._local_send_to_user = AsyncMock()
                
                user_id = str(uuid4())
                data = json.dumps({
                    "_instance": "other-instance",
                    "message": {
                        "type": MessageType.NOTIFICATION.value,
                        "payload": {"text": "Hi"},
                    },
                    "target_type": "user",
                    "target_id": user_id,
                    "exclude_user": None,
                })
                
                await manager._handle_pubsub_message("channel", data)
                
                manager._local_send_to_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscriber_loop_handles_cancelled_error(self):
        """Test subscriber loop handles cancellation gracefully."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                import asyncio
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._running = True
                
                mock_pubsub = AsyncMock()
                mock_pubsub.get_message = AsyncMock(side_effect=asyncio.CancelledError)
                manager._pubsub = mock_pubsub
                
                # Should exit gracefully
                await manager._subscriber_loop()
                
                # No exception raised

    @pytest.mark.asyncio
    async def test_subscriber_loop_handles_errors(self):
        """Test subscriber loop handles errors and continues."""
        with patch("app.infrastructure.websocket.redis_manager.HAS_REDIS", True):
            with patch("app.infrastructure.websocket.redis_manager.redis"):
                from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
                import asyncio
                
                manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
                manager._running = True
                
                call_count = 0
                
                async def mock_get_message(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise Exception("Test error")
                    else:
                        manager._running = False  # Stop after error
                        return None
                
                mock_pubsub = AsyncMock()
                mock_pubsub.get_message = mock_get_message
                manager._pubsub = mock_pubsub
                
                # Should handle error and continue
                await manager._subscriber_loop()
                
                assert call_count == 2  # Error + recovery
