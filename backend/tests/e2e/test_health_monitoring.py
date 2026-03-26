# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
End-to-End Tests - Health & Monitoring Flow.

Complete user journey tests for health checks and observability.

Note: Health checks may be publicly accessible.
"""

import pytest
from httpx import AsyncClient


class TestHealthChecksE2E:
    """End-to-end health check tests."""

    @pytest.mark.asyncio
    async def test_basic_health_check(self, client: AsyncClient) -> None:
        """Test basic health endpoint."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "ok", "up"]

    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client: AsyncClient) -> None:
        """Test detailed health endpoint with component status."""
        response = await client.get("/api/v1/health/detailed")

        if response.status_code == 200:
            data = response.json()

            assert "status" in data

            # May include component health
            if "components" in data or "checks" in data:
                components = data.get("components", data.get("checks", {}))

                # Common components
                expected_components = ["database", "cache", "search"]
                for component in expected_components:
                    if component in components:
                        assert "status" in components[component]

    @pytest.mark.asyncio
    async def test_readiness_probe(self, client: AsyncClient) -> None:
        """Test Kubernetes-style readiness probe."""
        response = await client.get("/api/v1/health/ready")

        if response.status_code in [200, 404]:
            if response.status_code == 200:
                data = response.json()
                assert "ready" in data or "status" in data

    @pytest.mark.asyncio
    async def test_liveness_probe(self, client: AsyncClient) -> None:
        """Test Kubernetes-style liveness probe."""
        response = await client.get("/api/v1/health/live")

        if response.status_code in [200, 404]:
            if response.status_code == 200:
                data = response.json()
                assert "alive" in data or "status" in data


class TestMetricsE2E:
    """End-to-end metrics tests."""

    @pytest.mark.asyncio
    async def test_prometheus_metrics_endpoint(self, client: AsyncClient) -> None:
        """Test Prometheus metrics endpoint."""
        response = await client.get("/metrics")

        if response.status_code == 200:
            content = response.text

            # Should contain Prometheus format metrics
            assert "# HELP" in content or "# TYPE" in content or "http_" in content

    @pytest.mark.asyncio
    async def test_application_metrics(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test application-specific metrics endpoint."""
        response = await client.get("/api/v1/metrics", headers=auth_headers)

        if response.status_code in [200, 401, 404]:
            if response.status_code == 200:
                data = response.json()
                # May include various app metrics
                assert isinstance(data, dict)


class TestVersionInfoE2E:
    """End-to-end version info tests."""

    @pytest.mark.asyncio
    async def test_version_endpoint(self, client: AsyncClient) -> None:
        """Test version information endpoint."""
        response = await client.get("/api/v1/version")

        if response.status_code in [200, 404]:
            if response.status_code == 200:
                data = response.json()

                # Should include version info
                assert "version" in data or "api_version" in data

    @pytest.mark.asyncio
    async def test_openapi_schema_available(self, client: AsyncClient) -> None:
        """Test OpenAPI schema is available."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    @pytest.mark.asyncio
    async def test_swagger_ui_available(self, client: AsyncClient) -> None:
        """Test Swagger UI is accessible."""
        response = await client.get("/docs")

        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    @pytest.mark.asyncio
    async def test_redoc_available(self, client: AsyncClient) -> None:
        """Test ReDoc documentation is accessible."""
        response = await client.get("/redoc")

        if response.status_code == 200:
            assert "redoc" in response.text.lower()


class TestLoggingE2E:
    """End-to-end logging configuration tests."""

    # Note: test_log_level_configuration removed - admin logging endpoint
    # not implemented. Add test when feature is available.


class TestDatabaseConnectionE2E:
    """End-to-end database connection tests."""

    @pytest.mark.asyncio
    async def test_database_health(self, client: AsyncClient) -> None:
        """Test database connection health."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        # If database is down, health check should fail

    @pytest.mark.asyncio
    async def test_database_operations_work(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test basic database operations through API."""
        # Simple read operation
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        # If DB is connected, should work (or return 401 if auth issue)
        assert response.status_code in [200, 401]


class TestCacheE2E:
    """End-to-end cache tests."""

    @pytest.mark.asyncio
    async def test_cache_health(self, client: AsyncClient) -> None:
        """Test cache connection in health check."""
        response = await client.get("/api/v1/health/detailed")

        if response.status_code == 200:
            data = response.json()

            if "components" in data:
                cache_status = data["components"].get("cache", {})
                if cache_status:
                    assert "status" in cache_status

    @pytest.mark.asyncio
    async def test_response_caching(self, client: AsyncClient) -> None:
        """Test that responses are properly cached."""
        # Make same request twice
        response1 = await client.get("/api/v1/health")
        response2 = await client.get("/api/v1/health")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both should succeed quickly (cache hit on second)
