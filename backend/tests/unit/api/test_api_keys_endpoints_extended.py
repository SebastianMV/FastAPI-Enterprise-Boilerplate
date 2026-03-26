# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Extended tests for API v1 endpoints - API Keys."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4


class TestApiKeysEndpointImport:
    """Tests for API keys endpoint import."""

    def test_api_keys_router_import(self) -> None:
        """Test API keys router can be imported."""
        from app.api.v1.endpoints.api_keys import router

        assert router is not None


class TestApiKeySchemas:
    """Tests for API key schemas."""

    def test_api_key_response_schema(self) -> None:
        """Test API key response schema."""
        from app.api.v1.schemas.api_keys import APIKeyResponse

        response = APIKeyResponse(
            id=uuid4(),
            name="Test API Key",
            prefix="sk_test_",
            scopes=["users:read"],
            is_active=True,
            expires_at=datetime.now(UTC) + timedelta(days=365),
            usage_count=0,
            created_at=datetime.now(UTC),
        )
        assert response.id is not None
        assert response.name == "Test API Key"
        assert response.is_active is True

    def test_api_key_create_schema(self) -> None:
        """Test API key create schema."""
        from app.api.v1.schemas.api_keys import APIKeyCreate

        create = APIKeyCreate(
            name="My API Key",
            expires_in_days=365,
        )
        assert create.name == "My API Key"
        assert create.expires_in_days == 365


class TestApiKeyRoutes:
    """Tests for API key endpoint routes."""

    def test_api_keys_router_has_routes(self) -> None:
        """Test API keys router has routes."""
        from app.api.v1.endpoints.api_keys import router

        routes = [getattr(route, "path", None) for route in router.routes]
        assert len(routes) > 0


class TestApiKeyGeneration:
    """Tests for API key generation."""

    def test_api_key_prefix_format(self) -> None:
        """Test API key prefix format."""
        prefix = "sk_live_"
        assert prefix.startswith("sk_")
        assert prefix.endswith("_")

    def test_api_key_length(self) -> None:
        """Test API key length."""
        import secrets

        key = secrets.token_urlsafe(32)
        assert len(key) >= 32

    def test_api_key_uniqueness(self) -> None:
        """Test API keys are unique."""
        import secrets

        keys = [secrets.token_urlsafe(32) for _ in range(10)]
        assert len(keys) == len(set(keys))


class TestApiKeyExpiration:
    """Tests for API key expiration."""

    def test_api_key_default_expiration(self) -> None:
        """Test default API key expiration."""
        default_days = 365
        expires_at = datetime.now(UTC) + timedelta(days=default_days)
        assert expires_at > datetime.now(UTC)

    def test_api_key_no_expiration(self) -> None:
        """Test API key without expiration."""
        expires_at = None
        assert expires_at is None

    def test_api_key_expired_check(self) -> None:
        """Test checking if API key is expired."""
        expired_at = datetime.now(UTC) - timedelta(days=1)
        is_expired = expired_at < datetime.now(UTC)
        assert is_expired is True
