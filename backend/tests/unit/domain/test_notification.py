# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for Notification domain entity.

Tests for Notification entity methods and properties.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_system_types(self) -> None:
        """Test system notification types."""
        assert NotificationType.SYSTEM.value == "system"
        assert NotificationType.MAINTENANCE.value == "maintenance"

    def test_user_types(self) -> None:
        """Test user-related notification types."""
        assert NotificationType.WELCOME.value == "welcome"
        assert NotificationType.PASSWORD_CHANGED.value == "password_changed"
        assert NotificationType.LOGIN_ALERT.value == "login_alert"

    def test_chat_types(self) -> None:
        """Test chat notification types."""
        assert NotificationType.NEW_MESSAGE.value == "new_message"
        assert NotificationType.MENTION.value == "mention"

    def test_alert_types(self) -> None:
        """Test alert notification types."""
        assert NotificationType.WARNING.value == "warning"
        assert NotificationType.ERROR.value == "error"
        assert NotificationType.SUCCESS.value == "success"
        assert NotificationType.INFO.value == "info"


class TestNotificationPriority:
    """Tests for NotificationPriority enum."""

    def test_priority_levels(self) -> None:
        """Test all priority levels exist."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


class TestNotificationChannel:
    """Tests for NotificationChannel enum."""

    def test_channel_types(self) -> None:
        """Test all channel types exist."""
        assert NotificationChannel.IN_APP.value == "in_app"
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.PUSH.value == "push"
        assert NotificationChannel.SMS.value == "sms"


class TestNotification:
    """Tests for Notification entity."""

    @pytest.fixture
    def notification(self) -> Notification:
        """Create a sample notification."""
        return Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Test Notification",
            message="This is a test message",
            priority=NotificationPriority.NORMAL,
        )

    def test_default_values(self) -> None:
        """Test notification default values."""
        notification = Notification()

        assert notification.type == NotificationType.INFO
        assert notification.priority == NotificationPriority.NORMAL
        assert notification.is_read is False
        assert notification.channels == [NotificationChannel.IN_APP]

    def test_is_expired_without_expiration(self, notification: Notification) -> None:
        """Test is_expired returns False when no expiration set."""
        notification.expires_at = None

        assert notification.is_expired is False

    def test_is_expired_future_date(self, notification: Notification) -> None:
        """Test is_expired returns False for future date."""
        notification.expires_at = datetime.now(UTC) + timedelta(hours=1)

        assert notification.is_expired is False

    def test_is_expired_past_date(self, notification: Notification) -> None:
        """Test is_expired returns True for past date."""
        notification.expires_at = datetime.now(UTC) - timedelta(hours=1)

        assert notification.is_expired is True

    def test_mark_read(self, notification: Notification) -> None:
        """Test marking notification as read."""
        assert notification.is_read is False
        assert notification.read_at is None

        notification.mark_read()

        assert notification.is_read is True
        assert notification.read_at is not None

    def test_mark_unread(self, notification: Notification) -> None:
        """Test marking notification as unread."""
        notification.mark_read()
        assert notification.is_read is True

        notification.mark_unread()

        assert notification.is_read is False
        assert notification.read_at is None

    def test_mark_action_clicked(self, notification: Notification) -> None:
        """Test marking action as clicked."""
        assert notification.action_clicked is False
        assert notification.action_clicked_at is None

        notification.mark_action_clicked()

        assert notification.action_clicked is True
        assert notification.action_clicked_at is not None

    def test_mark_delivered(self, notification: Notification) -> None:
        """Test marking notification as delivered."""
        notification.mark_delivered(NotificationChannel.EMAIL)

        assert "email" in notification.delivery_status
        assert "delivered_at" in notification.delivery_status["email"]

    def test_mark_sent(self, notification: Notification) -> None:
        """Test marking notification as sent."""
        notification.mark_sent(NotificationChannel.PUSH)

        assert "push" in notification.delivery_status
        assert "sent_at" in notification.delivery_status["push"]

    def test_is_delivered_true(self, notification: Notification) -> None:
        """Test is_delivered returns True when delivered."""
        notification.mark_delivered(NotificationChannel.IN_APP)

        assert notification.is_delivered(NotificationChannel.IN_APP) is True

    def test_is_delivered_false(self, notification: Notification) -> None:
        """Test is_delivered returns False when not delivered."""
        assert notification.is_delivered(NotificationChannel.SMS) is False

    def test_to_websocket_payload(self, notification: Notification) -> None:
        """Test conversion to WebSocket payload."""
        payload = notification.to_websocket_payload()

        assert payload["id"] == str(notification.id)
        assert payload["type"] == notification.type.value
        assert payload["title"] == notification.title
        assert payload["message"] == notification.message
        assert payload["priority"] == notification.priority.value
        assert payload["is_read"] == notification.is_read

    def test_to_websocket_payload_with_category(
        self, notification: Notification
    ) -> None:
        """Test WebSocket payload includes category."""
        notification.category = "security"

        payload = notification.to_websocket_payload()

        assert payload["category"] == "security"

    def test_to_websocket_payload_with_action_url(
        self, notification: Notification
    ) -> None:
        """Test WebSocket payload includes action URL."""
        notification.action_url = "https://example.com/action"

        payload = notification.to_websocket_payload()

        assert payload["action_url"] == "https://example.com/action"
