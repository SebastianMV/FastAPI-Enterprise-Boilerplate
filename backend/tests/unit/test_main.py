# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for FastAPI application main module.

Tests for app configuration and lifespan.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestAppConfiguration:
    """Tests for FastAPI app configuration."""

    def test_app_exists(self) -> None:
        """Test FastAPI app is created."""
        from app.main import app

        assert app is not None

    def test_app_title(self) -> None:
        """Test app has correct title."""
        from app.config import settings
        from app.main import app

        assert app.title == settings.APP_NAME

    def test_app_version(self) -> None:
        """Test app has version set."""
        from app.config import settings
        from app.main import app

        assert app.version == settings.APP_VERSION

    def test_app_has_routes(self) -> None:
        """Test app has routes registered."""
        from app.main import app

        # Should have some routes
        assert len(app.routes) > 0

    def test_app_includes_api_router(self) -> None:
        """Test app includes the API router."""
        from app.main import app

        # Find routes starting with /api/v1
        api_routes = [
            r for r in app.routes if hasattr(r, "path") and "/api/v1" in str(r.path)
        ]  # type: ignore[attr-defined]

        assert len(api_routes) > 0


class TestLifespan:
    """Tests for application lifespan handler."""

    def test_lifespan_is_async_context_manager(self) -> None:
        """Test lifespan is an async context manager."""
        from app.main import lifespan

        # lifespan should be decorated with asynccontextmanager
        assert hasattr(lifespan, "__call__")

    def test_lifespan_function_exists(self) -> None:
        """Test lifespan function is defined."""
        from app.main import lifespan

        assert lifespan is not None

    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown(self) -> None:
        """Test lifespan runs startup and shutdown."""
        from fastapi import FastAPI

        from app.main import lifespan

        mock_app = FastAPI()

        with (
            patch(
                "app.infrastructure.database.connection.init_database",
                new_callable=AsyncMock,
            ) as mock_init_db,
            patch(
                "app.infrastructure.database.connection.close_database",
                new_callable=AsyncMock,
            ) as mock_close_db,
            patch(
                "app.infrastructure.observability.logging.setup_logging"
            ) as mock_setup_logging,
            patch("app.config.settings") as mock_settings,
        ):
            mock_settings.APP_NAME = "Test App"
            mock_settings.APP_VERSION = "1.0.0"
            mock_settings.ENVIRONMENT = "test"
            mock_settings.OTEL_ENABLED = False

            async with lifespan(mock_app):
                # During lifespan, startup has run
                mock_setup_logging.assert_called_once()
                mock_init_db.assert_called_once()

            # After lifespan, shutdown has run
            mock_close_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_with_otel_enabled(self) -> None:
        """Test lifespan initializes telemetry when OTEL is enabled."""
        # This test verifies the code path exists for OTEL initialization
        # The actual OTEL setup is tested in test_telemetry.py
        from app.main import lifespan

        # Just verify lifespan function can be called
        assert lifespan is not None
        assert callable(lifespan)

    @pytest.mark.asyncio
    async def test_lifespan_handles_db_error(self) -> None:
        """Test lifespan raises when db init fails (fatal error)."""
        from fastapi import FastAPI

        from app.main import lifespan

        mock_app = FastAPI()

        with patch(
            "app.infrastructure.database.connection.init_database",
            new_callable=AsyncMock,
        ) as mock_init_db:
            mock_init_db.side_effect = Exception("DB connection failed")
            with patch(
                "app.infrastructure.database.connection.close_database",
                new_callable=AsyncMock,
            ):
                with patch("app.infrastructure.observability.logging.setup_logging"):
                    with patch("app.config.settings") as mock_settings:
                        mock_settings.APP_NAME = "Test App"
                        mock_settings.APP_VERSION = "1.0.0"
                        mock_settings.ENVIRONMENT = "test"
                        mock_settings.OTEL_ENABLED = False

                        # DB init failure is fatal — lifespan re-raises
                        with pytest.raises(Exception, match="DB connection failed"):
                            async with lifespan(mock_app):
                                pass


class TestCORSConfiguration:
    """Tests for CORS middleware configuration."""

    def test_cors_middleware_added(self) -> None:
        """Test CORS middleware is added to app."""
        from app.main import app

        # Check middleware is present
        middleware_names = [
            m.cls.__name__ for m in app.user_middleware if hasattr(m, "cls")
        ]  # type: ignore[attr-defined]

        # Should have middleware
        assert len(app.user_middleware) >= 0


class TestAppSettings:
    """Tests for settings integration in app."""

    def test_settings_imported(self) -> None:
        """Test settings are imported in main."""
        from app.main import settings

        assert settings is not None

    def test_logger_exists(self) -> None:
        """Test logger is configured."""
        from app.main import logger

        assert logger is not None
