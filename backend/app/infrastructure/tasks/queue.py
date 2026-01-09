# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Background task queue using Redis and ARQ.

ARQ is a lightweight async task queue for Python, similar to Celery
but designed for async/await and much simpler to configure.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID

from arq import create_pool, ArqRedis
from arq.connections import RedisSettings
from arq.jobs import Job, JobStatus

from app.config import settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate task duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


def get_redis_settings() -> RedisSettings:
    """Get Redis connection settings for ARQ."""
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        database=settings.REDIS_DB,
    )


# Global connection pool
_redis_pool: Optional[ArqRedis] = None


async def get_task_queue() -> ArqRedis:
    """
    Get the ARQ Redis connection pool.
    
    Returns:
        ArqRedis connection pool
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await create_pool(get_redis_settings())
    return _redis_pool


async def close_task_queue() -> None:
    """Close the ARQ Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


async def enqueue_task(
    task_name: str,
    *args,
    _defer_by: Optional[timedelta] = None,
    _defer_until: Optional[datetime] = None,
    _job_id: Optional[str] = None,
    _queue_name: Optional[str] = None,
    **kwargs,
) -> Job:
    """
    Enqueue a background task.
    
    Args:
        task_name: Name of the task function to execute
        *args: Positional arguments for the task
        _defer_by: Delay execution by this timedelta
        _defer_until: Execute at this datetime
        _job_id: Custom job ID (for deduplication)
        _queue_name: Custom queue name
        **kwargs: Keyword arguments for the task
        
    Returns:
        Job instance for tracking
        
    Usage:
        job = await enqueue_task("send_email", to="user@example.com", subject="Hello")
        status = await job.status()
    """
    pool = await get_task_queue()
    
    job = await pool.enqueue_job(
        task_name,
        *args,
        _defer_by=_defer_by,
        _defer_until=_defer_until,
        _job_id=_job_id,
        _queue_name=_queue_name,
        **kwargs,
    )
    
    logger.info(
        f"Task enqueued: {task_name}",
        extra_fields={"job_id": job.job_id, "task": task_name},
    )
    
    return job


async def get_job(job_id: str) -> Optional[Job]:
    """
    Get a job by ID.
    
    Args:
        job_id: The job ID
        
    Returns:
        Job instance or None if not found
    """
    pool = await get_task_queue()
    return Job(job_id, pool)


async def get_job_status(job_id: str) -> Optional[JobStatus]:
    """
    Get the status of a job.
    
    Args:
        job_id: The job ID
        
    Returns:
        JobStatus enum value
    """
    job = await get_job(job_id)
    if job:
        return await job.status()
    return None


async def get_job_result(job_id: str, timeout: float = 30.0) -> Any:
    """
    Wait for a job to complete and get its result.
    
    Args:
        job_id: The job ID
        timeout: Maximum time to wait in seconds
        
    Returns:
        The job result
        
    Raises:
        asyncio.TimeoutError: If job doesn't complete in time
    """
    job = await get_job(job_id)
    if job:
        return await job.result(timeout=timeout)
    return None


# =============================================================================
# TASK DEFINITIONS
# =============================================================================
# These are example tasks. Add your actual tasks here.

async def send_email_task(
    ctx: dict,
    to: str,
    subject: str,
    body: str,
    template_id: Optional[str] = None,
) -> dict:
    """
    Send an email asynchronously.
    
    Args:
        ctx: ARQ context (contains redis connection)
        to: Recipient email
        subject: Email subject
        body: Email body
        template_id: Optional email template ID
        
    Returns:
        Result dict with status
    """
    logger.info(f"Sending email to {to}: {subject}")
    
    # Use the email service for actual sending
    from app.infrastructure.email.service import get_email_service, EmailMessage, EmailRecipient
    
    email_service = get_email_service()
    message = EmailMessage(
        subject=subject,
        to=[EmailRecipient(email=to)],
        html_body=body,
        text_body=body,
    )
    
    success = await email_service._sender.send(message)
    
    return {
        "status": "sent" if success else "failed",
        "to": to,
        "subject": subject,
        "sent_at": datetime.now(UTC).isoformat(),
    }


async def process_webhook_task(
    ctx: dict,
    webhook_url: str,
    payload: dict,
    headers: Optional[dict] = None,
) -> dict:
    """
    Process an outgoing webhook.
    
    Args:
        ctx: ARQ context
        webhook_url: URL to send webhook to
        payload: JSON payload
        headers: Optional HTTP headers
        
    Returns:
        Result dict with response status
    """
    import httpx
    
    logger.info(f"Sending webhook to {webhook_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            webhook_url,
            json=payload,
            headers=headers or {},
        )
    
    return {
        "status": "sent",
        "url": webhook_url,
        "response_status": response.status_code,
        "sent_at": datetime.now(UTC).isoformat(),
    }


async def cleanup_expired_tokens_task(ctx: dict) -> dict:
    """
    Cleanup expired refresh tokens from the cache.
    
    This should be scheduled to run periodically.
    Note: Refresh tokens are stored in Redis with TTL, so they auto-expire.
    This task is for cleaning up any orphaned token references.
    """
    logger.info("Starting expired token cleanup")
    
    # Refresh tokens use Redis TTL for automatic expiration
    # This task handles any additional cleanup needed
    from app.infrastructure.cache import get_cache_service
    
    cache = get_cache_service()
    # Pattern to match expired token keys if needed
    # Most cleanup is handled by Redis TTL automatically
    
    deleted_count = 0  # Tokens auto-expire via Redis TTL
    
    deleted_count = 0  # Placeholder
    
    return {
        "status": "completed",
        "deleted_count": deleted_count,
        "completed_at": datetime.now(UTC).isoformat(),
    }


async def generate_report_task(
    ctx: dict,
    report_type: str,
    tenant_id: str,
    params: dict,
) -> dict:
    """
    Generate a report asynchronously.
    
    Args:
        ctx: ARQ context
        report_type: Type of report to generate
        tenant_id: Tenant ID
        params: Report parameters
        
    Returns:
        Result with report URL or path
    """
    logger.info(f"Generating {report_type} report for tenant {tenant_id}")
    
    # Simulate report generation
    await asyncio.sleep(2.0)
    
    return {
        "status": "completed",
        "report_type": report_type,
        "tenant_id": tenant_id,
        "file_path": f"/reports/{tenant_id}/{report_type}_{datetime.now(UTC).strftime('%Y%m%d')}.pdf",
        "generated_at": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# WORKER CONFIGURATION
# =============================================================================

class WorkerSettings:
    """
    ARQ Worker configuration.
    
    Run the worker with:
        arq app.infrastructure.tasks.queue.WorkerSettings
    """
    
    # Redis connection
    redis_settings = get_redis_settings()
    
    # Task functions to register
    functions = [
        send_email_task,
        process_webhook_task,
        cleanup_expired_tokens_task,
        generate_report_task,
    ]
    
    # Cron jobs (scheduled tasks)
    cron_jobs = [
        # Run token cleanup every hour
        # cron(cleanup_expired_tokens_task, hour={0, 6, 12, 18}, minute=0),
    ]
    
    # Worker settings
    max_jobs = 10  # Max concurrent jobs
    job_timeout = 300  # 5 minutes default timeout
    keep_result = 3600  # Keep results for 1 hour
    
    # Retry settings
    max_tries = 3
    retry_delay = 60  # 1 minute between retries
    
    # Health check
    health_check_interval = 30  # seconds
    
    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Called when worker starts."""
        logger.info("ARQ worker starting up")
        # Initialize any resources needed by tasks
        # e.g., database connections, HTTP clients
    
    @staticmethod
    async def on_shutdown(ctx: dict) -> None:
        """Called when worker shuts down."""
        logger.info("ARQ worker shutting down")
        # Cleanup resources
