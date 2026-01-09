# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for WebSocket endpoints and infrastructure."""

from __future__ import annotations

from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4
import pytest


class TestWebSocketEndpointsStructure:
    """Tests for WebSocket endpoints structure."""

    def test_router_import(self) -> None:
        """Test router can be imported."""
        from app.api.v1.endpoints.websocket import router
        assert router is not None

    def test_router_is_api_router(self) -> None:
        """Test router is an APIRouter."""
        from app.api.v1.endpoints.websocket import router
        from fastapi import APIRouter
        assert isinstance(router, APIRouter)

    def test_get_ws_manager_import(self) -> None:
        """Test get_ws_manager can be imported."""
        from app.api.v1.endpoints.websocket import get_ws_manager
        assert get_ws_manager is not None
        assert callable(get_ws_manager)


class TestWebSocketMessageTypes:
    """Tests for WebSocket message types."""

    def test_message_type_import(self) -> None:
        """Test MessageType can be imported."""
        from app.domain.ports.websocket import MessageType
        assert MessageType is not None

    def test_message_type_values(self) -> None:
        """Test MessageType has expected values."""
        from app.domain.ports.websocket import MessageType
        
        assert hasattr(MessageType, "PING")
        assert hasattr(MessageType, "PONG")

    def test_websocket_message_import(self) -> None:
        """Test WebSocketMessage can be imported."""
        from app.domain.ports.websocket import WebSocketMessage
        assert WebSocketMessage is not None

    def test_websocket_message_creation(self) -> None:
        """Test WebSocketMessage creation."""
        from app.domain.ports.websocket import WebSocketMessage, MessageType
        
        msg = WebSocketMessage(
            type=MessageType.PING,
            payload={"test": "data"}
        )
        assert msg.type == MessageType.PING


class TestWebSocketInfrastructure:
    """Tests for WebSocket infrastructure."""

    def test_memory_ws_manager_import(self) -> None:
        """Test MemoryWebSocketManager can be imported."""
        from app.infrastructure.websocket import MemoryWebSocketManager
        assert MemoryWebSocketManager is not None

    def test_connection_info_import(self) -> None:
        """Test ConnectionInfo can be imported."""
        from app.infrastructure.websocket import ConnectionInfo
        assert ConnectionInfo is not None

    def test_websocket_port_import(self) -> None:
        """Test WebSocketPort can be imported."""
        from app.infrastructure.websocket import WebSocketPort
        assert WebSocketPort is not None


class TestMemoryWebSocketManager:
    """Tests for MemoryWebSocketManager."""

    def test_manager_creation(self) -> None:
        """Test MemoryWebSocketManager can be created."""
        from app.infrastructure.websocket import MemoryWebSocketManager
        
        manager = MemoryWebSocketManager()
        assert manager is not None

    @pytest.mark.asyncio
    async def test_manager_has_connect_method(self) -> None:
        """Test manager has connect method."""
        from app.infrastructure.websocket import MemoryWebSocketManager
        
        manager = MemoryWebSocketManager()
        assert hasattr(manager, "connect")

    @pytest.mark.asyncio
    async def test_manager_has_disconnect_method(self) -> None:
        """Test manager has disconnect method."""
        from app.infrastructure.websocket import MemoryWebSocketManager
        
        manager = MemoryWebSocketManager()
        assert hasattr(manager, "disconnect")

    @pytest.mark.asyncio
    async def test_manager_has_send_methods(self) -> None:
        """Test manager has send methods."""
        from app.infrastructure.websocket import MemoryWebSocketManager
        
        manager = MemoryWebSocketManager()
        assert hasattr(manager, "send_to_connection")
        assert hasattr(manager, "send_to_user")
        assert hasattr(manager, "broadcast")


class TestWebSocketConfig:
    """Tests for WebSocket configuration."""

    def test_websocket_backend_setting(self) -> None:
        """Test WEBSOCKET_BACKEND setting exists."""
        from app.config import settings
        
        assert hasattr(settings, "WEBSOCKET_BACKEND")

    def test_websocket_backend_default(self) -> None:
        """Test WEBSOCKET_BACKEND has valid value."""
        from app.config import settings
        
        assert settings.WEBSOCKET_BACKEND in ["memory", "redis"]


class TestWebSocketRouter:
    """Tests for WebSocket router routes."""

    def test_router_has_routes(self) -> None:
        """Test router has WebSocket routes."""
        from app.api.v1.endpoints.websocket import router
        
        assert len(router.routes) >= 1

    def test_ws_endpoint_exists(self) -> None:
        """Test WebSocket endpoint is registered."""
        from app.api.v1.endpoints.websocket import router
        
        # Check for any websocket route
        has_ws_route = any(
            hasattr(r, "endpoint") for r in router.routes
        )
        assert has_ws_route
