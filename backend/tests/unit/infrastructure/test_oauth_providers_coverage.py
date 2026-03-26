# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for OAuth2 Providers.

Tests all OAuth providers with mocked HTTP requests.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.domain.entities.oauth import OAuthProvider
from app.infrastructure.auth.oauth_providers import (
    OAUTH_PROVIDERS,
    GitHubOAuthProvider,
    GoogleOAuthProvider,
    MicrosoftOAuthProvider,
    OAuthTokenResponse,
    get_oauth_provider,
)


class TestOAuthProviderBase:
    """Tests for base OAuth provider class."""

    def test_generate_state(self):
        """Test state generation."""
        provider = GoogleOAuthProvider(
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost/callback",
        )

        state1 = provider.generate_state()
        state2 = provider.generate_state()

        assert isinstance(state1, str)
        assert len(state1) > 32
        assert state1 != state2  # Should be unique

    def test_generate_pkce(self):
        """Test PKCE code verifier and challenge generation."""
        provider = GoogleOAuthProvider(
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost/callback",
        )

        verifier, challenge = provider.generate_pkce()

        assert isinstance(verifier, str)
        assert isinstance(challenge, str)
        assert len(verifier) > 64
        assert len(challenge) > 32
        assert verifier != challenge

    def test_get_authorization_url_basic(self):
        """Test basic authorization URL generation."""
        provider = GoogleOAuthProvider(
            client_id="my_client_id",
            client_secret="my_secret",
            redirect_uri="http://localhost:8000/callback",
        )

        state = "test_state_123"
        url = provider.get_authorization_url(state=state)

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert parsed.scheme == "https"
        assert "accounts.google.com" in parsed.netloc
        assert params["client_id"][0] == "my_client_id"
        assert params["redirect_uri"][0] == "http://localhost:8000/callback"
        assert params["response_type"][0] == "code"
        assert params["state"][0] == "test_state_123"
        assert "openid email profile" in params["scope"][0]

    def test_get_authorization_url_with_pkce(self):
        """Test authorization URL with PKCE."""
        provider = GoogleOAuthProvider(
            client_id="my_client_id",
            client_secret="my_secret",
            redirect_uri="http://localhost:8000/callback",
        )

        state = "test_state"
        _, challenge = provider.generate_pkce()
        url = provider.get_authorization_url(
            state=state,
            code_challenge=challenge,
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert params["code_challenge"][0] == challenge
        assert params["code_challenge_method"][0] == "S256"

    def test_get_authorization_url_custom_scopes(self):
        """Test authorization URL with custom scopes."""
        provider = GitHubOAuthProvider(
            client_id="github_client",
            client_secret="github_secret",
            redirect_uri="http://localhost/callback",
        )

        url = provider.get_authorization_url(
            state="state123",
            scopes=["repo", "admin:org"],
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert params["scope"][0] == "repo admin:org"

    def test_get_authorization_url_extra_params(self):
        """Test authorization URL with extra parameters."""
        provider = GoogleOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        url = provider.get_authorization_url(
            state="state",
            extra_params={"access_type": "offline", "prompt": "consent"},
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert params["access_type"][0] == "offline"
        assert params["prompt"][0] == "consent"

    @pytest.mark.asyncio
    async def test_exchange_code_success(self):
        """Test successful code exchange."""
        provider = GoogleOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "access_token_123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh_token_456",
            "scope": "openid email",
            "id_token": "id_token_789",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await provider.exchange_code(code="auth_code_123")

            assert isinstance(result, OAuthTokenResponse)
            assert result.access_token == "access_token_123"
            assert result.token_type == "Bearer"
            assert result.expires_in == 3600
            assert result.refresh_token == "refresh_token_456"
            assert result.scope == "openid email"
            assert result.id_token == "id_token_789"

    @pytest.mark.asyncio
    async def test_exchange_code_with_pkce(self):
        """Test code exchange with PKCE verifier."""
        provider = GitHubOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        verifier, _ = provider.generate_pkce()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "access_token",
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await provider.exchange_code(
                code="code123",
                code_verifier=verifier,
            )

            # Verify code_verifier was included in request
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["data"]["code_verifier"] == verifier

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self):
        """Test successful token refresh."""
        provider = GoogleOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid email",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await provider.refresh_access_token(
                refresh_token="old_refresh_token"
            )

            assert result.access_token == "new_access_token"
            assert result.refresh_token == "old_refresh_token"  # Preserved

    @pytest.mark.asyncio
    async def test_revoke_token_success(self):
        """Test successful token revocation."""
        provider = GoogleOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await provider.revoke_token(token="token_to_revoke")

            assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_no_revoke_url(self):
        """Test revoke when provider doesn't support revocation."""
        provider = GitHubOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        # GitHub doesn't have revoke_url
        assert provider.revoke_url is None

        result = await provider.revoke_token(token="token")
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_token_failure(self):
        """Test token revocation failure."""
        provider = GoogleOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Network error")
            )

            result = await provider.revoke_token(token="token")
            assert result is False


class TestGoogleOAuthProvider:
    """Tests for Google OAuth provider."""

    def test_google_authorization_url_defaults(self):
        """Test Google-specific authorization URL parameters."""
        provider = GoogleOAuthProvider(
            client_id="google_client",
            client_secret="google_secret",
            redirect_uri="http://localhost/callback",
        )

        url = provider.get_authorization_url(state="state123")

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # Google-specific defaults
        assert params["access_type"][0] == "offline"
        assert params["prompt"][0] == "consent"

    @pytest.mark.asyncio
    async def test_google_get_user_info_success(self):
        """Test getting user info from Google."""
        provider = GoogleOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sub": "google_user_123",
            "email": "user@gmail.com",
            "email_verified": True,
            "name": "John Doe",
            "given_name": "John",
            "family_name": "Doe",
            "picture": "https://example.com/photo.jpg",
            "locale": "en",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            user_info = await provider.get_user_info(access_token="access_token")

            assert user_info.provider == OAuthProvider.GOOGLE
            assert user_info.provider_user_id == "google_user_123"
            assert user_info.email == "user@gmail.com"
            assert user_info.email_verified is True
            assert user_info.name == "John Doe"
            assert user_info.given_name == "John"
            assert user_info.family_name == "Doe"
            assert user_info.picture == "https://example.com/photo.jpg"
            assert user_info.locale == "en"


class TestGitHubOAuthProvider:
    """Tests for GitHub OAuth provider."""

    @pytest.mark.asyncio
    async def test_github_get_user_info_with_email(self):
        """Test getting user info from GitHub when email is public."""
        provider = GitHubOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 12345,
            "email": "user@github.com",
            "name": "GitHub User",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            user_info = await provider.get_user_info(access_token="token")

            assert user_info.provider == OAuthProvider.GITHUB
            assert user_info.provider_user_id == "12345"
            assert user_info.email == "user@github.com"
            assert user_info.name == "GitHub User"
            assert user_info.picture == "https://avatars.githubusercontent.com/u/12345"
            assert user_info.given_name is None  # GitHub doesn't split names
            assert user_info.family_name is None

    @pytest.mark.asyncio
    async def test_github_get_user_info_fetch_email(self):
        """Test fetching email separately when not public."""
        provider = GitHubOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        # User profile without email
        profile_response = MagicMock()
        profile_response.json.return_value = {
            "id": 67890,
            "name": "Private User",
            "avatar_url": "https://avatars.githubusercontent.com/u/67890",
        }
        profile_response.raise_for_status = MagicMock()

        # Email endpoint
        emails_response = MagicMock()
        emails_response.status_code = 200
        emails_response.json.return_value = [
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "primary@github.com", "primary": True, "verified": True},
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock()
            mock_get.side_effect = [profile_response, emails_response]
            mock_client.return_value.__aenter__.return_value.get = mock_get

            user_info = await provider.get_user_info(access_token="token")

            assert user_info.email == "primary@github.com"
            assert user_info.email_verified is True


class TestMicrosoftOAuthProvider:
    """Tests for Microsoft OAuth provider."""

    def test_microsoft_tenant_common(self):
        """Test Microsoft provider with common tenant."""
        provider = MicrosoftOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        assert provider.tenant_id == "common"
        assert "common" in provider.authorization_url
        assert "common" in provider.token_url

    def test_microsoft_tenant_specific(self):
        """Test Microsoft provider with specific tenant ID."""
        provider = MicrosoftOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
            tenant_id="my-tenant-id-123",
        )

        assert provider.tenant_id == "my-tenant-id-123"
        assert "my-tenant-id-123" in provider.authorization_url
        assert "my-tenant-id-123" in provider.token_url

    @pytest.mark.asyncio
    async def test_microsoft_get_user_info_success(self):
        """Test getting user info from Microsoft Graph."""
        provider = MicrosoftOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "microsoft_user_id_123",
            "mail": "user@contoso.com",
            "displayName": "John Smith",
            "givenName": "John",
            "surname": "Smith",
            "preferredLanguage": "en-US",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            user_info = await provider.get_user_info(access_token="token")

            assert user_info.provider == OAuthProvider.MICROSOFT
            assert user_info.provider_user_id == "microsoft_user_id_123"
            assert user_info.email == "user@contoso.com"
            assert user_info.email_verified is True  # Microsoft always verifies
            assert user_info.name == "John Smith"
            assert user_info.given_name == "John"
            assert user_info.family_name == "Smith"
            assert user_info.locale == "en-US"

    @pytest.mark.asyncio
    async def test_microsoft_get_user_info_upn_fallback(self):
        """Test Microsoft user info with userPrincipalName fallback."""
        provider = MicrosoftOAuthProvider(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost/callback",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "user_id",
            "userPrincipalName": "user@tenant.onmicrosoft.com",  # No mail field
            "displayName": "User Name",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            user_info = await provider.get_user_info(access_token="token")

            # Should use userPrincipalName when mail is absent
            assert user_info.email == "user@tenant.onmicrosoft.com"


class TestProviderRegistry:
    """Tests for provider registry and factory."""

    def test_oauth_providers_registry(self):
        """Test that all providers are registered."""
        assert OAuthProvider.GOOGLE in OAUTH_PROVIDERS
        assert OAuthProvider.GITHUB in OAUTH_PROVIDERS
        assert OAuthProvider.MICROSOFT in OAUTH_PROVIDERS

        assert OAUTH_PROVIDERS[OAuthProvider.GOOGLE] == GoogleOAuthProvider
        assert OAUTH_PROVIDERS[OAuthProvider.GITHUB] == GitHubOAuthProvider
        assert OAUTH_PROVIDERS[OAuthProvider.MICROSOFT] == MicrosoftOAuthProvider

    def test_get_oauth_provider_google(self):
        """Test factory function for Google."""
        provider = get_oauth_provider(
            provider=OAuthProvider.GOOGLE,
            client_id="google_client",
            client_secret="google_secret",
            redirect_uri="http://localhost/callback",
        )

        assert isinstance(provider, GoogleOAuthProvider)
        assert provider.client_id == "google_client"
        assert provider.client_secret == "google_secret"

    def test_get_oauth_provider_github(self):
        """Test factory function for GitHub."""
        provider = get_oauth_provider(
            provider=OAuthProvider.GITHUB,
            client_id="github_client",
            client_secret="github_secret",
            redirect_uri="http://localhost/callback",
        )

        assert isinstance(provider, GitHubOAuthProvider)

    def test_get_oauth_provider_microsoft_with_tenant(self):
        """Test factory function for Microsoft with tenant."""
        provider = get_oauth_provider(
            provider=OAuthProvider.MICROSOFT,
            client_id="ms_client",
            client_secret="ms_secret",
            redirect_uri="http://localhost/callback",
            tenant_id="specific-tenant",
        )

        assert isinstance(provider, MicrosoftOAuthProvider)
        assert provider.tenant_id == "specific-tenant"

    def test_get_oauth_provider_unsupported(self):
        """Test factory with unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported OAuth provider"):
            get_oauth_provider(
                provider="INVALID_PROVIDER",  # type: ignore
                client_id="client",
                client_secret="secret",
                redirect_uri="http://localhost/callback",
            )
