# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for missing coverage in app/main.py.

Covers:
- Lines 41-43: OpenTelemetry setup when OTEL_ENABLED=True
- Lines 58-59: Uptime tracker initialization error handling
- Line 135: Root endpoint with is_production=True (docs=None)
"""

from unittest.mock import AsyncMock, patch

import pytest  # type: ignore
from fastapi import FastAPI


class TestLifespanOpenTelemetry:
    """Tests for OpenTelemetry initialization in lifespan (lines 41-43)."""

    @pytest.mark.asyncio
    async def test_lifespan_otel_enabled_success(self) -> None:
        """Test lifespan initializes OpenTelemetry when OTEL_ENABLED=True."""
        from app.main import lifespan

        mock_app = FastAPI()

        with (
            patch(
                "app.infrastructure.database.connection.init_database",
                new_callable=AsyncMock,
            ),
            patch(
                "app.infrastructure.database.connection.close_database",
                new_callable=AsyncMock,
            ),
            patch("app.infrastructure.observability.logging.setup_logging"),
            patch(
                "app.infrastructure.observability.telemetry.setup_telemetry"
            ) as mock_setup_telemetry,
            patch("app.main.settings") as mock_settings,
        ):
            mock_settings.APP_NAME = "Test App"
            mock_settings.APP_VERSION = "1.0.0"
            mock_settings.ENVIRONMENT = "test"
            mock_settings.OTEL_ENABLED = True  # Enable OTEL

            async with lifespan(mock_app):
                # Verify setup_telemetry was called (line 42)
                mock_setup_telemetry.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_otel_disabled_skips_setup(self) -> None:
        """Test lifespan skips OpenTelemetry when OTEL_ENABLED=False."""
        from app.main import lifespan

        mock_app = FastAPI()

        with (
            patch(
                "app.infrastructure.database.connection.init_database",
                new_callable=AsyncMock,
            ),
            patch(
                "app.infrastructure.database.connection.close_database",
                new_callable=AsyncMock,
            ),
            patch("app.infrastructure.observability.logging.setup_logging"),
            patch(
                "app.infrastructure.observability.telemetry.setup_telemetry"
            ) as mock_setup_telemetry,
            patch("app.main.settings") as mock_settings,
        ):
            mock_settings.APP_NAME = "Test App"
            mock_settings.APP_VERSION = "1.0.0"
            mock_settings.ENVIRONMENT = "test"
            mock_settings.OTEL_ENABLED = False  # Disable OTEL

            async with lifespan(mock_app):
                # Verify setup_telemetry was NOT called
                mock_setup_telemetry.assert_not_called()


class TestLifespanUptimeTrackerError:
    """Tests for uptime tracker error handling in lifespan (lines 58-59)."""

    @pytest.mark.asyncio
    async def test_lifespan_uptime_tracker_initialization_error(self) -> None:
        """Test lifespan handles uptime tracker initialization error gracefully."""
        from app.main import lifespan

        mock_app = FastAPI()

        with (
            patch(
                "app.infrastructure.database.connection.init_database",
                new_callable=AsyncMock,
            ),
            patch(
                "app.infrastructure.database.connection.close_database",
                new_callable=AsyncMock,
            ),
            patch("app.infrastructure.observability.logging.setup_logging"),
            patch(
                "app.infrastructure.monitoring.get_uptime_tracker"
            ) as mock_get_uptime,
        ):
            # Make uptime tracker initialization fail
            mock_tracker = AsyncMock()
            mock_tracker.initialize = AsyncMock(
                side_effect=Exception("Uptime tracker init failed")
            )
            mock_get_uptime.return_value = mock_tracker

            with patch("app.main.settings") as mock_settings:
                mock_settings.APP_NAME = "Test App"
                mock_settings.APP_VERSION = "1.0.0"
                mock_settings.ENVIRONMENT = "test"
                mock_settings.OTEL_ENABLED = False

                # Should not raise - error is logged as warning (line 59)
                async with lifespan(mock_app):
                    pass

                # Verify initialization was attempted
                mock_tracker.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_uptime_tracker_success(self) -> None:
        """Test lifespan successfully initializes uptime tracker."""
        from app.main import lifespan

        mock_app = FastAPI()

        with (
            patch(
                "app.infrastructure.database.connection.init_database",
                new_callable=AsyncMock,
            ),
            patch(
                "app.infrastructure.database.connection.close_database",
                new_callable=AsyncMock,
            ),
            patch("app.infrastructure.observability.logging.setup_logging"),
            patch(
                "app.infrastructure.monitoring.get_uptime_tracker"
            ) as mock_get_uptime,
        ):
            # Make uptime tracker initialization succeed
            mock_tracker = AsyncMock()
            mock_tracker.initialize = AsyncMock()
            mock_get_uptime.return_value = mock_tracker

            with patch("app.main.settings") as mock_settings:
                mock_settings.APP_NAME = "Test App"
                mock_settings.APP_VERSION = "1.0.0"
                mock_settings.ENVIRONMENT = "test"
                mock_settings.OTEL_ENABLED = False

                async with lifespan(mock_app):
                    pass

                # Verify successful initialization
                mock_tracker.initialize.assert_called_once()


class TestRootEndpoint:
    """Tests for root endpoint (line 135)."""

    def test_root_endpoint_response_structure(self) -> None:
        """Test root endpoint returns correct structure."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "environment" in data
        assert "docs" in data
        assert "health" in data
        assert data["health"] == "/api/v1/health"

    def test_root_endpoint_docs_field_in_production(self) -> None:
        """Test root endpoint docs field matches is_production setting (line 135)."""
        from fastapi.testclient import TestClient

        from app.main import app, settings

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # The docs field should be None if is_production, else "/docs"
        if settings.is_production:
            assert data["docs"] is None  # Line 135
        else:
            assert data["docs"] == "/docs"

    def test_root_endpoint_uses_settings_values(self) -> None:
        """Test root endpoint returns values from settings."""
        from fastapi.testclient import TestClient

        from app.main import app, settings

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Should match actual settings
        assert data["name"] == settings.APP_NAME
        assert data["version"] == settings.APP_VERSION
        assert data["environment"] == settings.ENVIRONMENT
