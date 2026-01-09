# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for MetricsMiddleware.

Tests for request/response time tracking and error counting.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.metrics import MetricsMiddleware, EXCLUDED_PATHS


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
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        # Create mock request for health endpoint
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/health"
        
        # Mock call_next
        mock_response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=mock_response)
        
        # Process request
        with patch("app.middleware.metrics.get_metrics_service") as mock_metrics:
            response = await middleware.dispatch(mock_request, call_next)
            
            # Metrics should not be called
            mock_metrics.assert_not_called()
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_docs_path_excluded(self) -> None:
        """Test that /docs is excluded from metrics."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/docs"
        
        mock_response = Response(content="Docs", status_code=200)
        call_next = AsyncMock(return_value=mock_response)
        
        with patch("app.middleware.metrics.get_metrics_service") as mock_metrics:
            response = await middleware.dispatch(mock_request, call_next)
            
            mock_metrics.assert_not_called()
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_path_excluded(self) -> None:
        """Test that /openapi.json is excluded from metrics."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/openapi.json"
        
        mock_response = Response(content="{}", status_code=200)
        call_next = AsyncMock(return_value=mock_response)
        
        with patch("app.middleware.metrics.get_metrics_service") as mock_metrics:
            response = await middleware.dispatch(mock_request, call_next)
            
            mock_metrics.assert_not_called()


class TestMetricsMiddlewareSuccessfulRequests:
    """Tests for successful request metrics."""

    @pytest.mark.asyncio
    async def test_records_response_time(self) -> None:
        """Test that response time is recorded."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/users"
        
        mock_response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=mock_response)
        
        mock_service = MagicMock()
        
        with patch("app.middleware.metrics.get_metrics_service", return_value=mock_service):
            response = await middleware.dispatch(mock_request, call_next)
            
            # Should record response time
            mock_service.record_response_time.assert_called_once()
            elapsed_ms = mock_service.record_response_time.call_args[0][0]
            assert isinstance(elapsed_ms, float)
            assert elapsed_ms >= 0
            
            # Should not record error for 2xx
            mock_service.record_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_adds_response_time_header(self) -> None:
        """Test that X-Response-Time-Ms header is added."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/users"
        
        mock_response = Response(content="OK", status_code=200)
        call_next = AsyncMock(return_value=mock_response)
        
        with patch("app.middleware.metrics.get_metrics_service"):
            response = await middleware.dispatch(mock_request, call_next)
            
            # Should have timing header
            assert "X-Response-Time-Ms" in response.headers
            timing = float(response.headers["X-Response-Time-Ms"])
            assert timing >= 0

    @pytest.mark.asyncio
    async def test_success_with_201_status(self) -> None:
        """Test successful request with 201 status."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/users"
        
        mock_response = Response(content="Created", status_code=201)
        call_next = AsyncMock(return_value=mock_response)
        
        mock_service = MagicMock()
        
        with patch("app.middleware.metrics.get_metrics_service", return_value=mock_service):
            response = await middleware.dispatch(mock_request, call_next)
            
            # Should record response time but not error
            mock_service.record_response_time.assert_called_once()
            mock_service.record_error.assert_not_called()
            assert response.status_code == 201


class TestMetricsMiddlewareErrorHandling:
    """Tests for error metrics."""

    @pytest.mark.asyncio
    async def test_records_error_for_500_response(self) -> None:
        """Test that 5xx responses record errors."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/users"
        
        mock_response = Response(content="Error", status_code=500)
        call_next = AsyncMock(return_value=mock_response)
        
        mock_service = MagicMock()
        
        with patch("app.middleware.metrics.get_metrics_service", return_value=mock_service):
            response = await middleware.dispatch(mock_request, call_next)
            
            # Should record both response time and error
            mock_service.record_response_time.assert_called_once()
            mock_service.record_error.assert_called_once()
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_records_error_for_503_response(self) -> None:
        """Test that 503 response records error."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/users"
        
        mock_response = Response(content="Service Unavailable", status_code=503)
        call_next = AsyncMock(return_value=mock_response)
        
        mock_service = MagicMock()
        
        with patch("app.middleware.metrics.get_metrics_service", return_value=mock_service):
            response = await middleware.dispatch(mock_request, call_next)
            
            mock_service.record_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_error_for_4xx_response(self) -> None:
        """Test that 4xx responses don't record errors."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/users"
        
        mock_response = Response(content="Not Found", status_code=404)
        call_next = AsyncMock(return_value=mock_response)
        
        mock_service = MagicMock()
        
        with patch("app.middleware.metrics.get_metrics_service", return_value=mock_service):
            response = await middleware.dispatch(mock_request, call_next)
            
            # Should record response time but not error
            mock_service.record_response_time.assert_called_once()
            mock_service.record_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_handling(self) -> None:
        """Test that exceptions are handled and metrics recorded."""
        app = MagicMock()
        middleware = MetricsMiddleware(app=app)
        
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/users"
        
        # Mock call_next that raises exception
        call_next = AsyncMock(side_effect=Exception("Test error"))
        
        mock_service = MagicMock()
        
        with patch("app.middleware.metrics.get_metrics_service", return_value=mock_service):
            with pytest.raises(Exception, match="Test error"):
                await middleware.dispatch(mock_request, call_next)
            
            # Should still record metrics even on exception
            mock_service.record_response_time.assert_called_once()
            mock_service.record_error.assert_called_once()


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
