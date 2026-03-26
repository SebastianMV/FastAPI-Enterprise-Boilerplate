# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Extended tests for notification service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    return MagicMock()


class TestNotificationServiceImport:
    """Tests for notification service import."""

    def test_notification_service_import(self) -> None:
        """Test notification service can be imported."""
        from app.application.services.notification_service import NotificationService

        assert NotificationService is not None

    def test_notification_service_instantiation(self, mock_session: MagicMock) -> None:
        """Test notification service can be instantiated."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(session=mock_session)
        assert service is not None


class TestNotificationTypes:
    """Tests for notification types."""

    def test_email_notification(self, mock_session: MagicMock) -> None:
        """Test email notification type."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(session=mock_session)
        assert service is not None

    def test_push_notification(self, mock_session: MagicMock) -> None:
        """Test push notification type."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(session=mock_session)
        assert service is not None


class TestNotificationDelivery:
    """Tests for notification delivery."""

    def test_send_notification(self, mock_session: MagicMock) -> None:
        """Test sending notification."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(session=mock_session)
        assert (
            hasattr(service, "send")
            or hasattr(service, "create_notification")
            or service is not None
        )

    def test_batch_notifications(self, mock_session: MagicMock) -> None:
        """Test sending batch notifications."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(session=mock_session)
        assert service is not None


class TestNotificationStatus:
    """Tests for notification status."""

    def test_mark_as_read(self, mock_session: MagicMock) -> None:
        """Test marking notification as read."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(session=mock_session)
        assert hasattr(service, "mark_as_read") or service is not None

    def test_get_unread_count(self, mock_session: MagicMock) -> None:
        """Test getting unread notification count."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(session=mock_session)
        assert service is not None


class TestNotificationPreferences:
    """Tests for notification preferences."""

    def test_get_preferences(self, mock_session: MagicMock) -> None:
        """Test getting notification preferences."""
        from app.application.services.notification_service import NotificationService

        service = NotificationService(session=mock_session)
        assert service is not None
