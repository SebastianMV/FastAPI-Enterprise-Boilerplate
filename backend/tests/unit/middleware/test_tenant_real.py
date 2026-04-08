# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for tenant middleware with real execution."""

from __future__ import annotations

from uuid import uuid4


class TestTenantContextFunctions:
    """Tests for tenant context functions."""

    def test_get_current_tenant_id_import(self) -> None:
        """Test get_current_tenant_id can be imported."""
        from app.middleware.tenant import get_current_tenant_id

        assert get_current_tenant_id is not None
        assert callable(get_current_tenant_id)

    def test_set_current_tenant_id_import(self) -> None:
        """Test set_current_tenant_id can be imported."""
        from app.middleware.tenant import set_current_tenant_id

        assert set_current_tenant_id is not None
        assert callable(set_current_tenant_id)

    def test_get_tenant_id_default_none(self) -> None:
        """Test get_current_tenant_id returns None by default."""
        from app.middleware.tenant import get_current_tenant_id, set_current_tenant_id

        # Reset to None first
        set_current_tenant_id(None)
        result = get_current_tenant_id()
        assert result is None

    def test_set_and_get_tenant_id(self) -> None:
        """Test set and get tenant_id."""
        from app.middleware.tenant import get_current_tenant_id, set_current_tenant_id

        tenant_id = uuid4()
        set_current_tenant_id(tenant_id)
        result = get_current_tenant_id()
        assert result == tenant_id

        # Cleanup
        set_current_tenant_id(None)


class TestTenantMiddlewareClass:
    """Tests for TenantMiddleware class."""

    def test_middleware_import(self) -> None:
        """Test TenantMiddleware can be imported."""
        from app.middleware.tenant import TenantMiddleware

        assert TenantMiddleware is not None

    def test_middleware_has_exempt_paths(self) -> None:
        """Test TenantMiddleware has EXEMPT_PATHS."""
        from app.middleware.tenant import TenantMiddleware

        assert hasattr(TenantMiddleware, "EXEMPT_PATHS")
        assert isinstance(TenantMiddleware.EXEMPT_PATHS, set)

    def test_exempt_paths_include_health(self) -> None:
        """Test EXEMPT_PATHS includes health endpoints."""
        from app.middleware.tenant import TenantMiddleware

        assert "/health" in TenantMiddleware.EXEMPT_PATHS
        assert "/health/live" in TenantMiddleware.EXEMPT_PATHS

    def test_exempt_paths_include_docs(self) -> None:
        """Test EXEMPT_PATHS includes documentation."""
        from app.middleware.tenant import TenantMiddleware

        assert "/docs" in TenantMiddleware.EXEMPT_PATHS
        assert "/openapi.json" in TenantMiddleware.EXEMPT_PATHS

    def test_exempt_paths_include_auth(self) -> None:
        """Test EXEMPT_PATHS includes auth endpoints."""
        from app.middleware.tenant import TenantMiddleware

        assert "/api/v1/auth/login" in TenantMiddleware.EXEMPT_PATHS
        assert "/api/v1/auth/register" in TenantMiddleware.EXEMPT_PATHS


class TestRateLimitMiddleware:
    """Tests for rate limit middleware."""

    def test_rate_limit_import(self) -> None:
        """Test rate limit module can be imported."""
        from app.middleware import rate_limit

        assert rate_limit is not None

    def test_rate_limit_middleware_class(self) -> None:
        """Test RateLimitMiddleware exists."""
        from app.middleware.rate_limit import RateLimitMiddleware

        assert RateLimitMiddleware is not None


class TestI18nMiddleware:
    """Tests for i18n middleware."""

    def test_i18n_import(self) -> None:
        """Test i18n module can be imported."""
        from app.middleware import i18n

        assert i18n is not None


class TestMiddlewareInit:
    """Tests for middleware __init__."""

    def test_middleware_package_import(self) -> None:
        """Test middleware package can be imported."""
        from app import middleware

        assert middleware is not None
