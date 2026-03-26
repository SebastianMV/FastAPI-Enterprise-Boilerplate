# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
In-memory WebSocket manager.

Single-instance WebSocket manager for development and small deployments.
For horizontal scaling, use RedisWebSocketManager instead.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import WebSocket

from app.domain.ports.websocket import (
    ConnectionInfo,
    MessageHandler,
    MessageType,
    WebSocketMessage,
    WebSocketPort,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class MemoryWebSocketManager(WebSocketPort):
    """
    In-memory WebSocket connection manager.

    Stores all connections in memory. Suitable for:
    - Development environments
    - Single-instance deployments
    - Small applications (< 1000 concurrent connections)

    Limitations:
    - Not suitable for horizontal scaling
    - Connections lost on server restart
    - Memory usage grows with connections

    Usage:
        manager = MemoryWebSocketManager()

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            conn_id = await manager.connect(websocket, user_id, tenant_id)
            try:
                while True:
                    data = await websocket.receive_json()
                    message = WebSocketMessage.from_dict(data)
                    await manager.handle_message(message, conn_info)
            except WebSocketDisconnect:
                await manager.disconnect(conn_id)
    """

    # Connection limits to prevent resource exhaustion
    MAX_CONNECTIONS_PER_USER = 5
    MAX_TOTAL_CONNECTIONS = 500

    def __init__(self) -> None:
        """Initialize the in-memory manager."""
        # connection_id -> (WebSocket, ConnectionInfo)
        self._connections: dict[str, tuple[WebSocket, ConnectionInfo]] = {}

        # user_id -> set of connection_ids
        self._user_connections: dict[UUID, set[str]] = {}

        # tenant_id -> set of connection_ids
        self._tenant_connections: dict[UUID, set[str]] = {}

        # room_id -> set of connection_ids
        self._rooms: dict[str, set[str]] = {}

        # Message handlers by type
        self._handlers: dict[MessageType, list[MessageHandler]] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    @property
    def backend_name(self) -> str:
        """Return backend name."""
        return "memory"

    async def connect(
        self,
        websocket: WebSocket,
        user_id: UUID,
        tenant_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Register a new WebSocket connection."""
        connection_id = str(uuid4())

        connection_info = ConnectionInfo(
            user_id=user_id,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connected_at=datetime.now(UTC),
            rooms=set(),
            metadata=metadata or {},
        )

        async with self._lock:
            # Enforce global connection limit
            if len(self._connections) >= self.MAX_TOTAL_CONNECTIONS:
                logger.warning(
                    "websocket_global_limit_reached",
                    max_connections=self.MAX_TOTAL_CONNECTIONS,
                )
                await websocket.close(code=1013)  # Try Again Later
                return None

            # Enforce per-user connection limit
            user_conns = self._user_connections.get(user_id, set())
            if len(user_conns) >= self.MAX_CONNECTIONS_PER_USER:
                logger.warning("websocket_per_user_limit_reached")
                await websocket.close(code=1008)  # Policy Violation
                return None

            # Store connection
            self._connections[connection_id] = (websocket, connection_info)

            # Index by user
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

            # Index by tenant
            if tenant_id:
                if tenant_id not in self._tenant_connections:
                    self._tenant_connections[tenant_id] = set()
                self._tenant_connections[tenant_id].add(connection_id)

        logger.info(
            "websocket_connected",
            connection_id=connection_id,
        )

        # Send connection confirmation
        await self._send_json(
            websocket,
            WebSocketMessage(
                type=MessageType.CONNECTED,
                payload={"connection_id": connection_id},
            ).to_dict(),
        )

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if connection_id not in self._connections:
                return

            _, connection_info = self._connections[connection_id]
            user_id = connection_info.user_id
            tenant_id = connection_info.tenant_id

            # Remove from user index
            if user_id in self._user_connections:
                self._user_connections[user_id].discard(connection_id)
                if not self._user_connections[user_id]:
                    del self._user_connections[user_id]

            # Remove from tenant index
            if tenant_id and tenant_id in self._tenant_connections:
                self._tenant_connections[tenant_id].discard(connection_id)
                if not self._tenant_connections[tenant_id]:
                    del self._tenant_connections[tenant_id]

            # Remove from rooms
            for room_id in list(connection_info.rooms):
                if room_id in self._rooms:
                    self._rooms[room_id].discard(connection_id)
                    if not self._rooms[room_id]:
                        del self._rooms[room_id]

            # Remove connection
            del self._connections[connection_id]

        logger.info("websocket_disconnected", connection_id=connection_id)

    async def _send_json(self, websocket: WebSocket, data: dict[str, Any]) -> bool:
        """Send JSON data to a WebSocket."""
        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.warning("websocket_send_failed", error=type(e).__name__)
            return False

    async def send_to_user(
        self,
        user_id: UUID,
        message: WebSocketMessage,
    ) -> int:
        """Send a message to all connections of a user."""
        sent_count = 0

        connection_ids = self._user_connections.get(user_id, set()).copy()

        for conn_id in connection_ids:
            if conn_id in self._connections:
                websocket, _ = self._connections[conn_id]
                if await self._send_json(websocket, message.to_dict()):
                    sent_count += 1

        return sent_count

    async def send_to_connection(
        self,
        connection_id: str,
        message: WebSocketMessage,
    ) -> bool:
        """Send a message to a specific connection."""
        if connection_id not in self._connections:
            return False

        websocket, _ = self._connections[connection_id]
        return await self._send_json(websocket, message.to_dict())

    async def broadcast(
        self,
        message: WebSocketMessage,
        exclude_user: UUID | None = None,
    ) -> int:
        """Broadcast a message to all connected users."""
        sent_count = 0

        for _conn_id, (websocket, info) in list(self._connections.items()):
            if exclude_user and info.user_id == exclude_user:
                continue

            if await self._send_json(websocket, message.to_dict()):
                sent_count += 1

        return sent_count

    async def broadcast_to_tenant(
        self,
        tenant_id: UUID,
        message: WebSocketMessage,
        exclude_user: UUID | None = None,
    ) -> int:
        """Broadcast a message to all users in a tenant."""
        sent_count = 0

        connection_ids = self._tenant_connections.get(tenant_id, set()).copy()

        for conn_id in connection_ids:
            if conn_id in self._connections:
                websocket, info = self._connections[conn_id]

                if exclude_user and info.user_id == exclude_user:
                    continue

                if await self._send_json(websocket, message.to_dict()):
                    sent_count += 1

        return sent_count

    async def join_room(
        self,
        connection_id: str,
        room_id: str,
    ) -> None:
        """Add a connection to a room."""
        async with self._lock:
            if connection_id not in self._connections:
                return

            _, connection_info = self._connections[connection_id]

            # Add to room
            if room_id not in self._rooms:
                self._rooms[room_id] = set()
            self._rooms[room_id].add(connection_id)

            # Track in connection info
            connection_info.rooms.add(room_id)

        logger.debug(
            "websocket_room_joined", connection_id=connection_id, room_id=room_id
        )

    async def leave_room(
        self,
        connection_id: str,
        room_id: str,
    ) -> None:
        """Remove a connection from a room."""
        async with self._lock:
            if connection_id not in self._connections:
                return

            _, connection_info = self._connections[connection_id]

            # Remove from room
            if room_id in self._rooms:
                self._rooms[room_id].discard(connection_id)
                if not self._rooms[room_id]:
                    del self._rooms[room_id]

            # Update connection info
            connection_info.rooms.discard(room_id)

        logger.debug(
            "websocket_room_left", connection_id=connection_id, room_id=room_id
        )

    async def send_to_room(
        self,
        room_id: str,
        message: WebSocketMessage,
        exclude_connection: str | None = None,
    ) -> int:
        """Send a message to all connections in a room."""
        sent_count = 0

        connection_ids = self._rooms.get(room_id, set()).copy()

        for conn_id in connection_ids:
            if conn_id == exclude_connection:
                continue

            if conn_id in self._connections:
                websocket, _ = self._connections[conn_id]
                if await self._send_json(websocket, message.to_dict()):
                    sent_count += 1

        return sent_count

    async def get_user_connections(self, user_id: UUID) -> list[ConnectionInfo]:
        """Get all connections for a user."""
        connections = []

        connection_ids = self._user_connections.get(user_id, set())

        for conn_id in connection_ids:
            if conn_id in self._connections:
                _, info = self._connections[conn_id]
                connections.append(info)

        return connections

    async def get_online_users(
        self,
        tenant_id: UUID | None = None,
    ) -> list[UUID]:
        """Get list of online user IDs."""
        if tenant_id:
            # Get users in specific tenant
            online_users = set()
            connection_ids = self._tenant_connections.get(tenant_id, set())

            for conn_id in connection_ids:
                if conn_id in self._connections:
                    _, info = self._connections[conn_id]
                    online_users.add(info.user_id)

            return list(online_users)

        # Get all online users
        return list(self._user_connections.keys())

    async def get_room_members(self, room_id: str) -> list[ConnectionInfo]:
        """Get all connections in a room."""
        members = []

        connection_ids = self._rooms.get(room_id, set())

        for conn_id in connection_ids:
            if conn_id in self._connections:
                _, info = self._connections[conn_id]
                members.append(info)

        return members

    async def is_user_online(self, user_id: UUID) -> bool:
        """Check if a user has any active connections."""
        return user_id in self._user_connections and bool(
            self._user_connections[user_id]
        )

    def register_handler(
        self,
        message_type: MessageType,
        handler: MessageHandler,
    ) -> None:
        """Register a handler for a specific message type."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

        logger.debug("websocket_handler_registered", message_type=message_type.value)

    async def handle_message(
        self,
        message: WebSocketMessage,
        connection: ConnectionInfo,
    ) -> None:
        """Process an incoming message through registered handlers."""
        handlers = self._handlers.get(message.type, [])

        for handler in handlers:
            try:
                await handler(message, connection)
            except Exception as e:
                logger.error(
                    "websocket_handler_error", error=type(e).__name__, exc_info=True
                )

                # Send error back to sender
                if connection.connection_id in self._connections:
                    websocket, _ = self._connections[connection.connection_id]
                    await self._send_json(
                        websocket,
                        WebSocketMessage(
                            type=MessageType.ERROR,
                            payload={
                                "error": "Failed to process message",
                                "original_type": message.type.value,
                            },
                        ).to_dict(),
                    )

    # =========================================
    # Stats and monitoring
    # =========================================

    @property
    def total_connections(self) -> int:
        """Get total number of active connections."""
        return len(self._connections)

    @property
    def total_users(self) -> int:
        """Get total number of unique online users."""
        return len(self._user_connections)

    @property
    def total_rooms(self) -> int:
        """Get total number of active rooms."""
        return len(self._rooms)

    def get_stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        return {
            "backend": self.backend_name,
            "total_connections": self.total_connections,
            "total_users": self.total_users,
            "total_rooms": self.total_rooms,
            "tenants": len(self._tenant_connections),
        }
