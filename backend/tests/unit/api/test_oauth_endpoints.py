# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for OAuth API endpoints schemas.

Tests for OAuth endpoint request/response schemas.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError


class TestOAuthConnectionResponse:
    """Tests for OAuthConnectionResponse schema."""

    def test_oauth_connection_response_full(self) -> None:
        """Test OAuthConnectionResponse with all fields."""
        from app.api.v1.endpoints.oauth import OAuthConnectionResponse

        response = OAuthConnectionResponse(
            id=uuid4(),
            provider="google",
            provider_email="user@gmail.com",
            provider_username="testuser",
            provider_display_name="Test User",
            provider_avatar_url="https://example.com/avatar.jpg",
            is_primary=True,
            last_used_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        assert response.provider == "google"
        assert response.is_primary is True
        assert response.provider_email == "user@gmail.com"

    def test_oauth_connection_response_minimal(self) -> None:
        """Test OAuthConnectionResponse with minimal fields."""
        from app.api.v1.endpoints.oauth import OAuthConnectionResponse

        response = OAuthConnectionResponse(
            id=uuid4(),
            provider="github",
            is_primary=False,
        )

        assert response.provider == "github"
        assert response.provider_email is None
        assert response.provider_avatar_url is None


class TestOAuthAuthorizeResponse:
    """Tests for OAuthAuthorizeResponse schema."""

    def test_oauth_authorize_response(self) -> None:
        """Test OAuthAuthorizeResponse schema."""
        from app.api.v1.endpoints.oauth import OAuthAuthorizeResponse

        response = OAuthAuthorizeResponse(
            authorization_url="https://accounts.google.com/o/oauth2/auth?...",
            state="random-state-string",
        )

        assert response.authorization_url.startswith("https://")
        assert len(response.state) > 0

    def test_oauth_authorize_response_with_long_url(self) -> None:
        """Test OAuthAuthorizeResponse with complex URL."""
        from app.api.v1.endpoints.oauth import OAuthAuthorizeResponse

        long_url = (
            "https://accounts.google.com/o/oauth2/auth?"
            "client_id=123456.apps.googleusercontent.com&"
            "redirect_uri=https://app.example.com/callback&"
            "scope=email+profile+openid&"
            "response_type=code&"
            "state=xyz123"
        )

        response = OAuthAuthorizeResponse(
            authorization_url=long_url,
            state="xyz123",
        )

        assert "client_id" in response.authorization_url
        assert "redirect_uri" in response.authorization_url


class TestOAuthTokenResponse:
    """Tests for OAuthTokenResponse schema."""

    def test_oauth_token_response_new_user(self) -> None:
        """Test OAuthTokenResponse for new user."""
        from app.api.v1.endpoints.oauth import OAuthTokenResponse

        response = OAuthTokenResponse(
            access_token="access-token-value",
            refresh_token="refresh-token-value",
            token_type="bearer",
            expires_in=3600,
            user_id=uuid4(),
            is_new_user=True,
        )

        assert response.is_new_user is True
        assert response.token_type == "bearer"
        assert response.expires_in == 3600

    def test_oauth_token_response_existing_user(self) -> None:
        """Test OAuthTokenResponse for existing user."""
        from app.api.v1.endpoints.oauth import OAuthTokenResponse

        response = OAuthTokenResponse(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=7200,
            user_id=uuid4(),
            is_new_user=False,
        )

        assert response.is_new_user is False


class TestSSOConfigRequest:
    """Tests for SSOConfigRequest schema."""

    def test_sso_config_request_full(self) -> None:
        """Test SSOConfigRequest with all fields."""
        from app.api.v1.endpoints.oauth import SSOConfigRequest

        request = SSOConfigRequest(
            provider="google",
            name="Google SSO",
            client_id="client-id-123",
            client_secret="client-secret-456",
            scopes=["email", "profile", "openid"],
            auto_create_users=True,
            auto_update_users=True,
            default_role_id=uuid4(),
            allowed_domains=["example.com", "corp.example.com"],
            is_required=False,
        )

        assert request.provider == "google"
        assert len(request.scopes) == 3
        assert len(request.allowed_domains) == 2

    def test_sso_config_request_minimal(self) -> None:
        """Test SSOConfigRequest with minimal required fields."""
        from app.api.v1.endpoints.oauth import SSOConfigRequest

        request = SSOConfigRequest(
            provider="github",
            name="GitHub SSO",
            client_id="github-client-id",
            client_secret="github-client-secret",
        )

        assert request.provider == "github"
        assert request.scopes == []
        assert request.auto_create_users is True

    def test_sso_config_request_empty_name_fails(self) -> None:
        """Test SSOConfigRequest fails with empty name."""
        from app.api.v1.endpoints.oauth import SSOConfigRequest

        with pytest.raises(ValidationError) as exc_info:
            SSOConfigRequest(
                provider="google",
                name="",  # Too short
                client_id="client-id",
                client_secret="client-secret",
            )

        assert "name" in str(exc_info.value)

    def test_sso_config_request_empty_client_id_fails(self) -> None:
        """Test SSOConfigRequest fails with empty client_id."""
        from app.api.v1.endpoints.oauth import SSOConfigRequest

        with pytest.raises(ValidationError) as exc_info:
            SSOConfigRequest(
                provider="google",
                name="Google SSO",
                client_id="",  # Too short
                client_secret="client-secret",
            )

        assert "client_id" in str(exc_info.value)


class TestSSOConfigResponse:
    """Tests for SSOConfigResponse schema."""

    def test_sso_config_response_full(self) -> None:
        """Test SSOConfigResponse with all fields."""
        from app.api.v1.endpoints.oauth import SSOConfigResponse

        response = SSOConfigResponse(
            id=uuid4(),
            provider="microsoft",
            name="Microsoft SSO",
            is_enabled=True,
            auto_create_users=True,
            auto_update_users=True,
            default_role_id=uuid4(),
            allowed_domains=["company.com"],
            is_required=True,
            created_at=datetime.now(UTC),
        )

        assert response.is_enabled is True
        assert response.is_required is True

    def test_sso_config_response_disabled(self) -> None:
        """Test SSOConfigResponse for disabled config."""
        from app.api.v1.endpoints.oauth import SSOConfigResponse

        response = SSOConfigResponse(
            id=uuid4(),
            provider="google",
            name="Google SSO",
            is_enabled=False,
            auto_create_users=False,
            auto_update_users=False,
            allowed_domains=[],
            is_required=False,
        )

        assert response.is_enabled is False
        assert len(response.allowed_domains) == 0


class TestOAuthProviders:
    """Tests for OAuth provider constants."""

    def test_supported_providers(self) -> None:
        """Test that common providers are supported."""
        from app.domain.entities.oauth import OAuthProvider

        supported = [p.value for p in OAuthProvider]

        assert "google" in supported
        assert "github" in supported
        assert "microsoft" in supported

    def test_oauth_provider_string_value(self) -> None:
        """Test OAuthProvider string conversion."""
        from app.domain.entities.oauth import OAuthProvider

        assert OAuthProvider.GOOGLE.value == "google"
        assert str(OAuthProvider.GITHUB) == "OAuthProvider.GITHUB"


class TestOAuthEndpointEdgeCases:
    """Tests for edge cases in OAuth endpoints."""

    def test_oauth_connection_multiple_providers(self) -> None:
        """Test user can have multiple OAuth connections."""
        from app.api.v1.endpoints.oauth import OAuthConnectionResponse

        # User connected with both Google and GitHub
        google_conn = OAuthConnectionResponse(
            id=uuid4(),
            provider="google",
            provider_email="user@gmail.com",
            is_primary=True,
        )

        github_conn = OAuthConnectionResponse(
            id=uuid4(),
            provider="github",
            provider_username="testuser",
            is_primary=False,
        )

        assert google_conn.is_primary is True
        assert github_conn.is_primary is False

    def test_oauth_token_expires_values(self) -> None:
        """Test various token expiration values."""
        from app.api.v1.endpoints.oauth import OAuthTokenResponse

        # Short lived token (15 minutes)
        short_token = OAuthTokenResponse(
            access_token="token",
            refresh_token="refresh",
            expires_in=900,
            user_id=uuid4(),
            is_new_user=False,
        )
        assert short_token.expires_in == 900

        # Long lived token (24 hours)
        long_token = OAuthTokenResponse(
            access_token="token",
            refresh_token="refresh",
            expires_in=86400,
            user_id=uuid4(),
            is_new_user=False,
        )
        assert long_token.expires_in == 86400

    def test_sso_config_domain_restrictions(self) -> None:
        """Test SSO config with domain restrictions."""
        from app.api.v1.endpoints.oauth import SSOConfigRequest

        request = SSOConfigRequest(
            provider="okta",
            name="Corporate SSO",
            client_id="okta-client",
            client_secret="okta-secret",
            allowed_domains=[
                "company.com",
                "subsidiary.company.com",
                "partner.org",
            ],
            is_required=True,
        )

        assert len(request.allowed_domains) == 3
        assert request.is_required is True


class TestOAuthSchemaFromAttributes:
    """Tests for schema from_attributes mode."""

    def test_oauth_connection_from_orm_object(self) -> None:
        """Test OAuthConnectionResponse can be created from ORM-like object."""
        from app.api.v1.endpoints.oauth import OAuthConnectionResponse

        # Simulate ORM object with attributes
        class MockConnection:
            id = uuid4()
            provider = "google"
            provider_email = "test@gmail.com"
            provider_username = None
            provider_display_name = "Test"
            provider_avatar_url = None
            is_primary = True
            last_used_at = datetime.now(UTC)
            created_at = datetime.now(UTC)

        # model_validate with from_attributes=True
        mock_obj = MockConnection()
        response = OAuthConnectionResponse.model_validate(mock_obj)

        assert response.provider == "google"
        assert response.is_primary is True

    def test_sso_config_from_orm_object(self) -> None:
        """Test SSOConfigResponse can be created from ORM-like object."""
        from app.api.v1.endpoints.oauth import SSOConfigResponse

        class MockConfig:
            id = uuid4()
            provider = "microsoft"
            name = "MS SSO"
            is_enabled = True
            auto_create_users = True
            auto_update_users = False
            default_role_id = None
            allowed_domains = ["corp.com"]
            is_required = False
            created_at = datetime.now(UTC)

        mock_obj = MockConfig()
        response = SSOConfigResponse.model_validate(mock_obj)

        assert response.provider == "microsoft"
        assert response.auto_update_users is False
