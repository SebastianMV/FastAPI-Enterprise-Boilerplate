# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
WebSocket endpoint for real-time communication.

Handles WebSocket connections for:
- Real-time notifications
- Presence (online status)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.domain.ports.websocket import MessageType, WebSocketMessage
from app.infrastructure.auth.jwt_handler import validate_access_token
from app.infrastructure.websocket import (
    ConnectionInfo,
    MemoryWebSocketManager,
    WebSocketPort,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Global WebSocket manager instance
# This will be replaced with dependency injection in production
_ws_manager: WebSocketPort | None = None


def get_ws_manager() -> WebSocketPort:
    """
    Get the WebSocket manager instance.
    
    Creates a singleton manager based on configuration.
    """
    global _ws_manager
    
    if _ws_manager is None:
        if settings.WEBSOCKET_BACKEND == "redis":
            from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
            _ws_manager = RedisWebSocketManager(redis_url=str(settings.REDIS_URL))
        else:
            _ws_manager = MemoryWebSocketManager()
        
        # Register default handlers
        _register_default_handlers(_ws_manager)
    
    return _ws_manager


def _register_default_handlers(manager: WebSocketPort) -> None:
    """Register default message handlers."""
    
    async def handle_ping(message: WebSocketMessage, connection: ConnectionInfo) -> None:
        """Handle ping messages."""
        await manager.send_to_connection(
            connection.connection_id,
            WebSocketMessage(
                type=MessageType.PONG,
                payload={"timestamp": message.payload.get("timestamp")},
            ),
        )
    
    # Register handlers
    manager.register_handler(MessageType.PING, handle_ping)


async def authenticate_websocket(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> tuple[UUID, UUID | None] | None:
    """
    Authenticate WebSocket connection using JWT token.
    
    Token can be provided via:
    1. Query parameter: ws://host/ws?token=xxx
    2. First message after connection
    
    Returns:
        Tuple of (user_id, tenant_id) if authenticated, None otherwise
    """
    if not token:
        return None
    
    try:
        payload = validate_access_token(token)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"]) if payload.get("tenant_id") else None
        return user_id, tenant_id
    
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """
    Main WebSocket endpoint.
    
    Connection flow:
    1. Client connects with token in query string
    2. Server validates token and accepts connection
    3. Server sends "connected" message with connection_id
    4. Client can now send/receive messages
    
    Message format (JSON):
    {
        "type": "chat_message|notification|ping|...",
        "payload": {...},
        "recipient_id": "uuid" (optional),
        "room_id": "string" (optional)
    }
    """
    # Check if WebSocket is enabled
    if not settings.WEBSOCKET_ENABLED:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Authenticate
    auth_result = await authenticate_websocket(websocket, token)
    
    if not auth_result:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id, tenant_id = auth_result
    
    # Accept connection
    await websocket.accept()
    
    # Get manager and register connection
    manager = get_ws_manager()
    connection_id = await manager.connect(
        websocket,
        user_id,
        tenant_id,
    )
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            try:
                message = WebSocketMessage.from_dict(data)
                message.sender_id = user_id  # Ensure sender is authenticated user
                
                # Get connection info
                connections = await manager.get_user_connections(user_id)
                connection = next(
                    (c for c in connections if c.connection_id == connection_id),
                    None,
                )
                
                if connection:
                    await manager.handle_message(message, connection)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": str(e)},
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        await manager.disconnect(connection_id)


@router.websocket("/ws/notifications")
async def notifications_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """
    Notifications-only WebSocket endpoint.
    
    Simpler endpoint for clients that only need to receive notifications.
    Does not support sending messages (except ping/pong).
    """
    if not settings.WEBSOCKET_ENABLED or not settings.WEBSOCKET_NOTIFICATIONS:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Authenticate
    auth_result = await authenticate_websocket(websocket, token)
    
    if not auth_result:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id, tenant_id = auth_result
    
    # Accept connection
    await websocket.accept()
    
    # Get manager and register connection
    manager = get_ws_manager()
    connection_id = await manager.connect(
        websocket,
        user_id,
        tenant_id,
        metadata={"type": "notifications_only"},
    )
    
    try:
        while True:
            # Only handle ping messages
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "payload": {"timestamp": data.get("payload", {}).get("timestamp")},
                })
    
    except WebSocketDisconnect:
        pass
    
    finally:
        await manager.disconnect(connection_id)


@router.websocket("/ws/chat/{room_id}")
async def chat_room_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str | None = Query(None),
):
    """
    Chat room WebSocket endpoint.
    
    Automatically joins the specified room on connection.
    """
    if not settings.WEBSOCKET_ENABLED or not settings.WEBSOCKET_CHAT:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Authenticate
    auth_result = await authenticate_websocket(websocket, token)
    
    if not auth_result:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id, tenant_id = auth_result
    
    # Accept connection
    await websocket.accept()
    
    # Get manager and register connection
    manager = get_ws_manager()
    connection_id = await manager.connect(
        websocket,
        user_id,
        tenant_id,
        metadata={"room_id": room_id},
    )
    
    # Auto-join the room
    await manager.join_room(connection_id, room_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            try:
                message = WebSocketMessage.from_dict(data)
                message.sender_id = user_id
                message.room_id = room_id  # Force room_id
                
                # Get connection info
                connections = await manager.get_user_connections(user_id)
                connection = next(
                    (c for c in connections if c.connection_id == connection_id),
                    None,
                )
                
                if connection:
                    await manager.handle_message(message, connection)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": str(e)},
                })
    
    except WebSocketDisconnect:
        pass
    
    finally:
        await manager.leave_room(connection_id, room_id)
        await manager.disconnect(connection_id)
