# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Additional notification service tests for coverage improvement.

Tests convenience methods and edge cases.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_ws_manager():
    """Create mock WebSocket manager."""
    manager = AsyncMock()
    manager.send_to_user = AsyncMock(return_value=1)
    return manager


class TestNotificationServiceConvenienceMethods:
    """Test convenience notification methods."""

    @pytest.mark.asyncio
    async def test_notify_welcome(self, mock_session, mock_ws_manager):
        """Test notify_welcome creates correct notification."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session, mock_ws_manager)

        user_id = uuid4()
        tenant_id = uuid4()

        # Mock the create method
        with patch.object(
            service, "create_notification", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(spec=Notification)

            result = await service.notify_welcome(user_id, tenant_id)

            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["user_id"] == user_id
            assert call_kwargs["tenant_id"] == tenant_id
            assert call_kwargs["type"] == NotificationType.WELCOME
            assert "Welcome" in call_kwargs["title"]

    @pytest.mark.asyncio
    async def test_notify_password_changed(self, mock_session, mock_ws_manager):
        """Test notify_password_changed creates security notification."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session, mock_ws_manager)

        user_id = uuid4()

        with patch.object(
            service, "create_notification", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(spec=Notification)

            result = await service.notify_password_changed(user_id)

            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["user_id"] == user_id
            assert call_kwargs["type"] == NotificationType.PASSWORD_CHANGED
            assert call_kwargs["priority"] == NotificationPriority.HIGH
            assert call_kwargs["category"] == "security"

    @pytest.mark.asyncio
    async def test_notify_login_alert_with_location(
        self, mock_session, mock_ws_manager
    ):
        """Test notify_login_alert with location."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session, mock_ws_manager)

        user_id = uuid4()
        ip_address = "192.168.1.1"
        location = "New York, US"

        with patch.object(
            service, "create_notification", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(spec=Notification)

            result = await service.notify_login_alert(user_id, ip_address, location)

            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert ip_address in call_kwargs["message"]
            assert location in call_kwargs["message"]
            assert call_kwargs["metadata"]["ip_address"] == ip_address
            assert call_kwargs["metadata"]["location"] == location

    @pytest.mark.asyncio
    async def test_notify_login_alert_without_location(self, mock_session):
        """Test notify_login_alert without location."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        user_id = uuid4()
        ip_address = "10.0.0.1"

        with patch.object(
            service, "create_notification", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(spec=Notification)

            result = await service.notify_login_alert(user_id, ip_address)

            call_kwargs = mock_create.call_args.kwargs
            assert ip_address in call_kwargs["message"]
            assert call_kwargs["metadata"]["location"] is None

    @pytest.mark.asyncio
    async def test_notify_mention(self, mock_session, mock_ws_manager):
        """Test notify_mention creates mention notification."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session, mock_ws_manager)

        user_id = uuid4()
        mentioned_by = "John Doe"
        context = "a conversation"
        action_url = "/chat/123"

        with patch.object(
            service, "create_notification", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = MagicMock(spec=Notification)

            result = await service.notify_mention(
                user_id=user_id,
                mentioned_by=mentioned_by,
                context=context,
                action_url=action_url,
            )

            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["type"] == NotificationType.MENTION
            assert mentioned_by in call_kwargs["message"]
            assert context in call_kwargs["message"]
            assert call_kwargs["action_url"] == action_url


class TestNotificationServiceGetOperations:
    """Test notification get operations."""

    @pytest.mark.asyncio
    async def test_get_notification_found(self, mock_session):
        """Test get_notification when notification exists."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        notification_id = uuid4()
        user_id = uuid4()

        # Create mock model
        mock_model = MagicMock()
        mock_model.id = notification_id
        mock_model.tenant_id = uuid4()
        mock_model.user_id = user_id
        mock_model.type = NotificationType.SYSTEM.value
        mock_model.title = "Test"
        mock_model.message = "Test message"
        mock_model.metadata = {}
        mock_model.priority = NotificationPriority.NORMAL.value
        mock_model.category = None
        mock_model.channels = [NotificationChannel.IN_APP.value]
        mock_model.delivery_status = {}
        mock_model.is_read = False
        mock_model.read_at = None
        mock_model.expires_at = None
        mock_model.group_key = None
        mock_model.action_url = None
        mock_model.action_clicked = False
        mock_model.action_clicked_at = None
        mock_model.created_at = datetime.now(UTC)
        mock_model.updated_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_model)
        mock_session.execute.return_value = mock_result

        result = await service.get_notification(notification_id, user_id)

        assert result is not None
        assert result.title == "Test"

    @pytest.mark.asyncio
    async def test_get_notification_not_found(self, mock_session):
        """Test get_notification when notification not exists."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await service.get_notification(uuid4(), uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_notifications_empty(self, mock_session):
        """Test get_user_notifications with no results."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        mock_session.execute.return_value = mock_result

        result = await service.get_user_notifications(uuid4())

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_notifications_with_filters(self, mock_session):
        """Test get_user_notifications with unread_only and category."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        mock_session.execute.return_value = mock_result

        result = await service.get_user_notifications(
            uuid4(),
            unread_only=True,
            category="security",
            limit=10,
            offset=5,
        )

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_unread_count(self, mock_session):
        """Test get_unread_count."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_result

        result = await service.get_unread_count(uuid4())

        assert result == 5

    @pytest.mark.asyncio
    async def test_get_unread_count_with_category(self, mock_session):
        """Test get_unread_count with category filter."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=3)
        mock_session.execute.return_value = mock_result

        result = await service.get_unread_count(uuid4(), category="security")

        assert result == 3

    @pytest.mark.asyncio
    async def test_get_unread_count_none_result(self, mock_session):
        """Test get_unread_count when scalar returns None."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await service.get_unread_count(uuid4())

        assert result == 0


class TestNotificationServiceUpdateOperations:
    """Test notification update operations."""

    @pytest.mark.asyncio
    async def test_mark_as_read_success(self, mock_session):
        """Test mark_as_read successfully marks notification."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await service.mark_as_read(uuid4(), uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_mark_as_read_not_found(self, mock_session):
        """Test mark_as_read when notification not found."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await service.mark_as_read(uuid4(), uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, mock_session):
        """Test mark_all_as_read returns count."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 10
        mock_session.execute.return_value = mock_result

        result = await service.mark_all_as_read(uuid4())

        assert result == 10

    @pytest.mark.asyncio
    async def test_mark_all_as_read_with_category(self, mock_session):
        """Test mark_all_as_read with category filter."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        result = await service.mark_all_as_read(uuid4(), category="security")

        assert result == 5

    @pytest.mark.asyncio
    async def test_delete_notification_success(self, mock_session):
        """Test delete_notification successfully deletes."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await service.delete_notification(uuid4(), uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_notification_not_found(self, mock_session):
        """Test delete_notification when not found."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await service.delete_notification(uuid4(), uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_all_read(self, mock_session):
        """Test delete_all_read returns count."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session)

        mock_result = MagicMock()
        mock_result.rowcount = 7
        mock_session.execute.return_value = mock_result

        result = await service.delete_all_read(uuid4())

        assert result == 7


class TestNotificationServiceDelivery:
    """Test notification delivery."""

    @pytest.mark.asyncio
    async def test_deliver_via_websocket_no_manager(self, mock_session):
        """Test _deliver_via_websocket when no manager."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session, ws_manager=None)

        notification = MagicMock(spec=Notification)

        # Should not raise - just return early
        await service._deliver_via_websocket(notification)

    @pytest.mark.asyncio
    async def test_deliver_via_websocket_success(self, mock_session, mock_ws_manager):
        """Test _deliver_via_websocket successful delivery."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session, mock_ws_manager)

        notification = MagicMock(spec=Notification)
        notification.id = uuid4()
        notification.user_id = uuid4()
        notification.to_websocket_payload = MagicMock(return_value={"test": "data"})
        notification.mark_delivered = MagicMock()
        notification.delivery_status = {"in_app": True}

        mock_ws_manager.send_to_user.return_value = 1

        await service._deliver_via_websocket(notification)

        mock_ws_manager.send_to_user.assert_called_once()
        notification.mark_delivered.assert_called_once_with(NotificationChannel.IN_APP)

    @pytest.mark.asyncio
    async def test_deliver_via_websocket_no_connections(
        self, mock_session, mock_ws_manager
    ):
        """Test _deliver_via_websocket when no connections."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(mock_session, mock_ws_manager)

        notification = MagicMock(spec=Notification)
        notification.user_id = uuid4()
        notification.to_websocket_payload = MagicMock(return_value={})
        notification.mark_delivered = MagicMock()

        mock_ws_manager.send_to_user.return_value = 0  # No connections

        await service._deliver_via_websocket(notification)

        # Should not mark as delivered
        notification.mark_delivered.assert_not_called()
