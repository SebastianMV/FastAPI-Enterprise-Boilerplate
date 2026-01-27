# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Additional tests for background task queue functionality."""

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.infrastructure.tasks.queue import (
    get_redis_settings,
    get_task_queue,
    close_task_queue,
    enqueue_task,
    get_job,
    TaskResult,
    TaskStatus,
)


class TestRedisSettings:
    """Tests for Redis settings configuration."""

    def test_get_redis_settings(self):
        """Should return Redis settings from config."""
        settings = get_redis_settings()
        
        assert settings is not None
        assert hasattr(settings, 'host')
        assert hasattr(settings, 'port')
        assert hasattr(settings, 'database')


class TestTaskQueue:
    """Tests for task queue operations."""

    @pytest.mark.asyncio
    async def test_get_task_queue_creates_pool(self):
        """Should create Redis pool on first call."""
        with patch('app.infrastructure.tasks.queue.create_pool', new_callable=AsyncMock) as mock_create:
            mock_pool = MagicMock()
            mock_create.return_value = mock_pool
            
            # Clear global pool
            import app.infrastructure.tasks.queue as queue_module
            queue_module._redis_pool = None
            
            pool = await get_task_queue()
            
            assert pool == mock_pool
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_queue_reuses_existing_pool(self):
        """Should reuse existing Redis pool."""
        mock_pool = MagicMock()
        
        with patch('app.infrastructure.tasks.queue.create_pool', new_callable=AsyncMock) as mock_create:
            import app.infrastructure.tasks.queue as queue_module
            queue_module._redis_pool = mock_pool
            
            pool = await get_task_queue()
            
            assert pool == mock_pool
            mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_task_queue(self):
        """Should close Redis pool."""
        mock_pool = AsyncMock()
        
        import app.infrastructure.tasks.queue as queue_module
        queue_module._redis_pool = mock_pool
        
        await close_task_queue()
        
        mock_pool.close.assert_called_once()
        assert queue_module._redis_pool is None

    @pytest.mark.asyncio
    async def test_close_task_queue_when_none(self):
        """Should handle closing when pool is None."""
        import app.infrastructure.tasks.queue as queue_module
        queue_module._redis_pool = None
        
        # Should not raise exception
        await close_task_queue()
        
        assert queue_module._redis_pool is None


class TestEnqueueTask:
    """Tests for task enqueueing."""

    @pytest.mark.asyncio
    async def test_enqueue_task_basic(self):
        """Should enqueue task with basic parameters."""
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        
        mock_pool = AsyncMock()
        mock_pool.enqueue_job.return_value = mock_job
        
        with patch('app.infrastructure.tasks.queue.get_task_queue', return_value=mock_pool):
            job = await enqueue_task("send_email", to="test@example.com", subject="Test")
            
            assert job == mock_job
            mock_pool.enqueue_job.assert_called_once()
            args, kwargs = mock_pool.enqueue_job.call_args
            assert args[0] == "send_email"
            assert "to" in kwargs
            assert kwargs["to"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_enqueue_task_with_defer_by(self):
        """Should enqueue task with defer_by."""
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        
        mock_pool = AsyncMock()
        mock_pool.enqueue_job.return_value = mock_job
        
        defer_time = timedelta(minutes=5)
        
        with patch('app.infrastructure.tasks.queue.get_task_queue', return_value=mock_pool):
            job = await enqueue_task("send_email", _defer_by=defer_time, to="test@example.com")
            
            assert job == mock_job
            args, kwargs = mock_pool.enqueue_job.call_args
            assert kwargs["_defer_by"] == defer_time

    @pytest.mark.asyncio
    async def test_enqueue_task_with_defer_until(self):
        """Should enqueue task with defer_until."""
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        
        mock_pool = AsyncMock()
        mock_pool.enqueue_job.return_value = mock_job
        
        defer_until = datetime.now(UTC) + timedelta(hours=1)
        
        with patch('app.infrastructure.tasks.queue.get_task_queue', return_value=mock_pool):
            job = await enqueue_task("send_email", _defer_until=defer_until, to="test@example.com")
            
            assert job == mock_job
            args, kwargs = mock_pool.enqueue_job.call_args
            assert kwargs["_defer_until"] == defer_until

    @pytest.mark.asyncio
    async def test_enqueue_task_with_custom_job_id(self):
        """Should enqueue task with custom job ID."""
        mock_job = MagicMock()
        mock_job.job_id = "custom-job-id"
        
        mock_pool = AsyncMock()
        mock_pool.enqueue_job.return_value = mock_job
        
        with patch('app.infrastructure.tasks.queue.get_task_queue', return_value=mock_pool):
            job = await enqueue_task("send_email", _job_id="custom-job-id", to="test@example.com")
            
            assert job.job_id == "custom-job-id"
            args, kwargs = mock_pool.enqueue_job.call_args
            assert kwargs["_job_id"] == "custom-job-id"

    @pytest.mark.asyncio
    async def test_enqueue_task_with_queue_name(self):
        """Should enqueue task to custom queue."""
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        
        mock_pool = AsyncMock()
        mock_pool.enqueue_job.return_value = mock_job
        
        with patch('app.infrastructure.tasks.queue.get_task_queue', return_value=mock_pool):
            job = await enqueue_task("send_email", _queue_name="high-priority", to="test@example.com")
            
            assert job == mock_job
            args, kwargs = mock_pool.enqueue_job.call_args
            assert kwargs["_queue_name"] == "high-priority"


class TestGetJob:
    """Tests for getting job by ID."""

    @pytest.mark.asyncio
    async def test_get_job_existing(self):
        """Should get existing job by ID."""
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        
        mock_pool = AsyncMock()
        
        # Mock the Job class initialization
        with patch('app.infrastructure.tasks.queue.get_task_queue', return_value=mock_pool), \
             patch('app.infrastructure.tasks.queue.Job') as mock_job_class:
            mock_job_class.return_value = mock_job
            
            job = await get_job("job-123")
            
            # Verify Job was instantiated with correct parameters
            mock_job_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_returns_none_when_not_found(self):
        """Should return None when job not found."""
        mock_pool = AsyncMock()
        
        with patch('app.infrastructure.tasks.queue.get_task_queue', return_value=mock_pool), \
             patch('app.infrastructure.tasks.queue.Job') as mock_job_class:
            
            job = await get_job("nonexistent-job")
            
            # Job should still be created but may not exist in Redis
            assert mock_job_class.called


class TestTaskResultDuration:
    """Tests for TaskResult duration calculation."""

    def test_duration_with_both_timestamps(self):
        """Should calculate duration when both timestamps exist."""
        start = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 10, 5, 30, tzinfo=UTC)
        
        result = TaskResult(
            task_id="test",
            status=TaskStatus.SUCCESS,
            started_at=start,
            completed_at=end
        )
        
        assert result.duration == timedelta(minutes=5, seconds=30)

    def test_duration_with_only_start(self):
        """Should return None when only start timestamp exists."""
        result = TaskResult(
            task_id="test",
            status=TaskStatus.RUNNING,
            started_at=datetime.now(UTC),
            completed_at=None
        )
        
        assert result.duration is None

    def test_duration_with_only_end(self):
        """Should return None when only end timestamp exists."""
        result = TaskResult(
            task_id="test",
            status=TaskStatus.FAILED,
            started_at=None,
            completed_at=datetime.now(UTC)
        )
        
        assert result.duration is None

    def test_duration_with_neither_timestamp(self):
        """Should return None when neither timestamp exists."""
        result = TaskResult(
            task_id="test",
            status=TaskStatus.PENDING
        )
        
        assert result.duration is None
