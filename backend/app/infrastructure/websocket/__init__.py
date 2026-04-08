# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
WebSocket infrastructure module.

Simple in-memory WebSocket management for:
- Real-time notifications
- Notification delivery
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
