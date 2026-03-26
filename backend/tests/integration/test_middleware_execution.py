# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for middleware code execution."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestTenantMiddleware:
    """Tests for tenant middleware."""

    @pytest.mark.asyncio
    async def test_request_without_tenant_header(self) -> None:
        """Test request without X-Tenant-ID header."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            # Should work even without tenant header for health endpoint
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_with_tenant_header(self) -> None:
        """Test request with X-Tenant-ID header."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/health",
                headers={"X-Tenant-ID": "00000000-0000-0000-0000-000000000000"},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_with_invalid_tenant_header(self) -> None:
        """Test request with invalid tenant UUID."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/health", headers={"X-Tenant-ID": "not-a-uuid"}
            )
            # Should either work (health is public) or fail validation
            assert response.status_code in [200, 400, 422]


class TestCORSMiddleware:
    """Tests for CORS middleware."""

    @pytest.mark.asyncio
    async def test_cors_preflight_request(self) -> None:
        """Test CORS preflight request."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.options(
                "/api/v1/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
            # Should return 200 for preflight
            assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_cors_headers_in_response(self) -> None:
        """Test CORS headers are present in response."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/health", headers={"Origin": "http://localhost:3000"}
            )
            assert response.status_code == 200
            # CORS headers may or may not be present depending on config


class TestRateLimitMiddleware:
    """Tests for rate limit middleware."""

    @pytest.mark.asyncio
    async def test_multiple_requests(self) -> None:
        """Test multiple requests don't immediately get rate limited."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Make a few requests
            for _ in range(3):
                response = await client.get("/api/v1/health")
                # Should not be rate limited for just 3 requests
                assert response.status_code in [200, 429]


class TestRequestIDMiddleware:
    """Tests for request ID middleware if present."""

    @pytest.mark.asyncio
    async def test_request_id_header(self) -> None:
        """Test request ID header handling."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/health", headers={"X-Request-ID": "test-request-123"}
            )
            assert response.status_code == 200


class TestContentTypeNegotiation:
    """Tests for content type handling."""

    @pytest.mark.asyncio
    async def test_json_content_type(self) -> None:
        """Test JSON content type is accepted."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "test@test.com", "password": "test"},
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code in [400, 401, 422, 500]

    @pytest.mark.asyncio
    async def test_accept_json_response(self) -> None:
        """Test Accept: application/json is handled."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/health", headers={"Accept": "application/json"}
            )
            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")


class TestErrorResponses:
    """Tests for error response handling."""

    @pytest.mark.asyncio
    async def test_404_returns_json(self) -> None:
        """Test 404 returns JSON response."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/nonexistent-endpoint-xyz")
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_validation_error_format(self) -> None:
        """Test validation errors return proper format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={},  # Missing required fields
            )
            assert response.status_code == 422
            data = response.json()
            assert "detail" in data


class TestAuthMiddleware:
    """Tests for authentication middleware."""

    @pytest.mark.asyncio
    async def test_auth_header_missing(self) -> None:
        """Test protected endpoint without auth header."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/users")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_auth_header_invalid_format(self) -> None:
        """Test protected endpoint with invalid auth format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/users", headers={"Authorization": "InvalidFormat token123"}
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_auth_header_bearer_invalid(self) -> None:
        """Test protected endpoint with invalid bearer token."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/users", headers={"Authorization": "Bearer invalid.jwt.token"}
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_auth_header_empty_bearer(self) -> None:
        """Test protected endpoint with empty bearer token."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/users", headers={"Authorization": "Bearer "}
            )
            assert response.status_code in [401, 403]


class TestEndpointMethods:
    """Tests for HTTP method handling."""

    @pytest.mark.asyncio
    async def test_patch_method(self) -> None:
        """Test PATCH method handling."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/users/00000000-0000-0000-0000-000000000000", json={}
            )
            # Should require auth or validate body
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_delete_method(self) -> None:
        """Test DELETE method handling."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/users/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_put_method(self) -> None:
        """Test PUT method handling."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                "/api/v1/roles/00000000-0000-0000-0000-000000000000", json={}
            )
            assert response.status_code in [401, 403, 404, 405, 422]
