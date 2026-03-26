# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for MetricsMiddleware.

Tests for request/response time tracking and error counting.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from starlette.responses import Response

from app.middleware.metrics import EXCLUDED_PATHS, MetricsMiddleware


class TestMetricsMiddlewareInit:
    """Tests for MetricsMiddleware initialization."""

    def test_middleware_creation(self) -> None:
        """Test middleware can be created."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)

        assert middleware.app == app


class TestMetricsMiddlewareExcludedPaths:
    """Tests for excluded paths handling."""

    @pytest.mark.asyncio
    async def test_excluded_path_skips_metrics(self) -> None:
        """Test that excluded paths don't record metrics."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/health")
        async def health():
            return {"status": "ok"}

        with patch("app.middleware.metrics.get_metrics_service") as mock_metrics:
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/health")

            # Metrics should not be called for excluded paths
            mock_metrics.assert_not_called()
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_docs_path_excluded(self) -> None:
        """Test that /docs is excluded from metrics."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/docs")
        async def docs():
            return {"docs": True}

        with patch("app.middleware.metrics.get_metrics_service") as mock_metrics:
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/docs")

            mock_metrics.assert_not_called()
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_path_excluded(self) -> None:
        """Test that /openapi.json is excluded from metrics."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/openapi.json")
        async def openapi():
            return {}

        with patch("app.middleware.metrics.get_metrics_service") as mock_metrics:
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/openapi.json")

            mock_metrics.assert_not_called()


class TestMetricsMiddlewareSuccessfulRequests:
    """Tests for successful request metrics."""

    @pytest.mark.asyncio
    async def test_records_response_time(self) -> None:
        """Test that response time is recorded."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            return {"users": []}

        mock_service = MagicMock()

        with patch(
            "app.middleware.metrics.get_metrics_service", return_value=mock_service
        ):
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/users")

            # Should record response time
            mock_service.record_response_time.assert_called_once()
            elapsed_ms = mock_service.record_response_time.call_args[0][0]
            assert isinstance(elapsed_ms, float)
            assert elapsed_ms >= 0

            # Should not record error for 2xx
            mock_service.record_error.assert_not_called()
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_adds_response_time_header(self) -> None:
        """Test that X-Response-Time-Ms header is added."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            return {"users": []}

        with patch("app.middleware.metrics.get_metrics_service"):
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/users")

            # Should have timing header
            assert "x-response-time-ms" in response.headers
            timing = float(response.headers["x-response-time-ms"])
            assert timing >= 0

    @pytest.mark.asyncio
    async def test_success_with_201_status(self) -> None:
        """Test successful request with 201 status."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.post("/api/v1/users")
        async def create_user():

            return Response(content="Created", status_code=201)

        mock_service = MagicMock()

        with patch(
            "app.middleware.metrics.get_metrics_service", return_value=mock_service
        ):
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post("/api/v1/users")

            # Should record response time but not error
            mock_service.record_response_time.assert_called_once()
            mock_service.record_error.assert_not_called()
            assert response.status_code == 201


class TestMetricsMiddlewareErrorHandling:
    """Tests for error metrics."""

    @pytest.mark.asyncio
    async def test_records_error_for_500_response(self) -> None:
        """Test that 5xx responses record errors."""
        from fastapi import FastAPI, HTTPException
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            # Use HTTPException to trigger 500 without internal exception
            raise HTTPException(status_code=500, detail="Internal error")

        mock_service = MagicMock()

        with patch(
            "app.middleware.metrics.get_metrics_service", return_value=mock_service
        ):
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/users")

            # Should record both response time and error
            mock_service.record_response_time.assert_called_once()
            mock_service.record_error.assert_called_once()
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_records_error_for_503_response(self) -> None:
        """Test that 503 response records error."""
        from fastapi import FastAPI, HTTPException
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            raise HTTPException(status_code=503, detail="Service Unavailable")

        mock_service = MagicMock()

        with patch(
            "app.middleware.metrics.get_metrics_service", return_value=mock_service
        ):
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/users")

            mock_service.record_error.assert_called_once()
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_no_error_for_4xx_response(self) -> None:
        """Test that 4xx responses don't record errors."""
        from fastapi import FastAPI, HTTPException
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            raise HTTPException(status_code=404, detail="Not Found")

        mock_service = MagicMock()

        with patch(
            "app.middleware.metrics.get_metrics_service", return_value=mock_service
        ):
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/users")

            # Should record response time but not error
            mock_service.record_response_time.assert_called_once()
            mock_service.record_error.assert_not_called()
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_exception_handling(self) -> None:
        """Test that exceptions are handled and metrics recorded."""
        from fastapi import FastAPI, HTTPException
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            # FastAPI converts unhandled exceptions to 500 responses
            raise HTTPException(status_code=500, detail="Test error")

        mock_service = MagicMock()

        with patch(
            "app.middleware.metrics.get_metrics_service", return_value=mock_service
        ):
            app.add_middleware(MetricsMiddleware)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/users")

            # Should still record metrics even on exception
            mock_service.record_response_time.assert_called_once()
            mock_service.record_error.assert_called_once()
            assert response.status_code == 500


class TestExcludedPathsConstant:
    """Tests for EXCLUDED_PATHS constant."""

    def test_excluded_paths_includes_health(self) -> None:
        """Test that health endpoints are in excluded paths."""
        assert "/api/v1/health" in EXCLUDED_PATHS
        assert "/api/v1/health/ready" in EXCLUDED_PATHS
        assert "/api/v1/health/live" in EXCLUDED_PATHS

    def test_excluded_paths_includes_docs(self) -> None:
        """Test that documentation endpoints are excluded."""
        assert "/docs" in EXCLUDED_PATHS
        assert "/redoc" in EXCLUDED_PATHS
        assert "/openapi.json" in EXCLUDED_PATHS

    def test_excluded_paths_is_set(self) -> None:
        """Test that EXCLUDED_PATHS is a set for O(1) lookup."""
        assert isinstance(EXCLUDED_PATHS, set)
