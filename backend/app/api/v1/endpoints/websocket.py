# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
WebSocket endpoint for real-time communication.

Handles WebSocket connections for:
- Real-time notifications
- Presence (online status)
"""

import json
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.config import settings
from app.domain.ports.websocket import MessageType, WebSocketMessage
from app.infrastructure.auth.jwt_handler import validate_access_token
from app.infrastructure.observability.logging import get_logger
from app.infrastructure.websocket import (
    ConnectionInfo,
    MemoryWebSocketManager,
    WebSocketPort,
)

logger = get_logger(__name__)

router = APIRouter()

# Maximum WebSocket message size (64KB) to prevent memory exhaustion
_WS_MAX_MESSAGE_SIZE = 64 * 1024


async def _receive_json_safe(websocket: WebSocket) -> dict:
    """Receive JSON with message size validation."""
    raw = await websocket.receive_text()
    if len(raw) > _WS_MAX_MESSAGE_SIZE:
        await websocket.close(code=1009, reason="Message too large")
        raise WebSocketDisconnect(code=1009)
    return json.loads(raw)


# Global WebSocket manager instance
# This will be replaced with dependency injection in production
_ws_manager: WebSocketPort | None = None


def get_ws_manager() -> WebSocketPort:
    """
    Get the WebSocket manager instance.

    Creates a singleton in-memory manager.
    """
    global _ws_manager

    if _ws_manager is None:
        _ws_manager = MemoryWebSocketManager()

        # Register default handlers
        _register_default_handlers(_ws_manager)

    return _ws_manager


def _register_default_handlers(manager: WebSocketPort) -> None:
    """Register default message handlers."""

    async def handle_ping(
        message: WebSocketMessage, connection: ConnectionInfo
    ) -> None:
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

    Token is read from:
    1. HttpOnly cookie (preferred, secure)
    2. Query parameter (fallback for clients that can't send cookies)

    Returns:
        Tuple of (user_id, tenant_id) if authenticated, None otherwise
    """
    # Prefer cookie-based auth (HttpOnly cookies are not exposed in URLs/logs)
    cookie_token = websocket.cookies.get("access_token")
    if token and not cookie_token:
        # In production, reject query-param tokens to prevent credential leakage
        # in server logs, proxy logs, Referer headers, and browser history.
        from app.config import settings

        if settings.ENVIRONMENT == "production":
            logger.warning(
                "websocket_query_param_auth_rejected"
            )
            return None

        logger.warning(
            "websocket_query_param_auth_deprecated"
        )
    auth_token = cookie_token or token

    if not auth_token:
        return None

    try:
        payload = validate_access_token(auth_token)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"]) if payload.get("tenant_id") else None
        return user_id, tenant_id

    except Exception as e:
        logger.warning("ws_auth_failed", error=type(e).__name__)
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
    if not connection_id:
        return  # Connection was rejected

    try:
        while True:
            # Receive message
            data = await _receive_json_safe(websocket)

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
                logger.error("ws_message_processing_error", error=type(e).__name__)
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {"message": "Failed to process message"},
                    }
                )

    except WebSocketDisconnect:
        logger.info("ws_disconnected", connection_id=str(connection_id))

    except Exception as e:
        logger.error("ws_error", error=type(e).__name__)

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
    if not connection_id:
        return  # Connection was rejected

    try:
        while True:
            # Only handle ping messages
            data = await _receive_json_safe(websocket)

            if data.get("type") == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                        "payload": {
                            "timestamp": data.get("payload", {}).get("timestamp")
                        },
                    }
                )

    except WebSocketDisconnect:
        logger.debug("ws_disconnected", connection_id=str(connection_id))

    finally:
        await manager.disconnect(connection_id)
