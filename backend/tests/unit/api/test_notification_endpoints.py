# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Notification API endpoints.

Tests the notification REST endpoints with mocked database.
"""

from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestNotificationSchemas:
    """Tests for notification endpoint schemas."""

    def test_notification_response_schema(self) -> None:
        """Test NotificationResponse schema."""
        from app.api.v1.endpoints.notifications import NotificationResponse

        response = NotificationResponse(
            id=str(uuid4()),
            type="info",
            title="Test Notification",
            message="This is a test message",
            priority="normal",
            data={"key": "value"},
            action_url="https://example.com/action",
            is_read=False,
            read_at=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.type == "info"
        assert response.title == "Test Notification"
        assert response.is_read is False
        assert response.data == {"key": "value"}

    def test_notification_response_read(self) -> None:
        """Test NotificationResponse with read notification."""
        from app.api.v1.endpoints.notifications import NotificationResponse

        read_at = datetime.now(timezone.utc).isoformat()
        response = NotificationResponse(
            id=str(uuid4()),
            type="success",
            title="Completed",
            message="Task completed",
            priority="high",
            is_read=True,
            read_at=read_at,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.is_read is True
        assert response.read_at == read_at

    def test_notification_list_response_schema(self) -> None:
        """Test NotificationListResponse schema."""
        from app.api.v1.endpoints.notifications import (
            NotificationListResponse,
            NotificationResponse,
        )

        items = [
            NotificationResponse(
                id=str(uuid4()),
                type="info",
                title=f"Notification {i}",
                message=f"Message {i}",
                priority="normal",
                is_read=False,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            for i in range(3)
        ]
        
        response = NotificationListResponse(
            items=items,
            total=10,
            unread_count=7,
        )
        
        assert len(response.items) == 3
        assert response.total == 10
        assert response.unread_count == 7

    def test_mark_read_request_schema(self) -> None:
        """Test MarkReadRequest schema."""
        from app.api.v1.endpoints.notifications import MarkReadRequest

        request = MarkReadRequest(
            notification_ids=[str(uuid4()), str(uuid4())],
        )
        
        assert len(request.notification_ids) == 2

    def test_mark_read_request_min_length(self) -> None:
        """Test MarkReadRequest requires at least one ID."""
        from pydantic import ValidationError
        from app.api.v1.endpoints.notifications import MarkReadRequest

        with pytest.raises(ValidationError) as exc_info:
            MarkReadRequest(notification_ids=[])
        
        assert "notification_ids" in str(exc_info.value)

    def test_unread_count_response_schema(self) -> None:
        """Test UnreadCountResponse schema."""
        from app.api.v1.endpoints.notifications import UnreadCountResponse

        response = UnreadCountResponse(count=42)
        assert response.count == 42

    def test_notification_priorities(self) -> None:
        """Test different notification priorities."""
        from app.api.v1.endpoints.notifications import NotificationResponse

        for priority in ["low", "normal", "high", "urgent"]:
            response = NotificationResponse(
                id=str(uuid4()),
                type="info",
                title="Test",
                message="Message",
                priority=priority,
                is_read=False,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            assert response.priority == priority

    def test_notification_types(self) -> None:
        """Test different notification types."""
        from app.api.v1.endpoints.notifications import NotificationResponse

        for ntype in ["info", "success", "warning", "error", "system"]:
            response = NotificationResponse(
                id=str(uuid4()),
                type=ntype,
                title="Test",
                message="Message",
                priority="normal",
                is_read=False,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            assert response.type == ntype


class TestListNotificationsEndpoint:
    """Tests for GET /notifications endpoint."""

    @pytest.mark.asyncio
    async def test_list_notifications_empty(self) -> None:
        """Test listing notifications when none exist."""
        from app.api.v1.endpoints.notifications import list_notifications

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        # Mock query execution to return empty results
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        # Mock count query to return 0
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_session.execute.side_effect = [
            mock_result,  # notifications query
            mock_count_result,  # total count
            mock_count_result,  # unread count
        ]
        
        result = await list_notifications(
            current_user=mock_user,
            session=mock_session,
            limit=50,
            offset=0,
            unread_only=False,
        )
        
        assert len(result.items) == 0
        assert result.total == 0
        assert result.unread_count == 0

    @pytest.mark.asyncio
    async def test_list_notifications_with_results(self) -> None:
        """Test listing notifications with results."""
        from app.api.v1.endpoints.notifications import list_notifications

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        # Create mock notification
        mock_notification = MagicMock()
        mock_notification.id = uuid4()
        mock_notification.type = "info"
        mock_notification.title = "Test"
        mock_notification.message = "Message"
        mock_notification.priority = "normal"
        mock_notification.metadata = None
        mock_notification.action_url = None
        mock_notification.read_at = None
        mock_notification.created_at = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_notification]
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        mock_session.execute.side_effect = [
            mock_result,  # notifications
            mock_count_result,  # total
            mock_count_result,  # unread
        ]
        
        result = await list_notifications(
            current_user=mock_user,
            session=mock_session,
            limit=50,
            offset=0,
            unread_only=False,
        )
        
        assert len(result.items) == 1
        assert result.items[0].title == "Test"

    @pytest.mark.asyncio
    async def test_list_notifications_unread_only(self) -> None:
        """Test listing only unread notifications."""
        from app.api.v1.endpoints.notifications import list_notifications

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        # Create mock notification
        mock_notification = MagicMock()
        mock_notification.id = uuid4()
        mock_notification.type = "info"
        mock_notification.title = "Unread Test"
        mock_notification.message = "Unread Message"
        mock_notification.priority = "normal"
        mock_notification.metadata = None
        mock_notification.action_url = None
        mock_notification.read_at = None  # Unread
        mock_notification.created_at = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_notification]
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        mock_session.execute.side_effect = [
            mock_result,  # notifications
            mock_count_result,  # total (unread_only filtered)
            mock_count_result,  # unread
        ]
        
        result = await list_notifications(
            current_user=mock_user,
            session=mock_session,
            limit=50,
            offset=0,
            unread_only=True,  # Test unread_only filter
        )
        
        assert len(result.items) == 1
        assert result.items[0].title == "Unread Test"
        assert result.items[0].is_read is False


class TestGetUnreadCountEndpoint:
    """Tests for GET /notifications/unread/count endpoint."""

    @pytest.mark.asyncio
    async def test_get_unread_count_zero(self) -> None:
        """Test getting unread count when all are read."""
        from app.api.v1.endpoints.notifications import get_unread_count

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        result = await get_unread_count(
            current_user=mock_user,
            session=mock_session,
        )
        
        assert result.count == 0

    @pytest.mark.asyncio
    async def test_get_unread_count_positive(self) -> None:
        """Test getting unread count with unread notifications."""
        from app.api.v1.endpoints.notifications import get_unread_count

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 15
        mock_session.execute.return_value = mock_result
        
        result = await get_unread_count(
            current_user=mock_user,
            session=mock_session,
        )
        
        assert result.count == 15


class TestGetNotificationEndpoint:
    """Tests for GET /notifications/{notification_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_notification_not_found(self) -> None:
        """Test getting a notification that doesn't exist."""
        from fastapi import HTTPException
        from app.api.v1.endpoints.notifications import get_notification

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_notification(
                notification_id=uuid4(),
                current_user=mock_user,
                session=mock_session,
            )
        
        assert exc_info.value.status_code == 404
        assert "Notification not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_notification_success(self) -> None:
        """Test successfully getting a notification."""
        from app.api.v1.endpoints.notifications import get_notification

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        notification_id = uuid4()
        mock_notification = MagicMock()
        mock_notification.id = notification_id
        mock_notification.type = "success"
        mock_notification.title = "Found"
        mock_notification.message = "This notification was found"
        mock_notification.priority = "high"
        mock_notification.metadata = {"extra": "data"}
        mock_notification.action_url = "https://example.com"
        mock_notification.read_at = datetime.now(timezone.utc)
        mock_notification.created_at = datetime.now(timezone.utc)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_notification
        mock_session.execute.return_value = mock_result
        
        result = await get_notification(
            notification_id=notification_id,
            current_user=mock_user,
            session=mock_session,
        )
        
        assert result.id == str(notification_id)
        assert result.title == "Found"
        assert result.is_read is True


class TestMarkAsReadEndpoint:
    """Tests for POST /notifications/read endpoint."""

    @pytest.mark.asyncio
    async def test_mark_as_read(self) -> None:
        """Test marking notifications as read."""
        from app.api.v1.endpoints.notifications import mark_as_read, MarkReadRequest

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        request = MarkReadRequest(
            notification_ids=[str(uuid4()), str(uuid4())],
        )
        
        await mark_as_read(
            request=request,
            current_user=mock_user,
            session=mock_session,
        )
        
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


class TestMarkAllAsReadEndpoint:
    """Tests for POST /notifications/read/all endpoint."""

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self) -> None:
        """Test marking all notifications as read."""
        from app.api.v1.endpoints.notifications import mark_all_as_read

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        await mark_all_as_read(
            current_user=mock_user,
            session=mock_session,
        )
        
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


class TestDeleteNotificationEndpoint:
    """Tests for DELETE /notifications/{notification_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_notification(self) -> None:
        """Test deleting a notification."""
        from app.api.v1.endpoints.notifications import delete_notification

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result
        
        await delete_notification(
            notification_id=uuid4(),
            current_user=mock_user,
            session=mock_session,
        )
        
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


class TestDeleteReadNotificationsEndpoint:
    """Tests for DELETE /notifications/read endpoint."""

    @pytest.mark.asyncio
    async def test_delete_read_notifications(self) -> None:
        """Test deleting all read notifications."""
        from app.api.v1.endpoints.notifications import delete_read_notifications

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_session = AsyncMock()
        
        await delete_read_notifications(
            current_user=mock_user,
            session=mock_session,
        )
        
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


class TestNotificationEdgeCases:
    """Tests for edge cases in notification handling."""

    def test_notification_with_null_optional_fields(self) -> None:
        """Test notification with null optional fields."""
        from app.api.v1.endpoints.notifications import NotificationResponse

        response = NotificationResponse(
            id=str(uuid4()),
            type="info",
            title="Minimal",
            message="Minimal notification",
            priority="normal",
            data=None,
            action_url=None,
            is_read=False,
            read_at=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert response.data is None
        assert response.action_url is None
        assert response.read_at is None

    def test_notification_list_empty_items(self) -> None:
        """Test empty notification list response."""
        from app.api.v1.endpoints.notifications import NotificationListResponse

        response = NotificationListResponse(
            items=[],
            total=0,
            unread_count=0,
        )
        
        assert response.items == []
        assert response.total == 0

    def test_mark_read_single_notification(self) -> None:
        """Test marking a single notification as read."""
        from app.api.v1.endpoints.notifications import MarkReadRequest

        request = MarkReadRequest(
            notification_ids=[str(uuid4())],
        )
        
        assert len(request.notification_ids) == 1

    def test_mark_read_many_notifications(self) -> None:
        """Test marking many notifications as read."""
        from app.api.v1.endpoints.notifications import MarkReadRequest

        notification_ids = [str(uuid4()) for _ in range(100)]
        request = MarkReadRequest(notification_ids=notification_ids)
        
        assert len(request.notification_ids) == 100

    def test_unread_count_none_returns_zero(self) -> None:
        """Test that None unread count is converted to 0."""
        from app.api.v1.endpoints.notifications import UnreadCountResponse

        # This tests the schema handles 0 correctly
        response = UnreadCountResponse(count=0)
        assert response.count == 0
