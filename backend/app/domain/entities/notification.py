# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Notification domain entity.

Represents a notification sent to a user.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from app.domain.entities.base import TenantEntity


class NotificationType(str, Enum):
    """Types of notifications."""

    # System notifications
    SYSTEM = "system"
    MAINTENANCE = "maintenance"

    # User-related
    WELCOME = "welcome"
    PASSWORD_CHANGED = "password_changed"
    LOGIN_ALERT = "login_alert"

    # Chat notifications
    NEW_MESSAGE = "new_message"
    MENTION = "mention"

    # Collaboration
    SHARED_WITH_YOU = "shared_with_you"
    COMMENT = "comment"
    ASSIGNMENT = "assignment"

    # Alerts
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""

    IN_APP = "in_app"  # WebSocket/UI notification
    EMAIL = "email"  # Email notification
    PUSH = "push"  # Push notification (mobile)
    SMS = "sms"  # SMS notification


@dataclass
class Notification(TenantEntity):
    """
    Notification domain entity.

    Represents a notification sent to a user through various channels.
    """

    # Target user
    user_id: UUID = field(default_factory=lambda: UUID(int=0))

    # Notification content
    type: NotificationType = NotificationType.INFO
    title: str = ""
    message: str = ""

    # Optional rich content
    # {"action_url": "...", "image_url": "...", "data": {...}}
    metadata: dict[str, Any] = field(default_factory=dict)

    # Priority and categorization
    priority: NotificationPriority = NotificationPriority.NORMAL
    category: str | None = None  # Custom category for filtering

    # Delivery settings
    channels: list[NotificationChannel] = field(
        default_factory=lambda: [NotificationChannel.IN_APP]
    )

    # Delivery status per channel
    # {"in_app": {"sent_at": "...", "delivered_at": "..."}, ...}
    delivery_status: dict[str, dict] = field(default_factory=dict)

    # Read status
    is_read: bool = False
    read_at: datetime | None = None

    # Expiration (optional)
    expires_at: datetime | None = None

    # Grouping (for notification stacking)
    group_key: str | None = None

    # Action tracking
    action_url: str | None = None
    action_clicked: bool = False
    action_clicked_at: datetime | None = None

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, type={self.type.value}, "
            f"user_id={self.user_id}, is_read={self.is_read})>"
        )

    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at

    def mark_read(self) -> None:
        """Mark notification as read."""
        self.is_read = True
        self.read_at = datetime.now(UTC)

    def mark_unread(self) -> None:
        """Mark notification as unread."""
        self.is_read = False
        self.read_at = None

    def mark_action_clicked(self) -> None:
        """Mark that user clicked the action."""
        self.action_clicked = True
        self.action_clicked_at = datetime.now(UTC)

    def mark_delivered(self, channel: NotificationChannel) -> None:
        """Mark notification as delivered through a channel."""
        if channel.value not in self.delivery_status:
            self.delivery_status[channel.value] = {}

        self.delivery_status[channel.value]["delivered_at"] = datetime.now(
            UTC
        ).isoformat()

    def mark_sent(self, channel: NotificationChannel) -> None:
        """Mark notification as sent through a channel."""
        if channel.value not in self.delivery_status:
            self.delivery_status[channel.value] = {}

        self.delivery_status[channel.value]["sent_at"] = datetime.now(UTC).isoformat()

    def is_delivered(self, channel: NotificationChannel) -> bool:
        """Check if notification was delivered through a channel."""
        status = self.delivery_status.get(channel.value, {})
        return "delivered_at" in status

    def to_websocket_payload(self) -> dict[str, Any]:
        """Convert to WebSocket message payload."""
        return {
            "id": str(self.id),
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "category": self.category,
            "metadata": self.metadata,
            "action_url": self.action_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_read": self.is_read,
        }
