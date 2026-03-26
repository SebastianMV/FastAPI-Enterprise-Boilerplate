# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Tests for Security Headers Middleware.

Verifies that all required security headers are properly set.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.middleware.security_headers import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    """Tests for security headers middleware."""

    @pytest.mark.asyncio
    async def test_security_headers_present_on_root(self):
        """Verify all security headers are present on root endpoint."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")

        # Check all required security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "0"

        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_security_headers_present_on_api_endpoints(self):
        """Verify security headers on API endpoints."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/health")

        # Security headers should be on all responses
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers

    @pytest.mark.asyncio
    async def test_security_headers_on_error_responses(self):
        """Verify security headers are present even on error responses."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/nonexistent-endpoint-12345")

        # Even 404 responses should have security headers
        assert response.status_code == 404
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers

    @pytest.mark.asyncio
    async def test_csp_header_contains_required_directives(self):
        """Verify CSP header contains essential directives."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")

        csp = response.headers.get("Content-Security-Policy", "")

        # Check for essential directives
        assert "default-src" in csp
        assert "script-src" in csp
        assert "frame-ancestors" in csp

    @pytest.mark.asyncio
    async def test_permissions_policy_restricts_features(self):
        """Verify Permissions-Policy restricts dangerous features."""
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")

        permissions = response.headers.get("Permissions-Policy", "")

        # Should restrict sensitive features
        assert "camera=()" in permissions
        assert "microphone=()" in permissions
        assert "geolocation=()" in permissions


class TestSecurityHeadersConfiguration:
    """Tests for middleware configuration options."""

    def test_hsts_header_construction(self):
        """Test HSTS header value is correctly constructed."""
        middleware = SecurityHeadersMiddleware(
            app=None,
            hsts_enabled=True,
            hsts_max_age=31536000,
            hsts_include_subdomains=True,
            hsts_preload=False,
        )

        assert "max-age=31536000" in middleware.hsts_value
        assert "includeSubDomains" in middleware.hsts_value
        assert "preload" not in middleware.hsts_value

    def test_hsts_with_preload(self):
        """Test HSTS header includes preload when enabled."""
        middleware = SecurityHeadersMiddleware(
            app=None,
            hsts_enabled=True,
            hsts_max_age=31536000,
            hsts_include_subdomains=True,
            hsts_preload=True,
        )

        assert "preload" in middleware.hsts_value

    def test_custom_frame_options(self):
        """Test custom X-Frame-Options value."""
        middleware = SecurityHeadersMiddleware(
            app=None,
            frame_options="SAMEORIGIN",
        )

        assert middleware.frame_options == "SAMEORIGIN"

    def test_custom_csp_policy(self):
        """Test custom CSP policy is used."""
        custom_csp = "default-src 'none'; script-src 'self'"
        middleware = SecurityHeadersMiddleware(
            app=None,
            csp_policy=custom_csp,
        )

        assert middleware.csp_policy == custom_csp

    def test_default_csp_policy_generated(self):
        """Test default CSP policy is generated when none provided."""
        middleware = SecurityHeadersMiddleware(app=None)

        assert middleware.csp_policy is not None
        assert "default-src" in middleware.csp_policy
