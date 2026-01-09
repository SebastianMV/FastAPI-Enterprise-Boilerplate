# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Metrics service for application monitoring.

Provides real-time metrics including:
- Redis health check
- Response time tracking
- Request counting
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Deque

import redis.asyncio as redis

from app.config import settings


logger = logging.getLogger(__name__)

# Global metrics instance
_metrics_service: "MetricsService | None" = None


@dataclass
class ResponseTimeMetrics:
    """Response time statistics."""
    
    avg_ms: float
    min_ms: float
    max_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    sample_count: int


class MetricsService:
    """
    Service for collecting and reporting application metrics.
    
    Features:
    - Redis health check with PING
    - Response time tracking with sliding window
    - Request counting
    """
    
    # Maximum samples to keep in memory
    MAX_SAMPLES = 1000
    
    def __init__(self) -> None:
        self._response_times: Deque[float] = deque(maxlen=self.MAX_SAMPLES)
        self._request_count = 0
        self._error_count = 0
        self._redis_client: redis.Redis | None = None
        self._last_redis_check: datetime | None = None
        self._redis_healthy = False
    
    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
            )
        return self._redis_client
    
    async def check_redis_health(self) -> tuple[bool, float]:
        """
        Check Redis health using PING command.
        
        Returns:
            Tuple of (is_healthy, response_time_ms)
        """
        start_time = time.perf_counter()
        
        try:
            client = await self._get_redis_client()
            response = await client.ping()
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            is_healthy = response is True
            self._redis_healthy = is_healthy
            self._last_redis_check = datetime.now(UTC)
            
            return is_healthy, elapsed_ms
            
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Redis health check failed: {e}")
            self._redis_healthy = False
            self._last_redis_check = datetime.now(UTC)
            return False, elapsed_ms
    
    def record_response_time(self, response_time_ms: float) -> None:
        """Record a response time sample."""
        self._response_times.append(response_time_ms)
        self._request_count += 1
    
    def record_error(self) -> None:
        """Record an error occurrence."""
        self._error_count += 1
    
    def get_response_time_metrics(self) -> ResponseTimeMetrics:
        """
        Calculate response time statistics.
        
        Returns:
            ResponseTimeMetrics with avg, min, max, and percentiles
        """
        if not self._response_times:
            return ResponseTimeMetrics(
                avg_ms=0.0,
                min_ms=0.0,
                max_ms=0.0,
                p50_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
                sample_count=0,
            )
        
        sorted_times = sorted(self._response_times)
        count = len(sorted_times)
        
        avg_ms = sum(sorted_times) / count
        min_ms = sorted_times[0]
        max_ms = sorted_times[-1]
        
        # Percentiles
        p50_idx = int(count * 0.50)
        p95_idx = int(count * 0.95)
        p99_idx = int(count * 0.99)
        
        p50_ms = sorted_times[min(p50_idx, count - 1)]
        p95_ms = sorted_times[min(p95_idx, count - 1)]
        p99_ms = sorted_times[min(p99_idx, count - 1)]
        
        return ResponseTimeMetrics(
            avg_ms=round(avg_ms, 2),
            min_ms=round(min_ms, 2),
            max_ms=round(max_ms, 2),
            p50_ms=round(p50_ms, 2),
            p95_ms=round(p95_ms, 2),
            p99_ms=round(p99_ms, 2),
            sample_count=count,
        )
    
    @property
    def request_count(self) -> int:
        """Get total request count."""
        return self._request_count
    
    @property
    def error_count(self) -> int:
        """Get total error count."""
        return self._error_count
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self._request_count == 0:
            return 0.0
        return round((self._error_count / self._request_count) * 100, 2)
    
    @property
    def is_redis_healthy(self) -> bool:
        """Get last known Redis health status."""
        return self._redis_healthy
    
    def reset_metrics(self) -> None:
        """Reset all metrics (for testing or rotation)."""
        self._response_times.clear()
        self._request_count = 0
        self._error_count = 0


def get_metrics_service() -> MetricsService:
    """
    Get MetricsService singleton.
    
    Uses singleton pattern to ensure consistent metrics.
    """
    global _metrics_service
    
    if _metrics_service is None:
        _metrics_service = MetricsService()
    
    return _metrics_service
