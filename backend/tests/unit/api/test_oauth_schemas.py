# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for OAuth endpoint schemas and validation."""

from __future__ import annotations

from uuid import uuid4
from datetime import datetime, UTC
import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.oauth import (
    OAuthAuthorizeResponse,
    OAuthConnectionResponse,
    OAuthTokenResponse,
    SSOConfigRequest,
)
from app.domain.entities.oauth import OAuthProvider


class TestOAuthAuthorizeResponse:
    """Tests for OAuthAuthorizeResponse schema."""

    def test_authorize_response(self) -> None:
        """Test authorize response."""
        data = OAuthAuthorizeResponse(
            authorization_url="https://accounts.google.com/oauth/authorize?...",
            state="random_state_123"
        )
        assert "google" in data.authorization_url
        assert data.state == "random_state_123"

    def test_authorize_response_github(self) -> None:
        """Test authorize response for GitHub."""
        data = OAuthAuthorizeResponse(
            authorization_url="https://github.com/login/oauth/authorize",
            state="state_456"
        )
        assert data.state == "state_456"


class TestOAuthTokenResponse:
    """Tests for OAuthTokenResponse schema."""

    def test_token_response(self) -> None:
        """Test token response."""
        user_id = uuid4()
        data = OAuthTokenResponse(
            access_token="access_123",
            refresh_token="refresh_456",
            expires_in=3600,
            user_id=user_id,
            is_new_user=False,
        )
        assert data.access_token == "access_123"
        assert data.user_id == user_id

    def test_token_response_new_user(self) -> None:
        """Test token response for new user."""
        data = OAuthTokenResponse(
            access_token="access_abc",
            refresh_token="refresh_xyz",
            expires_in=7200,
            user_id=uuid4(),
            is_new_user=True,
        )
        assert data.is_new_user is True

    def test_token_response_token_type(self) -> None:
        """Test token response default token type."""
        data = OAuthTokenResponse(
            access_token="token",
            refresh_token="refresh",
            expires_in=3600,
            user_id=uuid4(),
            is_new_user=False,
        )
        assert data.token_type == "bearer"


class TestOAuthConnectionResponse:
    """Tests for OAuthConnectionResponse schema."""

    def test_connection_response(self) -> None:
        """Test connection response."""
        conn_id = uuid4()
        data = OAuthConnectionResponse(
            id=conn_id,
            provider="google",
            provider_email="user@gmail.com",
            is_primary=True,
            created_at=datetime.now(UTC),
        )
        assert data.id == conn_id
        assert data.provider == "google"

    def test_connection_response_with_name(self) -> None:
        """Test connection response with display name."""
        data = OAuthConnectionResponse(
            id=uuid4(),
            provider="github",
            provider_email="user@github.com",
            provider_display_name="GitHub User",
            is_primary=False,
            created_at=datetime.now(UTC),
        )
        assert data.provider_display_name == "GitHub User"

    def test_connection_response_minimal(self) -> None:
        """Test connection response with minimal data."""
        data = OAuthConnectionResponse(
            id=uuid4(),
            provider="microsoft",
            is_primary=False,
        )
        assert data.provider_email is None


class TestSSOConfigRequest:
    """Tests for SSOConfigRequest schema."""

    def test_sso_config_minimal(self) -> None:
        """Test SSO config with minimal fields."""
        data = SSOConfigRequest(
            provider="google",
            name="Corporate SSO",
            client_id="client_123",
            client_secret="secret_456",
        )
        assert data.provider == "google"
        assert data.auto_create_users is True

    def test_sso_config_full(self) -> None:
        """Test SSO config with all fields."""
        role_id = uuid4()
        data = SSOConfigRequest(
            provider="okta",
            name="Company Okta",
            client_id="okta_client",
            client_secret="okta_secret",
            scopes=["openid", "profile", "email"],
            auto_create_users=False,
            auto_update_users=False,
            default_role_id=role_id,
            allowed_domains=["company.com", "company.org"],
            is_required=True,
        )
        assert data.is_required is True
        assert "company.com" in data.allowed_domains

    def test_sso_config_empty_name_fails(self) -> None:
        """Test SSO config with empty name fails."""
        with pytest.raises(ValidationError):
            SSOConfigRequest(
                provider="google",
                name="",
                client_id="client",
                client_secret="secret",
            )


class TestOAuthProviderEnum:
    """Tests for OAuthProvider enum."""

    def test_google_provider(self) -> None:
        """Test Google provider."""
        assert OAuthProvider.GOOGLE is not None
        assert OAuthProvider.GOOGLE.value == "google"

    def test_github_provider(self) -> None:
        """Test GitHub provider."""
        assert OAuthProvider.GITHUB is not None
        assert OAuthProvider.GITHUB.value == "github"

    def test_microsoft_provider(self) -> None:
        """Test Microsoft provider."""
        assert OAuthProvider.MICROSOFT is not None
        assert OAuthProvider.MICROSOFT.value == "microsoft"

    def test_apple_provider(self) -> None:
        """Test Apple provider."""
        assert OAuthProvider.APPLE is not None
        assert OAuthProvider.APPLE.value == "apple"

    def test_okta_provider(self) -> None:
        """Test Okta provider."""
        assert OAuthProvider.OKTA is not None
        assert OAuthProvider.OKTA.value == "okta"


class TestOAuthRouter:
    """Tests for OAuth router configuration."""

    def test_router_exists(self) -> None:
        """Test router exists."""
        from app.api.v1.endpoints.oauth import router
        assert router is not None

    def test_router_prefix(self) -> None:
        """Test router prefix."""
        from app.api.v1.endpoints.oauth import router
        assert router.prefix == "/auth/oauth"

    def test_router_has_routes(self) -> None:
        """Test router has routes."""
        from app.api.v1.endpoints.oauth import router
        assert len(router.routes) > 0
