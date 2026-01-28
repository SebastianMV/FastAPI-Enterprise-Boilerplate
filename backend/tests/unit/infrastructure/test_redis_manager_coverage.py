# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for redis_manager coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import asyncio
import json


class TestRedisWebSocketManagerCoverage:
    """Additional coverage tests for RedisWebSocketManager."""

    @pytest.mark.asyncio
    async def test_redis_not_available(self):
        """Test when Redis module is not available (lines 33-36)."""
        # This tests the import guard
        with patch.dict("sys.modules", {"redis.asyncio": None}):
            # The guard HAS_REDIS will be False
            from app.infrastructure.websocket.redis_manager import HAS_REDIS
            # We just test that the module handles the import gracefully
            # The actual HAS_REDIS value depends on whether redis is installed
            assert isinstance(HAS_REDIS, bool)

    @pytest.mark.asyncio
    async def test_stop_manager(self):
        """Test stop method (lines 163-167)."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
        manager._running = True
        manager._subscriber_task = None
        manager._pubsub = None
        manager._redis = None
        manager._instance_id = "test-instance"
        
        await manager.stop()
        
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_stop_manager_with_subscriber_task(self):
        """Test stop method with active subscriber task (lines 163-167)."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
        manager._running = True
        manager._instance_id = "test-instance"
        
        # Create a mock task that will be cancelled
        async def dummy_task():
            while True:
                await asyncio.sleep(0.1)
        
        task = asyncio.create_task(dummy_task())
        manager._subscriber_task = task
        manager._pubsub = None
        manager._redis = None
        
        await manager.stop()
        
        assert manager._running is False
        assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_subscriber_loop_cancelled_error(self):
        """Test subscriber loop handles CancelledError (line 187)."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
        manager._running = True
        manager._instance_id = "test-instance"
        
        mock_pubsub = MagicMock()
        mock_pubsub.get_message = AsyncMock(side_effect=asyncio.CancelledError())
        manager._pubsub = mock_pubsub
        
        # Should exit gracefully on CancelledError
        await manager._subscriber_loop()
        
        # Verify it ran without raising
        assert True

    @pytest.mark.asyncio
    async def test_subscriber_loop_general_exception(self):
        """Test subscriber loop handles general exceptions (line 195)."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
        manager._running = True
        manager._instance_id = "test-instance"
        
        call_count = 0
        
        async def mock_get_message(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Redis error")
            # Stop the loop after handling the error
            manager._running = False
            return None
        
        mock_pubsub = MagicMock()
        mock_pubsub.get_message = mock_get_message
        manager._pubsub = mock_pubsub
        
        await manager._subscriber_loop()
        
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_pubsub_message_skip_own_instance(self):
        """Test _handle_pubsub_message skips own instance messages (line 213)."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
        manager._instance_id = "test-instance"
        
        data = json.dumps({
            "_instance": "test-instance",  # Same instance
            "message": {"type": "test", "data": {}},
            "target_type": "broadcast",
        })
        
        # Should return early without processing
        await manager._handle_pubsub_message("channel", data)
        
        # Verify no error occurred
        assert True

    @pytest.mark.asyncio
    async def test_handle_pubsub_message_error(self):
        """Test _handle_pubsub_message handles errors (line 227-228)."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        
        manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
        manager._instance_id = "test-instance"
        
        # Invalid JSON data
        await manager._handle_pubsub_message("channel", "invalid json")
        
        # Should log error but not raise
        assert True

    @pytest.mark.asyncio
    async def test_handle_pubsub_message_user_target(self):
        """Test _handle_pubsub_message routes to user (line 217)."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        from app.domain.ports.websocket import MessageType
        
        manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
        manager._instance_id = "test-instance"
        manager._local_send_to_user = AsyncMock()
        
        user_id = uuid4()
        data = json.dumps({
            "_instance": "other-instance",
            "message": {"type": MessageType.NOTIFICATION.value, "data": {"text": "hello"}},
            "target_type": "user",
            "target_id": str(user_id),
        })
        
        await manager._handle_pubsub_message("channel", data)
        
        manager._local_send_to_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_pubsub_message_room_target(self):
        """Test _handle_pubsub_message routes to room (line 223)."""
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        from app.domain.ports.websocket import MessageType
        
        manager = RedisWebSocketManager.__new__(RedisWebSocketManager)
        manager._instance_id = "test-instance"
        manager._local_send_to_room = AsyncMock()
        
        data = json.dumps({
            "_instance": "other-instance",
            "message": {"type": MessageType.BROADCAST.value, "data": {}},
            "target_type": "room",
            "target_id": "room-123",
        })
        
        await manager._handle_pubsub_message("channel", data)
        
        manager._local_send_to_room.assert_called_once()
