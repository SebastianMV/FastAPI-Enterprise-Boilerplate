# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
WebSocket infrastructure module.

Pluggable WebSocket management with support for:
- Memory backend (development, single instance)
- Redis backend (production, horizontal scaling)
"""

from app.domain.ports.websocket import (
    ConnectionInfo,
    MessageHandler,
    MessageType,
    WebSocketMessage,
    WebSocketPort,
)
from app.infrastructure.websocket.memory_manager import MemoryWebSocketManager

# Lazy import for Redis manager (optional dependency)
_redis_manager: type | None = None


def get_redis_manager():
    """Lazy load Redis manager."""
    global _redis_manager
    if _redis_manager is None:
        from app.infrastructure.websocket.redis_manager import RedisWebSocketManager
        _redis_manager = RedisWebSocketManager
    return _redis_manager


__all__ = [
    "ConnectionInfo",
    "MessageHandler",
    "MessageType",
    "WebSocketMessage",
    "WebSocketPort",
    "MemoryWebSocketManager",
    "get_redis_manager",
]
