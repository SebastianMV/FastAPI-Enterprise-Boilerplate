# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Unit tests for Tenant middleware."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.middleware.tenant import (
    TenantContextManager,
    TenantMiddleware,
    get_current_tenant_id,
    require_tenant_context,
    set_current_tenant_id,
)


class TestTenantContext:
    """Tests for tenant context functions."""

    def test_get_set_tenant_id(self):
        """Test getting and setting tenant ID."""
        tenant_id = uuid4()

        # Initially None
        assert get_current_tenant_id() is None

        # Set tenant
        set_current_tenant_id(tenant_id)
        assert get_current_tenant_id() == tenant_id

        # Clear tenant
        set_current_tenant_id(None)
        assert get_current_tenant_id() is None


class TestTenantContextManager:
    """Tests for TenantContextManager."""

    @pytest.mark.asyncio
    async def test_context_manager_sets_tenant(self):
        """Test context manager sets and clears tenant."""
        tenant_id = uuid4()

        assert get_current_tenant_id() is None

        async with TenantContextManager(tenant_id):
            assert get_current_tenant_id() == tenant_id

        # Context should be cleared after exit
        assert get_current_tenant_id() is None

    @pytest.mark.asyncio
    async def test_context_manager_clears_on_exception(self):
        """Test context manager clears tenant on exception."""
        tenant_id = uuid4()

        with pytest.raises(ValueError):
            async with TenantContextManager(tenant_id):
                assert get_current_tenant_id() == tenant_id
                raise ValueError("Test error")

        # Context should be cleared after exception
        assert get_current_tenant_id() is None


class TestTenantMiddleware:
    """Tests for TenantMiddleware."""

    def test_exempt_paths(self):
        """Test exempt paths are identified correctly."""
        middleware = TenantMiddleware(app=MagicMock())

        # Exact matches
        assert middleware._is_exempt_path("/health") is True
        assert middleware._is_exempt_path("/docs") is True
        assert middleware._is_exempt_path("/api/v1/auth/login") is True

        # Not exempt
        assert middleware._is_exempt_path("/api/v1/users") is False
        assert middleware._is_exempt_path("/api/v1/tenants") is False

    def test_extract_tenant_id_no_header(self):
        """Test extracting tenant when no auth header."""
        middleware = TenantMiddleware(app=MagicMock())

        scope = {"headers": []}

        result = middleware._extract_tenant_id(scope)
        assert result is None

    def test_extract_tenant_id_invalid_token(self):
        """Test extracting tenant with invalid token."""
        middleware = TenantMiddleware(app=MagicMock())

        scope = {"headers": [(b"authorization", b"Bearer invalid_token")]}

        result = middleware._extract_tenant_id(scope)
        assert result is None

    @patch("app.middleware.tenant.decode_token")
    def test_extract_tenant_id_valid_token(self, mock_decode):
        """Test extracting tenant with valid token."""
        tenant_id = uuid4()
        mock_decode.return_value = {"tenant_id": str(tenant_id)}

        middleware = TenantMiddleware(app=MagicMock())

        scope = {"headers": [(b"authorization", b"Bearer valid_token")]}

        result = middleware._extract_tenant_id(scope)
        assert result == tenant_id

    @patch("app.middleware.tenant.decode_token")
    def test_extract_tenant_id_no_tenant_in_token(self, mock_decode):
        """Test extracting tenant when token has no tenant_id."""
        mock_decode.return_value = {"sub": "user_id"}

        middleware = TenantMiddleware(app=MagicMock())

        scope = {"headers": [(b"authorization", b"Bearer valid_token")]}

        result = middleware._extract_tenant_id(scope)
        assert result is None


class TestRequireTenantContext:
    """Tests for require_tenant_context dependency."""

    def test_require_tenant_with_context(self):
        """Test require_tenant_context with valid context."""
        tenant_id = uuid4()
        set_current_tenant_id(tenant_id)

        try:
            request = MagicMock()
            result = require_tenant_context(request)
            assert result == tenant_id
        finally:
            set_current_tenant_id(None)

    def test_require_tenant_from_request_state(self):
        """Test require_tenant_context falls back to request.state."""
        tenant_id = uuid4()

        request = MagicMock()
        request.state.tenant_id = tenant_id

        result = require_tenant_context(request)
        assert result == tenant_id

    def test_require_tenant_no_context(self):
        """Test require_tenant_context raises without context."""
        from fastapi import HTTPException

        request = MagicMock()
        request.state = MagicMock(spec=[])  # No tenant_id attribute

        with pytest.raises(HTTPException) as exc_info:
            require_tenant_context(request)

        assert exc_info.value.status_code == 400
        assert "Tenant context required" in str(exc_info.value.detail)


class TestTenantMiddlewareDispatch:
    """Tests for TenantMiddleware ASGI call method."""

    @pytest.mark.asyncio
    async def test_dispatch_exempt_path_bypasses_tenant_extraction(self):
        """Test dispatch skips tenant extraction for exempt paths."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        app.add_middleware(TenantMiddleware)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.middleware.tenant.decode_token")
    async def test_dispatch_sets_tenant_context(self, mock_decode):
        """Test dispatch sets tenant context for non-exempt paths."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        tenant_id = uuid4()
        mock_decode.return_value = {"tenant_id": str(tenant_id)}

        captured_tenant = None

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            nonlocal captured_tenant
            captured_tenant = get_current_tenant_id()
            return {"ok": True}

        app.add_middleware(TenantMiddleware)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/users", headers={"Authorization": "Bearer valid_token"}
            )

        assert response.status_code == 200
        assert captured_tenant == tenant_id

    @pytest.mark.asyncio
    async def test_dispatch_no_auth_header_sets_none_tenant(self):
        """Test dispatch sets None tenant when no auth header."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        captured_tenant = "not_set"

        app = FastAPI()

        @app.get("/api/v1/users")
        async def users():
            nonlocal captured_tenant
            captured_tenant = get_current_tenant_id()
            return {"ok": True}

        app.add_middleware(TenantMiddleware)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/users")

        assert response.status_code == 200
        assert captured_tenant is None
