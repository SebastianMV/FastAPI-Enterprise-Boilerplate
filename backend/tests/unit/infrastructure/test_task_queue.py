# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for task queue infrastructure.

Tests for task queue data structures and utilities.
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock

import pytest

from app.infrastructure.tasks.queue import (
    TaskPriority,
    TaskStatus,
    TaskResult,
    get_redis_settings,
)


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_low_priority(self) -> None:
        """Test LOW priority value."""
        assert TaskPriority.LOW.value == 1

    def test_normal_priority(self) -> None:
        """Test NORMAL priority value."""
        assert TaskPriority.NORMAL.value == 2

    def test_high_priority(self) -> None:
        """Test HIGH priority value."""
        assert TaskPriority.HIGH.value == 3

    def test_critical_priority(self) -> None:
        """Test CRITICAL priority value."""
        assert TaskPriority.CRITICAL.value == 4

    def test_priority_ordering(self) -> None:
        """Test priority values are ordered correctly."""
        assert TaskPriority.LOW.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.CRITICAL.value


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_pending_status(self) -> None:
        """Test PENDING status value."""
        assert TaskStatus.PENDING.value == "pending"

    def test_running_status(self) -> None:
        """Test RUNNING status value."""
        assert TaskStatus.RUNNING.value == "running"

    def test_success_status(self) -> None:
        """Test SUCCESS status value."""
        assert TaskStatus.SUCCESS.value == "success"

    def test_failed_status(self) -> None:
        """Test FAILED status value."""
        assert TaskStatus.FAILED.value == "failed"

    def test_cancelled_status(self) -> None:
        """Test CANCELLED status value."""
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_create_pending_result(self) -> None:
        """Test creating pending task result."""
        result = TaskResult(
            task_id="task_123",
            status=TaskStatus.PENDING,
        )
        
        assert result.task_id == "task_123"
        assert result.status == TaskStatus.PENDING
        assert result.result is None
        assert result.error is None

    def test_create_success_result(self) -> None:
        """Test creating successful task result."""
        started = datetime.now(UTC)
        completed = started + timedelta(seconds=5)
        
        result = TaskResult(
            task_id="task_456",
            status=TaskStatus.SUCCESS,
            result={"processed": 100},
            started_at=started,
            completed_at=completed,
        )
        
        assert result.status == TaskStatus.SUCCESS
        assert result.result == {"processed": 100}
        assert result.error is None

    def test_create_failed_result(self) -> None:
        """Test creating failed task result."""
        result = TaskResult(
            task_id="task_789",
            status=TaskStatus.FAILED,
            error="Connection timeout",
            started_at=datetime.now(UTC),
        )
        
        assert result.status == TaskStatus.FAILED
        assert result.error == "Connection timeout"
        assert result.result is None

    def test_duration_with_timestamps(self) -> None:
        """Test duration calculation with timestamps."""
        started = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        completed = datetime(2025, 1, 1, 12, 0, 10, tzinfo=UTC)
        
        result = TaskResult(
            task_id="task_abc",
            status=TaskStatus.SUCCESS,
            started_at=started,
            completed_at=completed,
        )
        
        assert result.duration == timedelta(seconds=10)

    def test_duration_without_started_at(self) -> None:
        """Test duration is None without started_at."""
        result = TaskResult(
            task_id="task_def",
            status=TaskStatus.SUCCESS,
            completed_at=datetime.now(UTC),
        )
        
        assert result.duration is None

    def test_duration_without_completed_at(self) -> None:
        """Test duration is None without completed_at."""
        result = TaskResult(
            task_id="task_ghi",
            status=TaskStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        
        assert result.duration is None

    def test_duration_without_timestamps(self) -> None:
        """Test duration is None without any timestamps."""
        result = TaskResult(
            task_id="task_jkl",
            status=TaskStatus.PENDING,
        )
        
        assert result.duration is None


class TestGetRedisSettings:
    """Tests for get_redis_settings function."""

    def test_returns_redis_settings(self) -> None:
        """Test that get_redis_settings returns RedisSettings."""
        settings = get_redis_settings()
        
        # Should return RedisSettings object
        assert hasattr(settings, 'host')
        assert hasattr(settings, 'port')
        assert hasattr(settings, 'database')

    def test_settings_have_correct_types(self) -> None:
        """Test that settings have correct types."""
        settings = get_redis_settings()
        
        assert isinstance(settings.host, str)
        assert isinstance(settings.port, int)
        assert isinstance(settings.database, int)


class TestGetTaskQueue:
    """Tests for get_task_queue function."""

    @pytest.mark.asyncio
    async def test_get_task_queue_creates_pool(self) -> None:
        """Test get_task_queue creates connection pool."""
        from unittest.mock import AsyncMock
        from app.infrastructure.tasks.queue import get_task_queue, close_task_queue
        import app.infrastructure.tasks.queue as queue_module
        
        # Reset global state
        queue_module._redis_pool = None
        
        with patch("app.infrastructure.tasks.queue.create_pool", new_callable=AsyncMock) as mock_create:
            mock_pool = AsyncMock()
            mock_create.return_value = mock_pool
            
            pool = await get_task_queue()
            
            mock_create.assert_called_once()
            assert pool == mock_pool
        
        # Cleanup
        queue_module._redis_pool = None

    @pytest.mark.asyncio
    async def test_get_task_queue_reuses_pool(self) -> None:
        """Test get_task_queue returns cached pool."""
        from unittest.mock import AsyncMock
        from app.infrastructure.tasks.queue import get_task_queue
        import app.infrastructure.tasks.queue as queue_module
        
        # Set up existing pool
        mock_pool = AsyncMock()
        queue_module._redis_pool = mock_pool
        
        pool = await get_task_queue()
        
        assert pool == mock_pool
        
        # Cleanup
        queue_module._redis_pool = None


class TestCloseTaskQueue:
    """Tests for close_task_queue function."""

    @pytest.mark.asyncio
    async def test_close_task_queue_closes_pool(self) -> None:
        """Test close_task_queue closes connection pool."""
        from unittest.mock import AsyncMock
        from app.infrastructure.tasks.queue import close_task_queue
        import app.infrastructure.tasks.queue as queue_module
        
        # Set up mock pool
        mock_pool = AsyncMock()
        queue_module._redis_pool = mock_pool
        
        await close_task_queue()
        
        mock_pool.close.assert_called_once()
        assert queue_module._redis_pool is None

    @pytest.mark.asyncio
    async def test_close_task_queue_when_none(self) -> None:
        """Test close_task_queue handles None pool."""
        from app.infrastructure.tasks.queue import close_task_queue
        import app.infrastructure.tasks.queue as queue_module
        
        queue_module._redis_pool = None
        
        # Should not raise
        await close_task_queue()
        
        assert queue_module._redis_pool is None
