# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for Notification Service.

Tests for notification creation and delivery.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
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

    def test_priority_values(self) -> None:
        """Test priority values."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"

    def test_priority_comparison(self) -> None:
        """Test priority comparison."""
        # Enum comparisons work by identity
        assert NotificationPriority.LOW != NotificationPriority.HIGH
        assert NotificationPriority.URGENT == NotificationPriority.URGENT


class TestNotificationChannel:
    """Tests for NotificationChannel enum."""

    def test_channel_values(self) -> None:
        """Test channel values."""
        assert NotificationChannel.IN_APP.value == "in_app"
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.PUSH.value == "push"
        assert NotificationChannel.SMS.value == "sms"


class TestNotificationEntity:
    """Tests for Notification entity."""

    def test_create_notification(self) -> None:
        """Test creating a notification entity."""
        user_id = uuid4()
        tenant_id = uuid4()

        notification = Notification(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            type=NotificationType.INFO,
            title="Test Notification",
            message="This is a test message",
        )

        assert notification.user_id == user_id
        assert notification.tenant_id == tenant_id
        assert notification.type == NotificationType.INFO
        assert notification.title == "Test Notification"

    def test_notification_with_priority(self) -> None:
        """Test notification with priority."""
        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.WARNING,
            title="Warning",
            message="Important warning",
            priority=NotificationPriority.HIGH,
        )

        assert notification.priority == NotificationPriority.HIGH

    def test_notification_with_channels(self) -> None:
        """Test notification with multiple channels."""
        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.SYSTEM,
            title="System Update",
            message="System maintenance scheduled",
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
        )

        assert NotificationChannel.IN_APP in notification.channels
        assert NotificationChannel.EMAIL in notification.channels

    def test_notification_with_action_url(self) -> None:
        """Test notification with action URL."""
        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.NEW_MESSAGE,
            title="New Message",
            message="You have a new message",
            action_url="/chat/conversation/123",
        )

        assert notification.action_url == "/chat/conversation/123"

    def test_notification_with_metadata(self) -> None:
        """Test notification with metadata."""
        metadata = {"sender_id": str(uuid4()), "conversation_id": "conv-123"}

        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.MENTION,
            title="You were mentioned",
            message="@user mentioned you in a conversation",
            metadata=metadata,
        )

        assert notification.metadata == metadata
        assert "sender_id" in notification.metadata


class TestNotificationDelivery:
    """Tests for notification delivery status."""

    def test_notification_default_not_read(self) -> None:
        """Test that notification is not read by default."""
        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Info",
            message="Information",
        )

        assert notification.is_read is False

    def test_notification_mark_as_read(self) -> None:
        """Test marking notification as read."""
        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Info",
            message="Information",
        )

        notification.mark_read()

        assert notification.is_read is True
        assert notification.read_at is not None

    def test_notification_mark_delivered(self) -> None:
        """Test marking notification as delivered."""
        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Info",
            message="Information",
            channels=[NotificationChannel.IN_APP],
        )

        notification.mark_delivered(NotificationChannel.IN_APP)

        assert NotificationChannel.IN_APP.value in notification.delivery_status
        assert (
            notification.delivery_status[NotificationChannel.IN_APP.value] is not None
        )

    def test_notification_expiration(self) -> None:
        """Test notification with expiration."""
        expires = datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC)

        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.SYSTEM,
            title="Temporary Notice",
            message="This expires soon",
            expires_at=expires,
        )

        assert notification.expires_at == expires


class TestNotificationGrouping:
    """Tests for notification grouping."""

    def test_notification_with_group_key(self) -> None:
        """Test notification with group key."""
        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.NEW_MESSAGE,
            title="New Message",
            message="Message from user",
            group_key="chat:conversation:123",
        )

        assert notification.group_key == "chat:conversation:123"

    def test_notification_with_category(self) -> None:
        """Test notification with category."""
        notification = Notification(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=uuid4(),
            type=NotificationType.COMMENT,
            title="New Comment",
            message="Someone commented on your post",
            category="social",
        )

        assert notification.category == "social"


# =========================================
# NotificationService Unit Tests
# =========================================


class TestNotificationServiceInit:
    """Tests for NotificationService initialization."""

    def test_init_with_session_only(self) -> None:
        """Test NotificationService can be initialized with session only."""
        from app.application.services.notification_service import NotificationService

        mock_session = AsyncMock()
        service = NotificationService(session=mock_session)

        assert service._session == mock_session
        assert service._ws_manager is None

    def test_init_with_ws_manager(self) -> None:
        """Test NotificationService can be initialized with WebSocket manager."""
        from app.application.services.notification_service import NotificationService

        mock_session = AsyncMock()
        mock_ws = MagicMock()
        service = NotificationService(session=mock_session, ws_manager=mock_ws)

        assert service._session == mock_session
        assert service._ws_manager == mock_ws


class TestNotificationServiceCreate:
    """Tests for NotificationService create methods."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def notification_service(self, mock_session: AsyncMock):
        """Create NotificationService with mock session."""
        from app.application.services.notification_service import NotificationService

        return NotificationService(session=mock_session)

    @pytest.mark.asyncio
    async def test_create_notification_basic(
        self, notification_service, mock_session: AsyncMock
    ) -> None:
        """Test creating a basic notification."""
        user_id = uuid4()
        tenant_id = uuid4()

        result = await notification_service.create_notification(
            user_id=user_id,
            type=NotificationType.INFO,
            title="Test Notification",
            message="This is a test",
            tenant_id=tenant_id,
        )

        assert result.user_id == user_id
        assert result.tenant_id == tenant_id
        assert result.type == NotificationType.INFO
        assert result.title == "Test Notification"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_create_notification_with_priority(
        self, notification_service, mock_session: AsyncMock
    ) -> None:
        """Test creating a notification with high priority."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.WARNING,
            title="Important",
            message="High priority message",
            priority=NotificationPriority.HIGH,
        )

        assert result.priority == NotificationPriority.HIGH

    @pytest.mark.asyncio
    async def test_create_notification_with_channels(
        self, notification_service, mock_session: AsyncMock
    ) -> None:
        """Test creating a notification with multiple channels."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.SYSTEM,
            title="System Alert",
            message="Multi-channel notification",
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
        )

        assert NotificationChannel.IN_APP in result.channels
        assert NotificationChannel.EMAIL in result.channels

    @pytest.mark.asyncio
    async def test_create_notification_with_metadata(
        self, notification_service, mock_session: AsyncMock
    ) -> None:
        """Test creating a notification with metadata."""
        metadata = {"key": "value", "count": 42}

        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="With Metadata",
            message="Has extra data",
            metadata=metadata,
        )

        assert result.metadata == metadata

    @pytest.mark.asyncio
    async def test_create_notification_with_action_url(
        self, notification_service, mock_session: AsyncMock
    ) -> None:
        """Test creating a notification with action URL."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.NEW_MESSAGE,
            title="New Message",
            message="Check your inbox",
            action_url="/messages/inbox",
        )

        assert result.action_url == "/messages/inbox"
