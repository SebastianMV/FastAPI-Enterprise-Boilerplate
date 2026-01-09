# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for background task queue."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.tasks.queue import (
    TaskPriority,
    TaskResult,
    TaskStatus,
    cleanup_expired_tokens_task,
    process_webhook_task,
    send_email_task,
)


class TestTaskPriority:
    """Tests for task priority enum."""

    def test_priority_values(self):
        """Priority values should be ordered correctly."""
        assert TaskPriority.LOW.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.CRITICAL.value

    def test_all_priorities_exist(self):
        """All priority levels should exist."""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.CRITICAL.value == 4


class TestTaskStatus:
    """Tests for task status enum."""

    def test_status_values(self):
        """Status values should exist."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.SUCCESS.value == "success"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestTaskResult:
    """Tests for task result class."""

    def test_create_success_result(self):
        """Should create successful result."""
        result = TaskResult(
            task_id="task-123",
            status=TaskStatus.SUCCESS,
            result={"data": "value"},
            error=None,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        assert result.task_id == "task-123"
        assert result.status == TaskStatus.SUCCESS
        assert result.result == {"data": "value"}
        assert result.error is None

    def test_create_failed_result(self):
        """Should create failed result."""
        result = TaskResult(
            task_id="task-123",
            status=TaskStatus.FAILED,
            result=None,
            error="Task failed: Connection timeout",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        assert result.status == TaskStatus.FAILED
        assert "Connection timeout" in result.error

    def test_duration_property(self):
        """Should calculate duration correctly."""
        started = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2025, 1, 1, 10, 5, 0, tzinfo=UTC)
        
        result = TaskResult(
            task_id="task-123",
            status=TaskStatus.SUCCESS,
            started_at=started,
            completed_at=completed,
        )
        
        assert result.duration is not None
        assert result.duration.total_seconds() == 300  # 5 minutes


class TestSendEmailTask:
    """Tests for email sending task."""

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Should send email successfully."""
        result = await send_email_task(
            {},  # ctx
            to="test@example.com",
            subject="Test Subject",
            body="Test body",
        )

        assert result["status"] == "sent"
        assert result["to"] == "test@example.com"
        assert "sent_at" in result

    @pytest.mark.asyncio
    async def test_send_email_with_template_id(self):
        """Should send email with template ID."""
        result = await send_email_task(
            {},
            to="test@example.com",
            subject="Welcome!",
            body="Welcome body",
            template_id="welcome-template",
        )

        assert result["status"] == "sent"


class TestProcessWebhookTask:
    """Tests for webhook processing task."""

    @pytest.mark.asyncio
    async def test_process_webhook_success(self):
        """Should process webhook successfully."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = '{"received": true}'

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            result = await process_webhook_task(
                {},
                webhook_url="https://example.com/webhook",
                payload={"event": "user.created"},
            )

            assert result["status"] == "sent"
            assert result["response_status"] == 200

    @pytest.mark.asyncio
    async def test_process_webhook_with_headers(self):
        """Should include custom headers."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = '{"ok": true}'

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            result = await process_webhook_task(
                {},
                webhook_url="https://example.com/webhook",
                payload={"event": "test"},
                headers={"X-Custom-Header": "value"},
            )

            assert result["status"] == "sent"


class TestCleanupExpiredTokensTask:
    """Tests for token cleanup task."""

    @pytest.mark.asyncio
    async def test_cleanup_returns_count(self):
        """Should return count of cleaned tokens."""
        result = await cleanup_expired_tokens_task({})

        assert "deleted_count" in result
        assert isinstance(result["deleted_count"], int)

    @pytest.mark.asyncio
    async def test_cleanup_returns_status(self):
        """Should return completed status."""
        result = await cleanup_expired_tokens_task({})

        assert result["status"] == "completed"
        assert "completed_at" in result
