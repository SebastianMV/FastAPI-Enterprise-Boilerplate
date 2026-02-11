# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for NotificationService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.services.notification_service import NotificationService
from app.domain.entities.notification import (
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_ws_manager():
    """Create a mock WebSocket manager."""
    ws_manager = AsyncMock()
    ws_manager.send_to_user = AsyncMock(return_value=1)
    return ws_manager


@pytest.fixture
def notification_service(mock_session, mock_ws_manager):
    """Create NotificationService instance."""
    return NotificationService(session=mock_session, ws_manager=mock_ws_manager)


@pytest.fixture
def notification_service_no_ws(mock_session):
    """Create NotificationService without WebSocket."""
    return NotificationService(session=mock_session, ws_manager=None)


class TestNotificationServiceInit:
    """Tests for NotificationService initialization."""

    def test_init_with_ws_manager(self, mock_session, mock_ws_manager):
        """Test initialization with WebSocket manager."""
        service = NotificationService(session=mock_session, ws_manager=mock_ws_manager)
        assert service._session == mock_session
        assert service._ws_manager == mock_ws_manager

    def test_init_without_ws_manager(self, mock_session):
        """Test initialization without WebSocket manager."""
        service = NotificationService(session=mock_session, ws_manager=None)
        assert service._ws_manager is None


class TestCreateNotification:
    """Tests for create_notification method."""

    @pytest.mark.asyncio
    async def test_create_notification_minimal(
        self, notification_service, mock_session
    ):
        """Test creating notification with minimal parameters."""
        user_id = uuid4()

        result = await notification_service.create_notification(
            user_id=user_id,
            type=NotificationType.INFO,
            title="Test Title",
            message="Test message",
        )

        assert result is not None
        assert result.user_id == user_id
        assert result.title == "Test Title"
        assert result.message == "Test message"
        assert result.type == NotificationType.INFO
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_notification_with_all_params(
        self, notification_service, mock_session
    ):
        """Test creating notification with all parameters."""
        user_id = uuid4()
        tenant_id = uuid4()
        expires = datetime.now(UTC)

        result = await notification_service.create_notification(
            user_id=user_id,
            type=NotificationType.WARNING,
            title="Warning",
            message="This is a warning",
            tenant_id=tenant_id,
            priority=NotificationPriority.HIGH,
            category="system",
            metadata={"key": "value"},
            action_url="/action",
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            expires_at=expires,
            group_key="group-1",
        )

        assert result.priority == NotificationPriority.HIGH
        assert result.category == "system"
        assert result.metadata == {"key": "value"}
        assert result.action_url == "/action"

    @pytest.mark.asyncio
    async def test_create_notification_delivers_via_websocket(
        self, notification_service, mock_ws_manager
    ):
        """Test notification is delivered via WebSocket."""
        user_id = uuid4()

        await notification_service.create_notification(
            user_id=user_id,
            type=NotificationType.INFO,
            title="Test",
            message="Message",
            channels=[NotificationChannel.IN_APP],
        )

        mock_ws_manager.send_to_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_notification_no_ws_delivery_without_manager(
        self, notification_service_no_ws
    ):
        """Test notification without WebSocket manager doesn't fail."""
        user_id = uuid4()

        result = await notification_service_no_ws.create_notification(
            user_id=user_id, type=NotificationType.INFO, title="Test", message="Message"
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_notification_default_priority(self, notification_service):
        """Test default priority is NORMAL."""
        user_id = uuid4()

        result = await notification_service.create_notification(
            user_id=user_id, type=NotificationType.INFO, title="Test", message="Message"
        )

        assert result.priority == NotificationPriority.NORMAL


class TestNotificationTypes:
    """Tests for different notification types."""

    @pytest.mark.asyncio
    async def test_info_notification(self, notification_service):
        """Test INFO notification type."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Info",
            message="Info message",
        )
        assert result.type == NotificationType.INFO

    @pytest.mark.asyncio
    async def test_warning_notification(self, notification_service):
        """Test WARNING notification type."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.WARNING,
            title="Warning",
            message="Warning message",
        )
        assert result.type == NotificationType.WARNING

    @pytest.mark.asyncio
    async def test_error_notification(self, notification_service):
        """Test ERROR notification type."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.ERROR,
            title="Error",
            message="Error message",
        )
        assert result.type == NotificationType.ERROR

    @pytest.mark.asyncio
    async def test_success_notification(self, notification_service):
        """Test SUCCESS notification type."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.SUCCESS,
            title="Success",
            message="Success message",
        )
        assert result.type == NotificationType.SUCCESS


class TestNotificationPriorities:
    """Tests for different notification priorities."""

    @pytest.mark.asyncio
    async def test_low_priority(self, notification_service):
        """Test LOW priority."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Test",
            message="Message",
            priority=NotificationPriority.LOW,
        )
        assert result.priority == NotificationPriority.LOW

    @pytest.mark.asyncio
    async def test_high_priority(self, notification_service):
        """Test HIGH priority."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Test",
            message="Message",
            priority=NotificationPriority.HIGH,
        )
        assert result.priority == NotificationPriority.HIGH

    @pytest.mark.asyncio
    async def test_urgent_priority(self, notification_service):
        """Test URGENT priority."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Test",
            message="Message",
            priority=NotificationPriority.URGENT,
        )
        assert result.priority == NotificationPriority.URGENT


class TestNotificationChannels:
    """Tests for different notification channels."""

    @pytest.mark.asyncio
    async def test_in_app_channel(self, notification_service, mock_ws_manager):
        """Test IN_APP channel triggers WebSocket delivery."""
        await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Test",
            message="Message",
            channels=[NotificationChannel.IN_APP],
        )
        mock_ws_manager.send_to_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_channel_no_ws_delivery(
        self, notification_service, mock_ws_manager
    ):
        """Test EMAIL only channel doesn't trigger WebSocket."""
        await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Test",
            message="Message",
            channels=[NotificationChannel.EMAIL],
        )
        mock_ws_manager.send_to_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_channels(self, notification_service):
        """Test multiple channels."""
        result = await notification_service.create_notification(
            user_id=uuid4(),
            type=NotificationType.INFO,
            title="Test",
            message="Message",
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
        )
        assert NotificationChannel.IN_APP in result.channels
        assert NotificationChannel.EMAIL in result.channels
