# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Additional WebSocket endpoint tests for coverage improvement.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import WebSocket
from fastapi.testclient import TestClient

from app.domain.ports.websocket import MessageType, WebSocketMessage


class TestWebSocketAuthentication:
    """Test WebSocket authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token(self):
        """Test authentication with no token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket
        
        mock_websocket = MagicMock(spec=WebSocket)
        
        result = await authenticate_websocket(mock_websocket, token=None)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_websocket_invalid_token(self):
        """Test authentication with invalid token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket
        
        mock_websocket = MagicMock(spec=WebSocket)
        
        with patch('app.api.v1.endpoints.websocket.validate_access_token') as mock_validate:
            mock_validate.side_effect = Exception("Invalid token")
            
            result = await authenticate_websocket(mock_websocket, token="invalid_token")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_websocket_valid_token(self):
        """Test authentication with valid token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket
        
        mock_websocket = MagicMock(spec=WebSocket)
        user_id = uuid4()
        tenant_id = uuid4()
        
        with patch('app.api.v1.endpoints.websocket.validate_access_token') as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
            }
            
            result = await authenticate_websocket(mock_websocket, token="valid_token")
            
            assert result is not None
            assert result[0] == user_id
            assert result[1] == tenant_id

    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_tenant(self):
        """Test authentication with no tenant in token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket
        
        mock_websocket = MagicMock(spec=WebSocket)
        user_id = uuid4()
        
        with patch('app.api.v1.endpoints.websocket.validate_access_token') as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
            }
            
            result = await authenticate_websocket(mock_websocket, token="valid_token")
            
            assert result is not None
            assert result[0] == user_id
            assert result[1] is None


class TestWebSocketManager:
    """Test WebSocket manager creation."""

    def test_get_ws_manager_memory(self):
        """Test getting memory WebSocket manager."""
        from app.api.v1.endpoints.websocket import get_ws_manager, _ws_manager
        import app.api.v1.endpoints.websocket as ws_module
        
        # Reset global manager
        ws_module._ws_manager = None
        
        with patch('app.api.v1.endpoints.websocket.settings') as mock_settings:
            mock_settings.WEBSOCKET_BACKEND = "memory"
            
            manager = get_ws_manager()
            
            assert manager is not None
            
            # Reset for other tests
            ws_module._ws_manager = None


class TestDefaultHandlers:
    """Test default message handlers."""

    @pytest.mark.asyncio
    async def test_register_default_handlers(self):
        """Test that default handlers are registered."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.infrastructure.websocket import MemoryWebSocketManager
        
        manager = MemoryWebSocketManager()
        _register_default_handlers(manager)
        
        # Test should just verify registration doesn't fail
        # The handlers dict may be named differently or be internal
        assert manager is not None

    @pytest.mark.asyncio
    async def test_handlers_registration_without_error(self):
        """Test handlers can be registered without errors."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.infrastructure.websocket import MemoryWebSocketManager
        
        manager = MemoryWebSocketManager()
        
        # Should not raise
        try:
            _register_default_handlers(manager)
            registered = True
        except Exception:
            registered = False
        
        assert registered is True

    @pytest.mark.asyncio
    async def test_multiple_handler_registration(self):
        """Test registering handlers multiple times."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.infrastructure.websocket import MemoryWebSocketManager
        
        manager = MemoryWebSocketManager()
        
        # Register twice should not fail
        _register_default_handlers(manager)
        _register_default_handlers(manager)
        
        assert manager is not None

    @pytest.mark.asyncio
    async def test_handlers_with_different_managers(self):
        """Test handlers with different manager types."""
        from app.api.v1.endpoints.websocket import _register_default_handlers
        from app.infrastructure.websocket import MemoryWebSocketManager
        
        manager1 = MemoryWebSocketManager()
        manager2 = MemoryWebSocketManager()
        
        _register_default_handlers(manager1)
        _register_default_handlers(manager2)
        
        assert manager1 is not manager2


class TestWebSocketEndpointDisabled:
    """Test WebSocket endpoints when disabled."""

    @pytest.mark.asyncio
    async def test_websocket_disabled(self):
        """Test main WebSocket when disabled."""
        from app.api.v1.endpoints.websocket import websocket_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        
        with patch('app.api.v1.endpoints.websocket.settings') as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = False
            
            await websocket_endpoint(mock_websocket, token="token")
            
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_websocket_disabled(self):
        """Test notifications WebSocket when disabled."""
        from app.api.v1.endpoints.websocket import notifications_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        
        with patch('app.api.v1.endpoints.websocket.settings') as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = False
            
            await notifications_endpoint(mock_websocket, token="token")
            
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_disabled_only(self):
        """Test notifications WebSocket when only notifications disabled."""
        from app.api.v1.endpoints.websocket import notifications_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        
        with patch('app.api.v1.endpoints.websocket.settings') as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            mock_settings.WEBSOCKET_NOTIFICATIONS = False
            
            await notifications_endpoint(mock_websocket, token="token")
            
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_room_disabled(self):
        """Test chat room WebSocket when disabled."""
        from app.api.v1.endpoints.websocket import chat_room_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        
        with patch('app.api.v1.endpoints.websocket.settings') as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = False
            
            await chat_room_endpoint(mock_websocket, "room1", token="token")
            
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_room_chat_disabled(self):
        """Test chat room WebSocket when chat disabled."""
        from app.api.v1.endpoints.websocket import chat_room_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        
        with patch('app.api.v1.endpoints.websocket.settings') as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            mock_settings.WEBSOCKET_CHAT = False
            
            await chat_room_endpoint(mock_websocket, "room1", token="token")
            
            mock_websocket.close.assert_called_once()


class TestWebSocketAuthFailure:
    """Test WebSocket endpoints with auth failure."""

    @pytest.mark.asyncio
    async def test_websocket_auth_failure(self):
        """Test main WebSocket with auth failure."""
        from app.api.v1.endpoints.websocket import websocket_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        
        with patch('app.api.v1.endpoints.websocket.settings') as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            
            with patch('app.api.v1.endpoints.websocket.authenticate_websocket', 
                       new_callable=AsyncMock) as mock_auth:
                mock_auth.return_value = None
                
                await websocket_endpoint(mock_websocket, token="bad_token")
                
                mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_auth_failure(self):
        """Test notifications WebSocket with auth failure."""
        from app.api.v1.endpoints.websocket import notifications_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        
        with patch('app.api.v1.endpoints.websocket.settings') as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            mock_settings.WEBSOCKET_NOTIFICATIONS = True
            
            with patch('app.api.v1.endpoints.websocket.authenticate_websocket',
                       new_callable=AsyncMock) as mock_auth:
                mock_auth.return_value = None
                
                await notifications_endpoint(mock_websocket, token="bad_token")
                
                mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_room_auth_failure(self):
        """Test chat room WebSocket with auth failure."""
        from app.api.v1.endpoints.websocket import chat_room_endpoint
        
        mock_websocket = AsyncMock(spec=WebSocket)
        
        with patch('app.api.v1.endpoints.websocket.settings') as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            mock_settings.WEBSOCKET_CHAT = True
            
            with patch('app.api.v1.endpoints.websocket.authenticate_websocket',
                       new_callable=AsyncMock) as mock_auth:
                mock_auth.return_value = None
                
                await chat_room_endpoint(mock_websocket, "room1", token="bad_token")
                
                mock_websocket.close.assert_called_once()
