# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Additional coverage tests for infrastructure modules."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestJwtHandlerCoverage:
    """Tests for jwt_handler missing coverage."""

    def test_get_token_user_id_missing_sub(self):
        """Test get_token_user_id raises when token has no sub."""
        from app.infrastructure.auth.jwt_handler import get_token_user_id
        from app.domain.exceptions.base import AuthenticationError
        
        # Mock decode_token to return payload without sub
        with patch('app.infrastructure.auth.jwt_handler.decode_token') as mock_decode:
            mock_decode.return_value = {"exp": 1234567890}  # No 'sub'
            
            with pytest.raises(AuthenticationError) as exc:
                get_token_user_id("some_token")
            
            assert "missing user id" in str(exc.value).lower()


class TestI18nCoverage:
    """Tests for i18n missing coverage."""

    def test_translate_with_invalid_params(self):
        """Test translate handles invalid params gracefully."""
        from app.infrastructure.i18n import I18n
        
        i18n = I18n()
        
        # Load with a key that has placeholders
        i18n._translations = {
            "en": {
                "test": {
                    "greeting": "Hello {name}, welcome to {place}!"
                }
            }
        }
        
        # Call with wrong params (missing 'place')
        result = i18n.t("test.greeting", locale="en", name="John")
        
        # Should return original message since params don't match
        assert "Hello" in result


class TestUptimeTrackerCoverage:
    """Tests for uptime_tracker missing coverage."""

    @pytest.mark.asyncio
    async def test_get_uptime_percentage_redis_error_with_local_fallback(self):
        """Test uptime percentage falls back to local counters on Redis error."""
        from app.infrastructure.monitoring.uptime_tracker import UptimeTracker
        
        tracker = UptimeTracker()
        tracker._local_check_count = 10
        tracker._local_success_count = 8
        
        # Mock _get_redis_client to return a mock that raises exception
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection error")
        tracker._redis_client = mock_redis
        
        result = await tracker.get_uptime_percentage()
        
        # Should return local calculation
        assert result == 80.0

    @pytest.mark.asyncio
    async def test_get_uptime_percentage_redis_error_no_local_checks(self):
        """Test uptime percentage returns 100 when no local checks on error."""
        from app.infrastructure.monitoring.uptime_tracker import UptimeTracker
        
        tracker = UptimeTracker()
        tracker._local_check_count = 0
        tracker._local_success_count = 0
        
        # Mock _get_redis_client to return a mock that raises exception
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection error")
        tracker._redis_client = mock_redis
        
        result = await tracker.get_uptime_percentage()
        
        # Should return 100.0 (assume healthy)
        assert result == 100.0


class TestLocalStorageCoverage:
    """Tests for local storage missing coverage."""

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file_returns_false(self):
        """Test delete returns False for non-existent file."""
        from app.infrastructure.storage.local import LocalStorageAdapter
        
        storage = LocalStorageAdapter(base_path="/tmp/test_storage_nonexistent")
        
        # Try to delete a file that doesn't exist
        result = await storage.delete("nonexistent/file.txt")
        
        assert result is False


class TestMemoryManagerCoverage:
    """Tests for memory websocket manager missing coverage."""

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self):
        """Test disconnect handles nonexistent connection gracefully."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager
        
        manager = MemoryWebSocketManager()
        
        # Disconnect should not raise for nonexistent connection
        await manager.disconnect(str(uuid4()))
        # If we get here without error, test passes

    @pytest.mark.asyncio
    async def test_broadcast_to_tenant_no_connections(self):
        """Test broadcast to tenant with no connections."""
        from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        manager = MemoryWebSocketManager()
        tenant_id = uuid4()
        
        # Broadcast to tenant with no connections should not raise
        await manager.broadcast_to_tenant(tenant_id, WebSocketMessage(type=MessageType.BROADCAST))
        # If we get here without error, test passes
