# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for TenantMiddleware cookie-based token extraction."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.middleware.tenant import TenantMiddleware


class TestTenantMiddlewareCookieExtraction:
    """Test that TenantMiddleware extracts tenant_id from cookies."""

    def setup_method(self):
        """Create middleware instance."""
        self.app = MagicMock()
        self.middleware = TenantMiddleware(self.app)

    def test_extract_from_bearer_header(self):
        """Bearer header takes priority over cookies."""
        tenant_id = str(uuid4())
        scope = {
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer valid-token"),
            ],
        }

        with patch(
            "app.middleware.tenant.decode_token",
            return_value={"tenant_id": tenant_id},
        ):
            result = self.middleware._extract_tenant_id(scope)
            assert result is not None
            assert str(result) == tenant_id

    def test_extract_from_cookie_when_no_bearer(self):
        """Falls back to access_token cookie when no Bearer header."""
        tenant_id = str(uuid4())
        scope = {
            "type": "http",
            "headers": [
                (b"cookie", b"access_token=cookie-token; other=value"),
            ],
        }

        with patch(
            "app.middleware.tenant.decode_token",
            return_value={"tenant_id": tenant_id},
        ):
            result = self.middleware._extract_tenant_id(scope)
            assert result is not None
            assert str(result) == tenant_id

    def test_no_token_at_all(self):
        """Returns None when neither Bearer nor cookie is present."""
        scope = {
            "type": "http",
            "headers": [],
        }
        result = self.middleware._extract_tenant_id(scope)
        assert result is None

    def test_bearer_takes_priority_over_cookie(self):
        """When both present, Bearer header is used, not cookie."""
        bearer_tenant = str(uuid4())
        cookie_tenant = str(uuid4())
        scope = {
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer bearer-token"),
                (b"cookie", b"access_token=cookie-token"),
            ],
        }

        call_count = 0

        def mock_decode(token):
            nonlocal call_count
            call_count += 1
            if token == "bearer-token":
                return {"tenant_id": bearer_tenant}
            return {"tenant_id": cookie_tenant}

        with patch("app.middleware.tenant.decode_token", side_effect=mock_decode):
            result = self.middleware._extract_tenant_id(scope)
            assert str(result) == bearer_tenant

    def test_invalid_token_returns_none(self):
        """Invalid token (decode failure) returns None gracefully."""
        scope = {
            "type": "http",
            "headers": [
                (b"cookie", b"access_token=bad-token"),
            ],
        }

        with patch(
            "app.middleware.tenant.decode_token",
            side_effect=Exception("Invalid token"),
        ):
            result = self.middleware._extract_tenant_id(scope)
            assert result is None

    def test_no_tenant_id_in_payload(self):
        """Token valid but no tenant_id claim returns None."""
        scope = {
            "type": "http",
            "headers": [
                (b"cookie", b"access_token=valid-no-tenant"),
            ],
        }

        with patch(
            "app.middleware.tenant.decode_token",
            return_value={"sub": str(uuid4())},
        ):
            result = self.middleware._extract_tenant_id(scope)
            assert result is None
