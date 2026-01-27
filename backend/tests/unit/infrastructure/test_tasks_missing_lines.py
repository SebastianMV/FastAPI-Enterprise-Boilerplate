"""Test coverage for missing lines in tasks/queue.py (74% → 95%+)."""

import pytest  # type: ignore
import asyncio
from datetime import datetime, UTC
from typing import Any
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from uuid import uuid4

from arq import ArqRedis  # type: ignore
from arq.jobs import Job, JobStatus as ArqJobStatus  # type: ignore

from app.infrastructure.tasks.queue import (
    get_job,
    get_job_status,
    get_job_result,
    send_email_task,
    process_webhook_task,
    cleanup_expired_tokens_task,
    generate_report_task,
    WorkerSettings,
)


class TestJobStatusAndResult:
    """Test get_job_status and get_job_result functions (lines 170-173, 190-193)."""
    
    @pytest.mark.asyncio
    async def test_get_job_status_with_existing_job(self):
        """Test get_job_status returns status for existing job (line 172)."""
        mock_job = AsyncMock(spec=Job)
        mock_job.status.return_value = ArqJobStatus.complete
        
        with patch('app.infrastructure.tasks.queue.get_job', return_value=mock_job):
            status = await get_job_status("test-job-id")
            assert status == ArqJobStatus.complete
            mock_job.status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_job_status_with_nonexistent_job(self):
        """Test get_job_status returns None for nonexistent job (line 173)."""
        with patch('app.infrastructure.tasks.queue.get_job', return_value=None):
            status = await get_job_status("nonexistent-job")
            assert status is None
    
    @pytest.mark.asyncio
    async def test_get_job_result_with_existing_job(self):
        """Test get_job_result waits and returns result (line 192)."""
        mock_job = AsyncMock(spec=Job)
        mock_job.result.return_value = {"status": "success", "data": "test"}
        
        with patch('app.infrastructure.tasks.queue.get_job', return_value=mock_job):
            result = await get_job_result("test-job-id", timeout=10.0)
            assert result == {"status": "success", "data": "test"}
            mock_job.result.assert_called_once_with(timeout=10.0)
    
    @pytest.mark.asyncio
    async def test_get_job_result_with_nonexistent_job(self):
        """Test get_job_result returns None for nonexistent job (line 193)."""
        with patch('app.infrastructure.tasks.queue.get_job', return_value=None):
            result = await get_job_result("nonexistent-job")
            assert result is None


class TestSendEmailTask:
    """Test send_email_task function (lines 221-236)."""
    
    @pytest.mark.asyncio
    async def test_send_email_task_success(self):
        """Test send_email_task sends email successfully."""
        mock_sender = AsyncMock()
        mock_sender.send.return_value = True
        
        mock_email_service = Mock()
        mock_email_service._sender = mock_sender
        
        # Patch where it's actually imported (inside the function)
        with patch('app.infrastructure.email.service.get_email_service', return_value=mock_email_service):
            result = await send_email_task(
                {},
                to="test@example.com",
                subject="Test Subject",
                body="Test body content",
            )
            
            assert result["status"] == "sent"
            assert result["to"] == "test@example.com"
            assert result["subject"] == "Test Subject"
            assert "sent_at" in result
            mock_sender.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_task_failure(self):
        """Test send_email_task handles send failure."""
        mock_sender = AsyncMock()
        mock_sender.send.return_value = False
        
        mock_email_service = Mock()
        mock_email_service._sender = mock_sender
        
        with patch('app.infrastructure.email.service.get_email_service', return_value=mock_email_service):
            result = await send_email_task(
                {},
                to="test@example.com",
                subject="Test",
                body="Body",
            )
            
            assert result["status"] == "failed"
    
    @pytest.mark.asyncio
    async def test_send_email_task_with_template(self):
        """Test send_email_task with template_id parameter."""
        mock_sender = AsyncMock()
        mock_sender.send.return_value = True
        
        mock_email_service = Mock()
        mock_email_service._sender = mock_sender
        
        with patch('app.infrastructure.email.service.get_email_service', return_value=mock_email_service):
            result = await send_email_task(
                {},
                to="user@example.com",
                subject="Welcome",
                body="Welcome to our service",
                template_id="welcome_template",
            )
            
            assert result["status"] == "sent"


class TestProcessWebhookTask:
    """Test process_webhook_task function (lines 262-273)."""
    
    @pytest.mark.asyncio
    async def test_process_webhook_task_success(self):
        """Test process_webhook_task sends webhook successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await process_webhook_task(
                {},
                webhook_url="https://example.com/webhook",
                payload={"event": "test", "data": "value"},
            )
            
            assert result["status"] == "sent"
            assert result["url"] == "https://example.com/webhook"
            assert result["response_status"] == 200
            assert "sent_at" in result
    
    @pytest.mark.asyncio
    async def test_process_webhook_task_with_headers(self):
        """Test process_webhook_task with custom headers."""
        mock_response = Mock()
        mock_response.status_code = 201
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        custom_headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await process_webhook_task(
                {},
                webhook_url="https://api.example.com/hook",
                payload={"event": "user.created"},
                headers=custom_headers,
            )
            
            assert result["status"] == "sent"
            assert result["response_status"] == 201
            mock_client.post.assert_called_once()


class TestCleanupExpiredTokensTask:
    """Test cleanup_expired_tokens_task function (lines 289-297)."""
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens_task(self):
        """Test cleanup_expired_tokens_task completes successfully."""
        result = await cleanup_expired_tokens_task({})
        
        assert result["status"] == "completed"
        assert result["deleted_count"] == 0  # Auto-expire via Redis TTL
        assert "completed_at" in result


class TestGenerateReportTask:
    """Test generate_report_task function (lines 322-327)."""
    
    @pytest.mark.asyncio
    async def test_generate_report_task_analytics(self):
        """Test generate_report_task for analytics report."""
        result = await generate_report_task(
            {},
            report_type="analytics",
            tenant_id="tenant-123",
            params={"start_date": "2024-01-01", "end_date": "2024-12-31"},
        )
        
        assert result["status"] == "completed"
        assert result["report_type"] == "analytics"
        assert result["tenant_id"] == "tenant-123"
        assert "file_path" in result
        assert "generated_at" in result
    
    @pytest.mark.asyncio
    async def test_generate_report_task_usage(self):
        """Test generate_report_task for usage report."""
        result = await generate_report_task(
            {},
            report_type="usage",
            tenant_id="tenant-456",
            params={"metrics": ["cpu", "memory", "disk"]},
        )
        
        assert result["status"] == "completed"
        assert result["report_type"] == "usage"
        assert result["tenant_id"] == "tenant-456"
    
    @pytest.mark.asyncio
    async def test_generate_report_task_financial(self):
        """Test generate_report_task for financial report."""
        result = await generate_report_task(
            {},
            report_type="financial",
            tenant_id="tenant-789",
            params={"currency": "USD", "include_vat": True},
        )
        
        assert result["status"] == "completed"
        assert result["report_type"] == "financial"


class TestWorkerSettings:
    """Test WorkerSettings lifecycle hooks (lines 380, 387)."""
    
    @pytest.mark.asyncio
    async def test_worker_on_startup(self):
        """Test WorkerSettings.on_startup hook is called (line 380)."""
        ctx = {}
        
        # Should not raise any exceptions
        await WorkerSettings.on_startup(ctx)
        
        # Verify it's a static method
        assert callable(WorkerSettings.on_startup)
    
    @pytest.mark.asyncio
    async def test_worker_on_shutdown(self):
        """Test WorkerSettings.on_shutdown hook is called (line 387)."""
        ctx = {}
        
        # Should not raise any exceptions
        await WorkerSettings.on_shutdown(ctx)
        
        # Verify it's a static method
        assert callable(WorkerSettings.on_shutdown)
    
    @pytest.mark.asyncio
    async def test_worker_lifecycle(self):
        """Test complete worker lifecycle (startup → shutdown)."""
        ctx = {"worker_id": "test-worker-1"}
        
        # Simulate worker lifecycle
        await WorkerSettings.on_startup(ctx)
        # ... worker processes tasks ...
        await WorkerSettings.on_shutdown(ctx)
        
        # Both hooks should complete without errors
        assert True
