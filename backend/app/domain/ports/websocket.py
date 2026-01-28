# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
WebSocket port interface.

Defines the contract for WebSocket connection management.
Supports pluggable backends: Memory (default) or Redis (scalable).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Awaitable
from uuid import UUID


class MessageType(str, Enum):
    """Types of WebSocket messages."""
    
    # System messages
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    
    # Notification messages
    NOTIFICATION = "notification"
    NOTIFICATION_READ = "notification_read"
    
    # Presence messages
    PRESENCE_ONLINE = "presence_online"
    PRESENCE_OFFLINE = "presence_offline"
    PRESENCE_AWAY = "presence_away"
    
    # Broadcast messages
    BROADCAST = "broadcast"
    TENANT_BROADCAST = "tenant_broadcast"


@dataclass
class WebSocketMessage:
    """
    WebSocket message structure.
    
    Standard format for all WebSocket communications.
    """
    
    type: MessageType
    payload: dict[str, Any] = field(default_factory=dict)
    sender_id: UUID | None = None
    recipient_id: UUID | None = None
    room_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    message_id: UUID | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "payload": self.payload,
            "sender_id": str(self.sender_id) if self.sender_id else None,
            "recipient_id": str(self.recipient_id) if self.recipient_id else None,
            "room_id": self.room_id,
            "timestamp": self.timestamp.isoformat(),
            "message_id": str(self.message_id) if self.message_id else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WebSocketMessage":
        """Create from dictionary."""
        return cls(
            type=MessageType(data["type"]),
            payload=data.get("payload", {}),
            sender_id=UUID(data["sender_id"]) if data.get("sender_id") else None,
            recipient_id=UUID(data["recipient_id"]) if data.get("recipient_id") else None,
            room_id=data.get("room_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(UTC),
            message_id=UUID(data["message_id"]) if data.get("message_id") else None,
        )


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    
    user_id: UUID
    tenant_id: UUID | None
    connection_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    rooms: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)


# Type alias for message handlers
MessageHandler = Callable[[WebSocketMessage, ConnectionInfo], Awaitable[None]]


class WebSocketPort(ABC):
    """
    Abstract base class for WebSocket management.
    
    Implementations:
        - MemoryWebSocketManager: Single-instance, in-memory (development)
        - RedisWebSocketManager: Distributed, Redis Pub/Sub (production)
    
    Usage:
        # Connect user
        await manager.connect(websocket, user_id, tenant_id)
        
        # Send to specific user
        await manager.send_to_user(user_id, message)
        
        # Broadcast to all users in tenant
        await manager.broadcast_to_tenant(tenant_id, message)
        
        # Join/leave rooms (for group chats)
        await manager.join_room(user_id, room_id)
        await manager.leave_room(user_id, room_id)
        await manager.send_to_room(room_id, message)
    """
    
    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the backend name (memory, redis)."""
        ...
    
    @abstractmethod
    async def connect(
        self,
        websocket: Any,
        user_id: UUID,
        tenant_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection object
            user_id: The authenticated user's ID
            tenant_id: Optional tenant ID for multi-tenant isolation
            metadata: Optional connection metadata
            
        Returns:
            Connection ID (unique identifier for this connection)
        """
        ...
    
    @abstractmethod
    async def disconnect(self, connection_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            connection_id: The connection ID to remove
        """
        ...
    
    @abstractmethod
    async def send_to_user(
        self,
        user_id: UUID,
        message: WebSocketMessage,
    ) -> int:
        """
        Send a message to all connections of a specific user.
        
        Args:
            user_id: Target user ID
            message: Message to send
            
        Returns:
            Number of connections the message was sent to
        """
        ...
    
    @abstractmethod
    async def send_to_connection(
        self,
        connection_id: str,
        message: WebSocketMessage,
    ) -> bool:
        """
        Send a message to a specific connection.
        
        Args:
            connection_id: Target connection ID
            message: Message to send
            
        Returns:
            True if sent successfully
        """
        ...
    
    @abstractmethod
    async def broadcast(
        self,
        message: WebSocketMessage,
        exclude_user: UUID | None = None,
    ) -> int:
        """
        Broadcast a message to all connected users.
        
        Args:
            message: Message to broadcast
            exclude_user: Optional user ID to exclude
            
        Returns:
            Number of connections the message was sent to
        """
        ...
    
    @abstractmethod
    async def broadcast_to_tenant(
        self,
        tenant_id: UUID,
        message: WebSocketMessage,
        exclude_user: UUID | None = None,
    ) -> int:
        """
        Broadcast a message to all users in a tenant.
        
        Args:
            tenant_id: Target tenant ID
            message: Message to broadcast
            exclude_user: Optional user ID to exclude
            
        Returns:
            Number of connections the message was sent to
        """
        ...
    
    @abstractmethod
    async def join_room(
        self,
        connection_id: str,
        room_id: str,
    ) -> None:
        """
        Add a connection to a room.
        
        Rooms are used for group chats or topic-based channels.
        
        Args:
            connection_id: Connection to add
            room_id: Room identifier
        """
        ...
    
    @abstractmethod
    async def leave_room(
        self,
        connection_id: str,
        room_id: str,
    ) -> None:
        """
        Remove a connection from a room.
        
        Args:
            connection_id: Connection to remove
            room_id: Room identifier
        """
        ...
    
    @abstractmethod
    async def send_to_room(
        self,
        room_id: str,
        message: WebSocketMessage,
        exclude_connection: str | None = None,
    ) -> int:
        """
        Send a message to all connections in a room.
        
        Args:
            room_id: Target room ID
            message: Message to send
            exclude_connection: Optional connection ID to exclude
            
        Returns:
            Number of connections the message was sent to
        """
        ...
    
    @abstractmethod
    async def get_user_connections(self, user_id: UUID) -> list[ConnectionInfo]:
        """
        Get all connections for a user.
        
        Args:
            user_id: User ID to look up
            
        Returns:
            List of connection info objects
        """
        ...
    
    @abstractmethod
    async def get_online_users(
        self,
        tenant_id: UUID | None = None,
    ) -> list[UUID]:
        """
        Get list of online user IDs.
        
        Args:
            tenant_id: Optional tenant filter
            
        Returns:
            List of online user IDs
        """
        ...
    
    @abstractmethod
    async def get_room_members(self, room_id: str) -> list[ConnectionInfo]:
        """
        Get all connections in a room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            List of connection info objects
        """
        ...
    
    @abstractmethod
    async def is_user_online(self, user_id: UUID) -> bool:
        """
        Check if a user has any active connections.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user has at least one connection
        """
        ...
    
    @abstractmethod
    def register_handler(
        self,
        message_type: MessageType,
        handler: MessageHandler,
    ) -> None:
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Async function to call when message is received
        """
        ...
    
    @abstractmethod
    async def handle_message(
        self,
        message: WebSocketMessage,
        connection: ConnectionInfo,
    ) -> None:
        """
        Process an incoming message through registered handlers.
        
        Args:
            message: Incoming message
            connection: Connection that sent the message
        """
        ...
