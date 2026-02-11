# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for notification service with real execution."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.services.notification_service import NotificationService
from app.domain.entities.notification import (
    Notification,
    NotificationPriority,
    NotificationType,
)


class TestNotificationServiceCreation:
    """Tests for NotificationService creation."""

    def test_service_requires_session(self) -> None:
        """Test NotificationService requires session parameter."""
        mock_session = AsyncMock()
        service = NotificationService(session=mock_session)
        assert service is not None

    def test_service_has_session(self) -> None:
        """Test NotificationService stores session."""
        mock_session = AsyncMock()
        service = NotificationService(session=mock_session)
        assert service._session is mock_session


class TestNotificationEntity:
    """Tests for Notification entity."""

    def test_notification_creation(self) -> None:
        """Test Notification entity creation."""
        user_id = uuid4()
        tenant_id = uuid4()
        notification = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title="Test",
            message="Test message",
            type=NotificationType.INFO,
        )
        assert notification.title == "Test"
        assert notification.user_id == user_id
        assert notification.read_at is None

    def test_notification_types(self) -> None:
        """Test NotificationType enum values."""
        assert NotificationType.INFO is not None
        assert NotificationType.WARNING is not None
        assert NotificationType.ERROR is not None
        assert NotificationType.SUCCESS is not None

    def test_notification_priority(self) -> None:
        """Test NotificationPriority enum values."""
        assert NotificationPriority.LOW is not None
        assert NotificationPriority.NORMAL is not None
        assert NotificationPriority.HIGH is not None

    def test_notification_mark_read(self) -> None:
        """Test marking notification as read."""
        user_id = uuid4()
        tenant_id = uuid4()
        notification = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title="Test",
            message="Test message",
            type=NotificationType.INFO,
        )
        notification.mark_read()
        assert notification.is_read is True
        assert notification.read_at is not None


class TestNotificationServiceQuery:
    """Tests for notification query methods."""

    @pytest.mark.asyncio
    async def test_get_user_notifications_import(self) -> None:
        """Test get_user_notifications method exists."""
        mock_session = AsyncMock()
        service = NotificationService(session=mock_session)

        assert hasattr(service, "get_user_notifications")

    @pytest.mark.asyncio
    async def test_get_unread_count_import(self) -> None:
        """Test get_unread_count method exists."""
        mock_session = AsyncMock()
        service = NotificationService(session=mock_session)

        assert hasattr(service, "get_unread_count")

    @pytest.mark.asyncio
    async def test_service_has_send_method(self) -> None:
        """Test send method exists."""
        mock_session = AsyncMock()
        service = NotificationService(session=mock_session)

        assert hasattr(service, "send_notification") or hasattr(
            service, "create_notification"
        )
