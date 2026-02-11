# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for MetricsService.

Tests for response time tracking, error counting, and Redis health checks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.monitoring.metrics_service import (
    MetricsService,
    ResponseTimeMetrics,
    get_metrics_service,
)


class TestMetricsServiceInit:
    """Tests for MetricsService initialization."""

    def test_service_creation(self) -> None:
        """Test service can be created."""
        service = MetricsService()

        assert service.request_count == 0
        assert service.error_count == 0
        assert service.error_rate == 0.0
        assert not service.is_redis_healthy

    def test_singleton_pattern(self) -> None:
        """Test get_metrics_service returns singleton."""
        service1 = get_metrics_service()
        service2 = get_metrics_service()

        assert service1 is service2


class TestResponseTimeTracking:
    """Tests for response time tracking."""

    def test_record_response_time(self) -> None:
        """Test recording response time."""
        service = MetricsService()

        service.record_response_time(100.5)
        service.record_response_time(200.3)
        service.record_response_time(150.7)

        assert service.request_count == 3

    def test_get_metrics_empty(self) -> None:
        """Test getting metrics with no data."""
        service = MetricsService()

        metrics = service.get_response_time_metrics()

        assert metrics.avg_ms == 0.0
        assert metrics.min_ms == 0.0
        assert metrics.max_ms == 0.0
        assert metrics.p50_ms == 0.0
        assert metrics.p95_ms == 0.0
        assert metrics.p99_ms == 0.0
        assert metrics.sample_count == 0

    def test_get_metrics_with_data(self) -> None:
        """Test calculating response time metrics."""
        service = MetricsService()

        # Add sample data
        times = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        for time in times:
            service.record_response_time(time)

        metrics = service.get_response_time_metrics()

        assert metrics.sample_count == 10
        assert metrics.min_ms == 10.0
        assert metrics.max_ms == 100.0
        assert metrics.avg_ms == 55.0  # Average of 10-100
        assert 50.0 <= metrics.p50_ms <= 60.0  # Median (interpolated)
        assert metrics.p95_ms >= 90.0  # 95th percentile
        assert metrics.p99_ms >= 90.0  # 99th percentile

    def test_metrics_percentiles(self) -> None:
        """Test percentile calculations."""
        service = MetricsService()

        # Add 100 samples from 1-100
        for i in range(1, 101):
            service.record_response_time(float(i))

        metrics = service.get_response_time_metrics()

        assert metrics.sample_count == 100
        assert 50.0 <= metrics.p50_ms <= 51.0  # 50th percentile (interpolated)
        assert 95.0 <= metrics.p95_ms <= 96.0  # 95th percentile
        assert 99.0 <= metrics.p99_ms <= 100.0  # 99th percentile

    def test_max_samples_limit(self) -> None:
        """Test that samples are limited to MAX_SAMPLES."""
        service = MetricsService()

        # Add more than MAX_SAMPLES
        for i in range(MetricsService.MAX_SAMPLES + 100):
            service.record_response_time(float(i))

        metrics = service.get_response_time_metrics()

        # Should only keep MAX_SAMPLES
        assert metrics.sample_count == MetricsService.MAX_SAMPLES


class TestErrorTracking:
    """Tests for error tracking."""

    def test_record_error(self) -> None:
        """Test recording errors."""
        service = MetricsService()

        service.record_error()
        service.record_error()

        assert service.error_count == 2

    def test_error_rate_calculation(self) -> None:
        """Test error rate percentage calculation."""
        service = MetricsService()

        # Record 10 requests, 2 errors
        for _ in range(10):
            service.record_response_time(100.0)
        service.record_error()
        service.record_error()

        assert service.error_rate == 20.0  # 2/10 = 20%

    def test_error_rate_zero_requests(self) -> None:
        """Test error rate with zero requests."""
        service = MetricsService()

        assert service.error_rate == 0.0

    def test_error_rate_no_errors(self) -> None:
        """Test error rate with no errors."""
        service = MetricsService()

        for _ in range(10):
            service.record_response_time(100.0)

        assert service.error_rate == 0.0


class TestRedisHealthCheck:
    """Tests for Redis health checking."""

    @pytest.mark.asyncio
    async def test_redis_health_check_success(self) -> None:
        """Test successful Redis health check."""
        service = MetricsService()

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True

        with patch.object(service, "_get_redis_client", return_value=mock_redis):
            is_healthy, elapsed_ms = await service.check_redis_health()

            assert is_healthy is True
            assert elapsed_ms >= 0
            assert service.is_redis_healthy is True

    @pytest.mark.asyncio
    async def test_redis_health_check_failure(self) -> None:
        """Test failed Redis health check."""
        service = MetricsService()

        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")

        with patch.object(service, "_get_redis_client", return_value=mock_redis):
            is_healthy, elapsed_ms = await service.check_redis_health()

            assert is_healthy is False
            assert elapsed_ms >= 0
            assert service.is_redis_healthy is False

    @pytest.mark.asyncio
    async def test_redis_ping_false(self) -> None:
        """Test Redis ping returning False."""
        service = MetricsService()

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = False

        with patch.object(service, "_get_redis_client", return_value=mock_redis):
            is_healthy, elapsed_ms = await service.check_redis_health()

            assert is_healthy is False
            assert service.is_redis_healthy is False


class TestMetricsReset:
    """Tests for metrics reset functionality."""

    def test_reset_metrics(self) -> None:
        """Test resetting all metrics."""
        service = MetricsService()

        # Add some data
        service.record_response_time(100.0)
        service.record_response_time(200.0)
        service.record_error()

        assert service.request_count > 0
        assert service.error_count > 0

        # Reset
        service.reset_metrics()

        assert service.request_count == 0
        assert service.error_count == 0
        assert service.error_rate == 0.0

        metrics = service.get_response_time_metrics()
        assert metrics.sample_count == 0


class TestResponseTimeMetricsDataclass:
    """Tests for ResponseTimeMetrics dataclass."""

    def test_metrics_creation(self) -> None:
        """Test creating ResponseTimeMetrics."""
        metrics = ResponseTimeMetrics(
            avg_ms=50.0,
            min_ms=10.0,
            max_ms=100.0,
            p50_ms=45.0,
            p95_ms=90.0,
            p99_ms=95.0,
            sample_count=100,
        )

        assert metrics.avg_ms == 50.0
        assert metrics.min_ms == 10.0
        assert metrics.max_ms == 100.0
        assert metrics.p50_ms == 45.0
        assert metrics.p95_ms == 90.0
        assert metrics.p99_ms == 95.0
        assert metrics.sample_count == 100


class TestMetricsServiceProperties:
    """Tests for MetricsService properties."""

    def test_request_count_property(self) -> None:
        """Test request_count property."""
        service = MetricsService()

        assert service.request_count == 0

        service.record_response_time(100.0)
        assert service.request_count == 1

    def test_error_count_property(self) -> None:
        """Test error_count property."""
        service = MetricsService()

        assert service.error_count == 0

        service.record_error()
        assert service.error_count == 1

    def test_is_redis_healthy_property(self) -> None:
        """Test is_redis_healthy property."""
        service = MetricsService()

        assert service.is_redis_healthy is False
