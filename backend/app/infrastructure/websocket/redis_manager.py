# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Redis-backed WebSocket manager.

Distributed WebSocket manager using Redis Pub/Sub for horizontal scaling.
Suitable for production deployments with multiple server instances.
"""

import asyncio
import json
import logging
from datetime import datetime, UTC
from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import WebSocket

from app.domain.ports.websocket import (
    ConnectionInfo,
    MessageHandler,
    MessageType,
    WebSocketMessage,
    WebSocketPort,
)

# Redis is an optional dependency
try:
    import redis.asyncio as redis
    from redis.asyncio.client import PubSub
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None  # type: ignore
    PubSub = None  # type: ignore

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from redis.asyncio.client import PubSub as PubSubType

logger = logging.getLogger(__name__)


class RedisWebSocketManager(WebSocketPort):
    """
    Redis-backed WebSocket manager for horizontal scaling.
    
    Uses Redis Pub/Sub to broadcast messages across multiple server instances.
    Each instance maintains its own local connections but receives messages
    from all instances via Redis.
    
    Features:
    - Horizontal scaling support
    - Automatic reconnection to Redis
    - Graceful degradation if Redis is unavailable
    - Connection state stored in Redis for cross-instance queries
    
    Architecture:
        Server 1 ─────┐
        Server 2 ─────┼───── Redis Pub/Sub ───── All Servers
        Server 3 ─────┘
    
    Usage:
        manager = RedisWebSocketManager(redis_url="redis://localhost:6379")
        await manager.start()  # Start Redis subscriber
        
        # Use like MemoryWebSocketManager
        conn_id = await manager.connect(websocket, user_id, tenant_id)
        await manager.send_to_user(user_id, message)
        
        await manager.stop()  # Cleanup on shutdown
    
    Requirements:
        pip install redis
    """
    
    # Redis key prefixes
    PREFIX = "ws:"
    CONNECTIONS_KEY = "ws:connections"
    USER_CONNS_KEY = "ws:user:"
    TENANT_CONNS_KEY = "ws:tenant:"
    ROOM_KEY = "ws:room:"
    ONLINE_KEY = "ws:online"
    
    # Pub/Sub channels
    BROADCAST_CHANNEL = "ws:broadcast"
    USER_CHANNEL = "ws:user:{user_id}"
    TENANT_CHANNEL = "ws:tenant:{tenant_id}"
    ROOM_CHANNEL = "ws:room:{room_id}"
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        instance_id: str | None = None,
    ) -> None:
        """
        Initialize the Redis WebSocket manager.
        
        Args:
            redis_url: Redis connection URL
            instance_id: Unique identifier for this server instance
        """
        if not HAS_REDIS:
            raise ImportError(
                "redis package is required for RedisWebSocketManager. "
                "Install with: pip install redis"
            )
        
        self._redis_url = redis_url
        self._instance_id = instance_id or str(uuid4())[:8]
        
        # Redis clients (typed as Any due to redis.asyncio typing issues)
        self._redis: Any = None
        self._pubsub: Any = None
        
        # Local connections (this instance only)
        self._local_connections: dict[str, tuple[WebSocket, ConnectionInfo]] = {}
        
        # Message handlers
        self._handlers: dict[MessageType, list[MessageHandler]] = {}
        
        # Background tasks
        self._subscriber_task: asyncio.Task | None = None
        self._running = False
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    @property
    def backend_name(self) -> str:
        """Return backend name."""
        return "redis"
    
    async def start(self) -> None:
        """Start the Redis connection and subscriber."""
        if self._running:
            return
        
        self._redis = redis.from_url(  # type: ignore[union-attr]
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        
        # Test connection
        await self._redis.ping()  # type: ignore[union-attr]
        
        # Start Pub/Sub subscriber
        self._pubsub = self._redis.pubsub()  # type: ignore[union-attr]
        await self._pubsub.psubscribe(f"{self.PREFIX}*")  # type: ignore[union-attr]
        
        self._running = True
        self._subscriber_task = asyncio.create_task(self._subscriber_loop())
        
        logger.info(f"RedisWebSocketManager started (instance={self._instance_id})")
    
    async def stop(self) -> None:
        """Stop the Redis connection and cleanup."""
        self._running = False
        
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.close()
        
        if self._redis:
            await self._redis.close()
        
        logger.info(f"RedisWebSocketManager stopped (instance={self._instance_id})")
    
    async def _subscriber_loop(self) -> None:
        """Background task to receive messages from Redis Pub/Sub."""
        while self._running and self._pubsub:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                
                if message and message["type"] == "pmessage":
                    await self._handle_pubsub_message(
                        message["channel"],
                        message["data"],
                    )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in subscriber loop: {e}")
                await asyncio.sleep(1)
    
    async def _handle_pubsub_message(self, channel: str, data: str) -> None:
        """Handle incoming Pub/Sub message."""
        try:
            msg_data = json.loads(data)
            
            # Skip messages from this instance
            if msg_data.get("_instance") == self._instance_id:
                return
            
            message = WebSocketMessage.from_dict(msg_data["message"])
            target_type = msg_data.get("target_type")
            target_id = msg_data.get("target_id")
            exclude_user = msg_data.get("exclude_user")
            
            if exclude_user:
                exclude_user = UUID(exclude_user)
            
            # Route to appropriate local connections
            if target_type == "user":
                await self._local_send_to_user(UUID(target_id), message)
            elif target_type == "tenant":
                await self._local_broadcast_to_tenant(
                    UUID(target_id), message, exclude_user
                )
            elif target_type == "room":
                await self._local_send_to_room(target_id, message)
            elif target_type == "broadcast":
                await self._local_broadcast(message, exclude_user)
            
        except Exception as e:
            logger.error(f"Error handling Pub/Sub message: {e}")
    
    async def _publish(
        self,
        channel: str,
        message: WebSocketMessage,
        target_type: str,
        target_id: str | None = None,
        exclude_user: UUID | None = None,
    ) -> None:
        """Publish a message to Redis Pub/Sub."""
        if not self._redis:
            return
        
        data = {
            "_instance": self._instance_id,
            "message": message.to_dict(),
            "target_type": target_type,
            "target_id": target_id,
            "exclude_user": str(exclude_user) if exclude_user else None,
        }
        
        await self._redis.publish(channel, json.dumps(data))
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: UUID,
        tenant_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Register a new WebSocket connection."""
        connection_id = f"{self._instance_id}:{uuid4()}"
        
        connection_info = ConnectionInfo(
            user_id=user_id,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connected_at=datetime.now(UTC),
            rooms=set(),
            metadata=metadata or {},
        )
        
        async with self._lock:
            # Store locally
            self._local_connections[connection_id] = (websocket, connection_info)
            
            # Store in Redis
            if self._redis:
                conn_data = {
                    "user_id": str(user_id),
                    "tenant_id": str(tenant_id) if tenant_id else None,
                    "instance": self._instance_id,
                    "connected_at": connection_info.connected_at.isoformat(),
                }
                
                await self._redis.hset(
                    self.CONNECTIONS_KEY,
                    connection_id,
                    json.dumps(conn_data),
                )
                
                await self._redis.sadd(f"{self.USER_CONNS_KEY}{user_id}", connection_id)
                
                if tenant_id:
                    await self._redis.sadd(
                        f"{self.TENANT_CONNS_KEY}{tenant_id}",
                        connection_id,
                    )
                
                await self._redis.sadd(self.ONLINE_KEY, str(user_id))
        
        logger.info(f"WebSocket connected: user={user_id}, conn={connection_id}")
        
        # Send connection confirmation
        await self._send_json(
            websocket,
            WebSocketMessage(
                type=MessageType.CONNECTED,
                payload={"connection_id": connection_id},
            ).to_dict(),
        )
        
        # Notify presence via Pub/Sub
        if tenant_id:
            await self._publish(
                f"{self.TENANT_CHANNEL.format(tenant_id=tenant_id)}",
                WebSocketMessage(
                    type=MessageType.PRESENCE_ONLINE,
                    payload={"user_id": str(user_id)},
                    sender_id=user_id,
                ),
                target_type="tenant",
                target_id=str(tenant_id),
                exclude_user=user_id,
            )
        
        return connection_id
    
    async def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if connection_id not in self._local_connections:
                return
            
            _, connection_info = self._local_connections[connection_id]
            user_id = connection_info.user_id
            tenant_id = connection_info.tenant_id
            
            # Remove from Redis
            if self._redis:
                await self._redis.hdel(self.CONNECTIONS_KEY, connection_id)
                await self._redis.srem(f"{self.USER_CONNS_KEY}{user_id}", connection_id)
                
                if tenant_id:
                    await self._redis.srem(
                        f"{self.TENANT_CONNS_KEY}{tenant_id}",
                        connection_id,
                    )
                
                # Remove from rooms
                for room_id in connection_info.rooms:
                    await self._redis.srem(f"{self.ROOM_KEY}{room_id}", connection_id)
                
                # Check if user still online
                remaining = await self._redis.scard(f"{self.USER_CONNS_KEY}{user_id}")
                if remaining == 0:
                    await self._redis.srem(self.ONLINE_KEY, str(user_id))
            
            # Remove locally
            del self._local_connections[connection_id]
        
        logger.info(f"WebSocket disconnected: conn={connection_id}")
        
        # Notify presence if user has no more connections
        if self._redis:
            remaining = await self._redis.scard(f"{self.USER_CONNS_KEY}{user_id}")
            if remaining == 0 and tenant_id:
                await self._publish(
                    f"{self.TENANT_CHANNEL.format(tenant_id=tenant_id)}",
                    WebSocketMessage(
                        type=MessageType.PRESENCE_OFFLINE,
                        payload={"user_id": str(user_id)},
                        sender_id=user_id,
                    ),
                    target_type="tenant",
                    target_id=str(tenant_id),
                )
    
    async def _send_json(self, websocket: WebSocket, data: dict[str, Any]) -> bool:
        """Send JSON data to a WebSocket."""
        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
            return False
    
    async def _local_send_to_user(
        self,
        user_id: UUID,
        message: WebSocketMessage,
    ) -> int:
        """Send to user's local connections only."""
        sent_count = 0
        
        for conn_id, (websocket, info) in list(self._local_connections.items()):
            if info.user_id == user_id:
                if await self._send_json(websocket, message.to_dict()):
                    sent_count += 1
        
        return sent_count
    
    async def send_to_user(
        self,
        user_id: UUID,
        message: WebSocketMessage,
    ) -> int:
        """Send a message to all connections of a user (all instances)."""
        # Send to local connections
        local_count = await self._local_send_to_user(user_id, message)
        
        # Publish to Redis for other instances
        await self._publish(
            f"{self.USER_CHANNEL.format(user_id=user_id)}",
            message,
            target_type="user",
            target_id=str(user_id),
        )
        
        return local_count
    
    async def send_to_connection(
        self,
        connection_id: str,
        message: WebSocketMessage,
    ) -> bool:
        """Send a message to a specific connection."""
        if connection_id in self._local_connections:
            websocket, _ = self._local_connections[connection_id]
            return await self._send_json(websocket, message.to_dict())
        
        # Connection might be on another instance
        # In that case, we'd need to route through Redis
        # For now, return False as we can't directly send
        return False
    
    async def _local_broadcast(
        self,
        message: WebSocketMessage,
        exclude_user: UUID | None = None,
    ) -> int:
        """Broadcast to local connections only."""
        sent_count = 0
        
        for conn_id, (websocket, info) in list(self._local_connections.items()):
            if exclude_user and info.user_id == exclude_user:
                continue
            
            if await self._send_json(websocket, message.to_dict()):
                sent_count += 1
        
        return sent_count
    
    async def broadcast(
        self,
        message: WebSocketMessage,
        exclude_user: UUID | None = None,
    ) -> int:
        """Broadcast a message to all connected users (all instances)."""
        # Send to local connections
        local_count = await self._local_broadcast(message, exclude_user)
        
        # Publish to Redis for other instances
        await self._publish(
            self.BROADCAST_CHANNEL,
            message,
            target_type="broadcast",
            exclude_user=exclude_user,
        )
        
        return local_count
    
    async def _local_broadcast_to_tenant(
        self,
        tenant_id: UUID,
        message: WebSocketMessage,
        exclude_user: UUID | None = None,
    ) -> int:
        """Broadcast to tenant's local connections only."""
        sent_count = 0
        
        for conn_id, (websocket, info) in list(self._local_connections.items()):
            if info.tenant_id != tenant_id:
                continue
            
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
        """Broadcast to all users in a tenant (all instances)."""
        # Send to local connections
        local_count = await self._local_broadcast_to_tenant(
            tenant_id, message, exclude_user
        )
        
        # Publish to Redis for other instances
        await self._publish(
            f"{self.TENANT_CHANNEL.format(tenant_id=tenant_id)}",
            message,
            target_type="tenant",
            target_id=str(tenant_id),
            exclude_user=exclude_user,
        )
        
        return local_count
    
    async def join_room(
        self,
        connection_id: str,
        room_id: str,
    ) -> None:
        """Add a connection to a room."""
        async with self._lock:
            if connection_id not in self._local_connections:
                return
            
            _, connection_info = self._local_connections[connection_id]
            connection_info.rooms.add(room_id)
            
            # Store in Redis
            if self._redis:
                await self._redis.sadd(f"{self.ROOM_KEY}{room_id}", connection_id)
        
        logger.debug(f"Connection {connection_id} joined room {room_id}")
    
    async def leave_room(
        self,
        connection_id: str,
        room_id: str,
    ) -> None:
        """Remove a connection from a room."""
        async with self._lock:
            if connection_id not in self._local_connections:
                return
            
            _, connection_info = self._local_connections[connection_id]
            connection_info.rooms.discard(room_id)
            
            # Remove from Redis
            if self._redis:
                await self._redis.srem(f"{self.ROOM_KEY}{room_id}", connection_id)
        
        logger.debug(f"Connection {connection_id} left room {room_id}")
    
    async def _local_send_to_room(
        self,
        room_id: str,
        message: WebSocketMessage,
        exclude_connection: str | None = None,
    ) -> int:
        """Send to room's local connections only."""
        sent_count = 0
        
        for conn_id, (websocket, info) in list(self._local_connections.items()):
            if room_id not in info.rooms:
                continue
            
            if conn_id == exclude_connection:
                continue
            
            if await self._send_json(websocket, message.to_dict()):
                sent_count += 1
        
        return sent_count
    
    async def send_to_room(
        self,
        room_id: str,
        message: WebSocketMessage,
        exclude_connection: str | None = None,
    ) -> int:
        """Send a message to all connections in a room (all instances)."""
        # Send to local connections
        local_count = await self._local_send_to_room(
            room_id, message, exclude_connection
        )
        
        # Publish to Redis for other instances
        await self._publish(
            f"{self.ROOM_CHANNEL.format(room_id=room_id)}",
            message,
            target_type="room",
            target_id=room_id,
        )
        
        return local_count
    
    async def get_user_connections(self, user_id: UUID) -> list[ConnectionInfo]:
        """Get all connections for a user (local only)."""
        connections = []
        
        for conn_id, (_, info) in self._local_connections.items():
            if info.user_id == user_id:
                connections.append(info)
        
        return connections
    
    async def get_online_users(
        self,
        tenant_id: UUID | None = None,
    ) -> list[UUID]:
        """Get list of online user IDs (from Redis)."""
        if not self._redis:
            return []
        
        if tenant_id:
            # Get connection IDs for tenant
            conn_ids = await self._redis.smembers(
                f"{self.TENANT_CONNS_KEY}{tenant_id}"
            )
            
            # Get unique user IDs
            user_ids = set()
            for conn_id in conn_ids:
                conn_data = await self._redis.hget(self.CONNECTIONS_KEY, conn_id)
                if conn_data:
                    data = json.loads(conn_data)
                    user_ids.add(UUID(data["user_id"]))
            
            return list(user_ids)
        
        # Get all online users
        user_ids_str = await self._redis.smembers(self.ONLINE_KEY)
        return [UUID(uid) for uid in user_ids_str]
    
    async def get_room_members(self, room_id: str) -> list[ConnectionInfo]:
        """Get all connections in a room (local only)."""
        members = []
        
        for conn_id, (_, info) in self._local_connections.items():
            if room_id in info.rooms:
                members.append(info)
        
        return members
    
    async def is_user_online(self, user_id: UUID) -> bool:
        """Check if a user has any active connections (from Redis)."""
        if not self._redis:
            # Fallback to local check
            return any(
                info.user_id == user_id
                for _, (_, info) in self._local_connections.items()
            )
        
        return bool(await self._redis.sismember(self.ONLINE_KEY, str(user_id)))
    
    def register_handler(
        self,
        message_type: MessageType,
        handler: MessageHandler,
    ) -> None:
        """Register a handler for a specific message type."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
        
        logger.debug(f"Registered handler for {message_type.value}")
    
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
                logger.error(f"Error in message handler: {e}", exc_info=True)
                
                # Send error back to sender
                if connection.connection_id in self._local_connections:
                    websocket, _ = self._local_connections[connection.connection_id]
                    await self._send_json(
                        websocket,
                        WebSocketMessage(
                            type=MessageType.ERROR,
                            payload={
                                "error": str(e),
                                "original_type": message.type.value,
                            },
                        ).to_dict(),
                    )
    
    # =========================================
    # Stats and monitoring
    # =========================================
    
    async def get_stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        stats = {
            "backend": self.backend_name,
            "instance_id": self._instance_id,
            "local_connections": len(self._local_connections),
        }
        
        if self._redis:
            stats["total_connections"] = await self._redis.hlen(self.CONNECTIONS_KEY)
            stats["total_online_users"] = await self._redis.scard(self.ONLINE_KEY)
        
        return stats
