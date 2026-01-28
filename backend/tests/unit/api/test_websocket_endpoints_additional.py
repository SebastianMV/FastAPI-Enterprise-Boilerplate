"""Additional websocket endpoint tests for coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC

from fastapi import WebSocket, WebSocketDisconnect


class TestMainWebSocketEndpoint:
    """Tests for main websocket endpoint."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock websocket."""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.receive_json = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_websocket_endpoint_disabled(self, mock_websocket):
        """Test websocket endpoint when disabled."""
        from app.api.v1.endpoints.websocket import websocket_endpoint
        
        with patch("app.api.v1.endpoints.websocket.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = False
            
            await websocket_endpoint(websocket=mock_websocket, token=None)
            
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_endpoint_auth_failure(self, mock_websocket):
        """Test websocket endpoint with authentication failure."""
        from app.api.v1.endpoints.websocket import websocket_endpoint
        
        with patch("app.api.v1.endpoints.websocket.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            
            with patch("app.api.v1.endpoints.websocket.authenticate_websocket") as mock_auth:
                mock_auth.return_value = None
                
                await websocket_endpoint(websocket=mock_websocket, token=None)
                
                mock_websocket.close.assert_called()

    @pytest.mark.asyncio
    async def test_websocket_endpoint_message_processing_error(self, mock_websocket):
        """Test websocket message processing with error."""
        from app.api.v1.endpoints.websocket import websocket_endpoint
        
        user_id = uuid4()
        tenant_id = uuid4()
        
        # First call returns data, second raises disconnect
        call_count = 0
        async def receive_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"type": "invalid_type"}
            raise WebSocketDisconnect()
        
        mock_websocket.receive_json = receive_side_effect
        
        with patch("app.api.v1.endpoints.websocket.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            
            with patch("app.api.v1.endpoints.websocket.authenticate_websocket") as mock_auth:
                mock_auth.return_value = (user_id, tenant_id)
                
                with patch("app.api.v1.endpoints.websocket.get_ws_manager") as mock_get_manager:
                    mock_manager = MagicMock()
                    mock_manager.connect = AsyncMock(return_value="conn-123")
                    mock_manager.disconnect = AsyncMock()
                    mock_manager.get_user_connections = AsyncMock(return_value=[])
                    mock_get_manager.return_value = mock_manager
                    
                    await websocket_endpoint(websocket=mock_websocket, token="valid-token")
                    
                    mock_manager.disconnect.assert_called_once()


class TestNotificationsWebSocketEndpoint:
    """Tests for notifications websocket endpoint."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock websocket."""
        ws = AsyncMock(spec=WebSocket)
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.receive_json = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_notifications_endpoint_disabled(self, mock_websocket):
        """Test notifications endpoint when disabled."""
        from app.api.v1.endpoints.websocket import notifications_endpoint
        
        with patch("app.api.v1.endpoints.websocket.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            mock_settings.WEBSOCKET_NOTIFICATIONS = False
            
            await notifications_endpoint(websocket=mock_websocket, token=None)
            
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_endpoint_both_disabled(self, mock_websocket):
        """Test notifications endpoint when both disabled."""
        from app.api.v1.endpoints.websocket import notifications_endpoint
        
        with patch("app.api.v1.endpoints.websocket.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = False
            mock_settings.WEBSOCKET_NOTIFICATIONS = True
            
            await notifications_endpoint(websocket=mock_websocket, token=None)
            
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifications_endpoint_auth_failure(self, mock_websocket):
        """Test notifications endpoint with auth failure."""
        from app.api.v1.endpoints.websocket import notifications_endpoint
        
        with patch("app.api.v1.endpoints.websocket.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            mock_settings.WEBSOCKET_NOTIFICATIONS = True
            
            with patch("app.api.v1.endpoints.websocket.authenticate_websocket") as mock_auth:
                mock_auth.return_value = None
                
                await notifications_endpoint(websocket=mock_websocket, token=None)
                
                mock_websocket.close.assert_called()

    @pytest.mark.asyncio
    async def test_notifications_endpoint_ping_pong(self, mock_websocket):
        """Test notifications endpoint ping/pong handling."""
        from app.api.v1.endpoints.websocket import notifications_endpoint
        
        user_id = uuid4()
        tenant_id = uuid4()
        
        call_count = 0
        async def receive_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"type": "ping", "payload": {"timestamp": 1234567890}}
            raise WebSocketDisconnect()
        
        mock_websocket.receive_json = receive_side_effect
        
        with patch("app.api.v1.endpoints.websocket.settings") as mock_settings:
            mock_settings.WEBSOCKET_ENABLED = True
            mock_settings.WEBSOCKET_NOTIFICATIONS = True
            
            with patch("app.api.v1.endpoints.websocket.authenticate_websocket") as mock_auth:
                mock_auth.return_value = (user_id, tenant_id)
                
                with patch("app.api.v1.endpoints.websocket.get_ws_manager") as mock_get_manager:
                    mock_manager = MagicMock()
                    mock_manager.connect = AsyncMock(return_value="conn-123")
                    mock_manager.disconnect = AsyncMock()
                    mock_get_manager.return_value = mock_manager
                    
                    await notifications_endpoint(websocket=mock_websocket, token="valid-token")
                    
                    # Check pong was sent
                    mock_websocket.send_json.assert_called()
                    pong_call = mock_websocket.send_json.call_args
                    assert pong_call[0][0]["type"] == "pong"


class TestWebSocketHelpers:
    """Tests for websocket helper functions."""

    @pytest.mark.asyncio
    async def test_authenticate_websocket_with_query_param(self):
        """Test websocket authentication with query parameter."""
        from app.api.v1.endpoints.websocket import authenticate_websocket
        
        user_id = uuid4()
        
        mock_websocket = MagicMock()
        mock_websocket.headers = {}
        
        with patch("app.api.v1.endpoints.websocket.validate_access_token") as mock_validate:
            mock_validate.return_value = {
                "sub": str(user_id),
                "tenant_id": None,
            }
            
            result = await authenticate_websocket(mock_websocket, "query-token")
            
            assert result is not None
            assert result[0] == user_id

    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token(self):
        """Test websocket authentication without token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket
        
        mock_websocket = MagicMock()
        mock_websocket.headers = {}
        
        result = await authenticate_websocket(mock_websocket, None)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_websocket_invalid_token(self):
        """Test websocket authentication with invalid token."""
        from app.api.v1.endpoints.websocket import authenticate_websocket
        
        mock_websocket = MagicMock()
        mock_websocket.headers = {"authorization": "Bearer invalid-token"}
        
        with patch("app.api.v1.endpoints.websocket.validate_access_token") as mock_validate:
            mock_validate.side_effect = Exception("Invalid token")
            
            result = await authenticate_websocket(mock_websocket, None)
            
            assert result is None

