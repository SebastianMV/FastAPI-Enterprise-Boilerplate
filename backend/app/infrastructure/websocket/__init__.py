# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
WebSocket infrastructure module.

Simple in-memory WebSocket management for:
- Real-time notifications
- Presence tracking (online/offline)
- PING/PONG keepalive
"""

from app.domain.ports.websocket import (
    ConnectionInfo,
    MessageHandler,
    MessageType,
    WebSocketMessage,
    WebSocketPort,
)
from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

__all__ = [
    "ConnectionInfo",
    "MessageHandler",
    "MessageType",
    "WebSocketMessage",
    "WebSocketPort",
    "MemoryWebSocketManager",
]
