# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for notifications endpoint schemas."""

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.notifications import (
    NotificationResponse,
    NotificationListResponse,
    MarkReadRequest,
    UnreadCountResponse,
)


class TestNotificationSchemas:
    """Tests for notification schemas."""

    def test_notification_response_schema(self):
        """Test NotificationResponse schema."""
        notification = NotificationResponse(
            id="notif-123",
            type="info",
            title="Test Notification",
            message="This is a test",
            priority="normal",
            is_read=False,
            created_at="2025-01-01T00:00:00Z"
        )
        assert notification.id == "notif-123"
        assert notification.type == "info"
        assert notification.title == "Test Notification"
        assert notification.is_read is False

    def test_notification_response_with_optional_fields(self):
        """Test NotificationResponse with optional fields."""
        notification = NotificationResponse(
            id="notif-123",
            type="action",
            title="Action Required",
            message="Please review",
            priority="high",
            data={"action": "approve", "item_id": "123"},
            action_url="/approve/123",
            is_read=True,
            read_at="2025-01-02T00:00:00Z",
            created_at="2025-01-01T00:00:00Z"
        )
        assert notification.data == {"action": "approve", "item_id": "123"}
        assert notification.action_url == "/approve/123"
        assert notification.read_at == "2025-01-02T00:00:00Z"

    def test_notification_list_response_schema(self):
        """Test NotificationListResponse schema."""
        response = NotificationListResponse(
            items=[
                NotificationResponse(
                    id="1",
                    type="info",
                    title="Test",
                    message="Test message",
                    priority="normal",
                    is_read=False,
                    created_at="2025-01-01T00:00:00Z"
                )
            ],
            total=1,
            unread_count=1
        )
        assert len(response.items) == 1
        assert response.total == 1
        assert response.unread_count == 1

    def test_mark_read_request_schema(self):
        """Test MarkReadRequest schema."""
        request = MarkReadRequest(notification_ids=["id1", "id2", "id3"])
        assert len(request.notification_ids) == 3

    def test_mark_read_request_requires_ids(self):
        """Test MarkReadRequest requires at least one ID."""
        with pytest.raises(ValidationError):
            MarkReadRequest(notification_ids=[])

    def test_unread_count_response_schema(self):
        """Test UnreadCountResponse schema."""
        response = UnreadCountResponse(count=5)
        assert response.count == 5

    def test_notification_response_all_fields(self):
        """Test NotificationResponse with all fields."""
        notification = NotificationResponse(
            id="test-id",
            type="warning",
            title="Warning Title",
            message="Warning message",
            priority="high",
            data={"key": "value"},
            action_url="https://example.com/action",
            is_read=True,
            read_at="2025-01-15T10:30:00Z",
            created_at="2025-01-14T10:30:00Z"
        )
        assert notification.priority == "high"
        assert notification.data == {"key": "value"}
        assert notification.action_url == "https://example.com/action"
        assert notification.is_read is True

    def test_notification_list_response_empty(self):
        """Test empty NotificationListResponse."""
        response = NotificationListResponse(
            items=[],
            total=0,
            unread_count=0
        )
        assert len(response.items) == 0
        assert response.total == 0

    def test_mark_read_request_single_id(self):
        """Test MarkReadRequest with single ID."""
        request = MarkReadRequest(notification_ids=["single-id"])
        assert len(request.notification_ids) == 1

    def test_unread_count_response_zero(self):
        """Test UnreadCountResponse with zero count."""
        response = UnreadCountResponse(count=0)
        assert response.count == 0
