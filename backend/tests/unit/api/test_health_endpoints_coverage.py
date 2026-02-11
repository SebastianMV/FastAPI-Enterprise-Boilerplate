# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for health endpoints to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self):
        """Test basic health check returns healthy status."""
        from app.api.v1.endpoints.health import health_check

        result = await health_check()

        assert result.status == "healthy"
        assert result.version is not None
        assert result.environment is not None

    @pytest.mark.asyncio
    async def test_liveness_check_returns_alive(self):
        """Test liveness check returns alive status."""
        from app.api.v1.endpoints.health import liveness_check

        result = await liveness_check()

        assert result.status == "alive"
        assert result.version is not None

    @pytest.mark.asyncio
    async def test_readiness_check_redis_healthy(self):
        """Test readiness check when Redis is healthy."""
        from app.api.v1.endpoints.health import readiness_check

        mock_metrics = MagicMock()
        mock_metrics.check_redis_health = AsyncMock(return_value=(True, 1.5))

        mock_uptime = MagicMock()
        mock_uptime.record_ping = AsyncMock()

        with (
            patch(
                "app.infrastructure.monitoring.get_metrics_service",
                return_value=mock_metrics,
            ),
            patch(
                "app.infrastructure.monitoring.get_uptime_tracker",
                return_value=mock_uptime,
            ),
        ):
            result = await readiness_check()

            assert result.status == "ready"
            assert result.redis == "healthy"
            assert result.database == "healthy"
            mock_uptime.record_ping.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_readiness_check_redis_unhealthy(self):
        """Test readiness check when Redis is unhealthy."""
        from app.api.v1.endpoints.health import readiness_check

        mock_metrics = MagicMock()
        mock_metrics.check_redis_health = AsyncMock(return_value=(False, 0))

        mock_uptime = MagicMock()
        mock_uptime.record_ping = AsyncMock()

        with (
            patch(
                "app.infrastructure.monitoring.get_metrics_service",
                return_value=mock_metrics,
            ),
            patch(
                "app.infrastructure.monitoring.get_uptime_tracker",
                return_value=mock_uptime,
            ),
        ):
            result = await readiness_check()

            assert result.status == "degraded"
            assert result.redis == "unhealthy"
            mock_uptime.record_ping.assert_called_once_with(False)
