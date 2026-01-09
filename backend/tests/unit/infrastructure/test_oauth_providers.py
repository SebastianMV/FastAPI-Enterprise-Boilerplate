# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for OAuth2 provider implementations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib
import base64

from app.infrastructure.auth.oauth_providers import (
    OAuthTokenResponse,
    OAuthProviderBase,
    GoogleOAuthProvider,
    GitHubOAuthProvider,
    MicrosoftOAuthProvider,
    DiscordOAuthProvider,
    OAUTH_PROVIDERS,
    get_oauth_provider,
)
from app.domain.entities.oauth import OAuthProvider


class TestOAuthTokenResponse:
    """Tests for OAuthTokenResponse dataclass."""

    def test_create_minimal(self):
        """Test creating response with minimal fields."""
        response = OAuthTokenResponse(
            access_token="token123",
            token_type="Bearer",
        )
        
        assert response.access_token == "token123"
        assert response.token_type == "Bearer"
        assert response.expires_in is None
        assert response.refresh_token is None

    def test_create_full(self):
        """Test creating response with all fields."""
        response = OAuthTokenResponse(
            access_token="token123",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="refresh123",
            scope="openid email",
            id_token="id_token123",
        )
        
        assert response.access_token == "token123"
        assert response.expires_in == 3600
        assert response.refresh_token == "refresh123"
        assert response.scope == "openid email"
        assert response.id_token == "id_token123"


class TestOAuthProviderBase:
    """Tests for OAuthProviderBase class."""

    @pytest.fixture
    def google_provider(self):
        """Create a Google provider for testing base functionality."""
        return GoogleOAuthProvider(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
        )

    def test_init(self, google_provider):
        """Test provider initialization."""
        assert google_provider.client_id == "test_client_id"
        assert google_provider.client_secret == "test_client_secret"
        assert google_provider.redirect_uri == "http://localhost:8000/callback"

    def test_generate_state(self, google_provider):
        """Test state generation produces unique values."""
        states = [google_provider.generate_state() for _ in range(10)]
        
        assert len(set(states)) == 10  # All unique
        assert all(len(s) > 20 for s in states)  # Sufficient length

    def test_generate_pkce(self, google_provider):
        """Test PKCE generation."""
        verifier, challenge = google_provider.generate_pkce()
        
        assert len(verifier) > 40
        assert len(challenge) > 40
        
        # Verify challenge is correct hash of verifier
        expected_digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode()
        
        assert challenge == expected_challenge

    def test_get_authorization_url_basic(self, google_provider):
        """Test basic authorization URL generation."""
        url = google_provider.get_authorization_url(
            state="test_state",
        )
        
        assert "https://accounts.google.com/o/oauth2/v2/auth?" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback" in url
        assert "response_type=code" in url
        assert "state=test_state" in url

    def test_get_authorization_url_with_scopes(self, google_provider):
        """Test authorization URL with custom scopes."""
        url = google_provider.get_authorization_url(
            state="test_state",
            scopes=["openid", "email", "profile"],
        )
        
        assert "scope=openid+email+profile" in url

    def test_get_authorization_url_with_pkce(self, google_provider):
        """Test authorization URL with PKCE challenge."""
        url = google_provider.get_authorization_url(
            state="test_state",
            code_challenge="test_challenge",
        )
        
        assert "code_challenge=test_challenge" in url
        assert "code_challenge_method=S256" in url

    def test_get_authorization_url_with_extra_params(self, google_provider):
        """Test authorization URL with extra parameters."""
        url = google_provider.get_authorization_url(
            state="test_state",
            extra_params={"login_hint": "user@example.com"},
        )
        
        assert "login_hint=user%40example.com" in url

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, google_provider):
        """Test successful code exchange."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "access123",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh123",
            "scope": "openid email",
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await google_provider.exchange_code("auth_code")
        
        assert result.access_token == "access123"
        assert result.token_type == "Bearer"
        assert result.expires_in == 3600
        assert result.refresh_token == "refresh123"

    @pytest.mark.asyncio
    async def test_exchange_code_with_pkce(self, google_provider):
        """Test code exchange with PKCE verifier."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "access123",
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await google_provider.exchange_code("auth_code", code_verifier="verifier123")
        
        # Verify code_verifier was included in the request
        call_kwargs = mock_post.call_args
        assert "code_verifier" in call_kwargs.kwargs.get("data", {})

    @pytest.mark.asyncio
    async def test_refresh_access_token(self, google_provider):
        """Test access token refresh."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await google_provider.refresh_access_token("old_refresh_token")
        
        assert result.access_token == "new_access123"
        # Should preserve original refresh token if not returned
        assert result.refresh_token == "old_refresh_token"

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, google_provider):
        """Test successful token revocation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await google_provider.revoke_token("token123")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_failure(self, google_provider):
        """Test failed token revocation."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await google_provider.revoke_token("token123")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_token_no_revoke_url(self):
        """Test revocation when provider has no revoke URL."""
        # GitHub doesn't have a revoke URL
        provider = GitHubOAuthProvider(
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost",
        )
        
        result = await provider.revoke_token("token123")
        assert result is False


class TestGoogleOAuthProvider:
    """Tests for GoogleOAuthProvider."""

    @pytest.fixture
    def provider(self):
        return GoogleOAuthProvider(
            client_id="google_client_id",
            client_secret="google_client_secret",
            redirect_uri="http://localhost:8000/callback/google",
        )

    def test_provider_attributes(self, provider):
        """Test Google provider has correct attributes."""
        assert provider.provider == OAuthProvider.GOOGLE
        assert "accounts.google.com" in provider.authorization_url
        assert "oauth2.googleapis.com" in provider.token_url
        assert "googleapis.com" in provider.userinfo_url
        assert provider.revoke_url is not None

    def test_default_scopes(self, provider):
        """Test default scopes include essential ones."""
        assert "openid" in provider.default_scopes
        assert "email" in provider.default_scopes
        assert "profile" in provider.default_scopes

    def test_authorization_url_includes_google_params(self, provider):
        """Test Google-specific authorization params."""
        url = provider.get_authorization_url(state="test_state")
        
        assert "access_type=offline" in url
        assert "prompt=consent" in url

    @pytest.mark.asyncio
    async def test_get_user_info(self, provider):
        """Test getting user info from Google."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sub": "123456789",
            "email": "user@gmail.com",
            "email_verified": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/photo.jpg",
            "locale": "en",
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await provider.get_user_info("access_token")
        
        assert result.provider == OAuthProvider.GOOGLE
        assert result.provider_user_id == "123456789"
        assert result.email == "user@gmail.com"
        assert result.email_verified is True
        assert result.name == "Test User"
        assert result.given_name == "Test"
        assert result.family_name == "User"


class TestGitHubOAuthProvider:
    """Tests for GitHubOAuthProvider."""

    @pytest.fixture
    def provider(self):
        return GitHubOAuthProvider(
            client_id="github_client_id",
            client_secret="github_client_secret",
            redirect_uri="http://localhost:8000/callback/github",
        )

    def test_provider_attributes(self, provider):
        """Test GitHub provider has correct attributes."""
        assert provider.provider == OAuthProvider.GITHUB
        assert "github.com" in provider.authorization_url
        assert "github.com" in provider.token_url
        assert "api.github.com" in provider.userinfo_url
        assert provider.revoke_url is None  # GitHub doesn't support revocation

    def test_default_scopes(self, provider):
        """Test default scopes."""
        assert "read:user" in provider.default_scopes
        assert "user:email" in provider.default_scopes

    @pytest.mark.asyncio
    async def test_get_user_info_with_email(self, provider):
        """Test getting user info when email is in profile."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "user@github.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await provider.get_user_info("access_token")
        
        assert result.provider == OAuthProvider.GITHUB
        assert result.provider_user_id == "12345"
        assert result.email == "user@github.com"
        assert result.name == "Test User"
        assert result.picture == "https://avatars.githubusercontent.com/u/12345"

    @pytest.mark.asyncio
    async def test_get_user_info_fetches_email_separately(self, provider):
        """Test fetching email when not in profile."""
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": None,  # No email in profile
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        }
        mock_user_response.raise_for_status = MagicMock()
        
        mock_emails_response = MagicMock()
        mock_emails_response.status_code = 200
        mock_emails_response.json.return_value = [
            {"email": "secondary@example.com", "primary": False, "verified": True},
            {"email": "primary@example.com", "primary": True, "verified": True},
        ]
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(side_effect=[mock_user_response, mock_emails_response])
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            result = await provider.get_user_info("access_token")
        
        assert result.email == "primary@example.com"
        assert result.email_verified is True


class TestMicrosoftOAuthProvider:
    """Tests for MicrosoftOAuthProvider."""

    @pytest.fixture
    def provider(self):
        return MicrosoftOAuthProvider(
            client_id="ms_client_id",
            client_secret="ms_client_secret",
            redirect_uri="http://localhost:8000/callback/microsoft",
        )

    def test_provider_attributes(self, provider):
        """Test Microsoft provider has correct attributes."""
        assert provider.provider == OAuthProvider.MICROSOFT
        assert "login.microsoftonline.com" in provider.authorization_url
        assert "graph.microsoft.com" in provider.userinfo_url

    def test_default_scopes(self, provider):
        """Test default scopes include Graph API."""
        assert "openid" in provider.default_scopes
        assert "User.Read" in provider.default_scopes

    def test_custom_tenant_id(self):
        """Test provider with custom tenant ID."""
        provider = MicrosoftOAuthProvider(
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost",
            tenant_id="my-tenant-id",
        )
        
        assert "my-tenant-id" in provider.authorization_url
        assert "my-tenant-id" in provider.token_url

    @pytest.mark.asyncio
    async def test_get_user_info(self, provider):
        """Test getting user info from Microsoft Graph."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "user-uuid-123",
            "mail": "user@outlook.com",
            "displayName": "Test User",
            "givenName": "Test",
            "surname": "User",
            "preferredLanguage": "en-US",
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await provider.get_user_info("access_token")
        
        assert result.provider == OAuthProvider.MICROSOFT
        assert result.provider_user_id == "user-uuid-123"
        assert result.email == "user@outlook.com"
        assert result.email_verified is True  # Microsoft always verifies
        assert result.name == "Test User"

    @pytest.mark.asyncio
    async def test_get_user_info_fallback_to_upn(self, provider):
        """Test email fallback to userPrincipalName."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "user-uuid-123",
            "mail": None,  # No mail field
            "userPrincipalName": "user@domain.onmicrosoft.com",
            "displayName": "Test User",
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await provider.get_user_info("access_token")
        
        assert result.email == "user@domain.onmicrosoft.com"


class TestDiscordOAuthProvider:
    """Tests for DiscordOAuthProvider."""

    @pytest.fixture
    def provider(self):
        return DiscordOAuthProvider(
            client_id="discord_client_id",
            client_secret="discord_client_secret",
            redirect_uri="http://localhost:8000/callback/discord",
        )

    def test_provider_attributes(self, provider):
        """Test Discord provider has correct attributes."""
        assert provider.provider == OAuthProvider.DISCORD
        assert "discord.com" in provider.authorization_url
        assert "discord.com" in provider.token_url
        assert provider.revoke_url is not None

    def test_default_scopes(self, provider):
        """Test default scopes."""
        assert "identify" in provider.default_scopes
        assert "email" in provider.default_scopes

    @pytest.mark.asyncio
    async def test_get_user_info(self, provider):
        """Test getting user info from Discord."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "123456789012345678",
            "username": "testuser",
            "global_name": "Test User",
            "email": "user@discord.com",
            "verified": True,
            "avatar": "abc123",
            "locale": "en-US",
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await provider.get_user_info("access_token")
        
        assert result.provider == OAuthProvider.DISCORD
        assert result.provider_user_id == "123456789012345678"
        assert result.email == "user@discord.com"
        assert result.email_verified is True
        assert result.name == "Test User"
        assert "cdn.discordapp.com" in result.picture

    @pytest.mark.asyncio
    async def test_get_user_info_no_avatar(self, provider):
        """Test user info when no avatar is set."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "123456789012345678",
            "username": "testuser",
            "global_name": None,
            "email": "user@discord.com",
            "verified": True,
            "avatar": None,
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await provider.get_user_info("access_token")
        
        assert result.picture is None
        assert result.name == "testuser"  # Falls back to username


class TestOAuthProviderRegistry:
    """Tests for provider registry and factory function."""

    def test_all_providers_registered(self):
        """Test all expected providers are in registry."""
        assert OAuthProvider.GOOGLE in OAUTH_PROVIDERS
        assert OAuthProvider.GITHUB in OAUTH_PROVIDERS
        assert OAuthProvider.MICROSOFT in OAUTH_PROVIDERS
        assert OAuthProvider.DISCORD in OAUTH_PROVIDERS

    def test_get_oauth_provider_google(self):
        """Test getting Google provider."""
        provider = get_oauth_provider(
            provider=OAuthProvider.GOOGLE,
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost",
        )
        
        assert isinstance(provider, GoogleOAuthProvider)
        assert provider.client_id == "test"

    def test_get_oauth_provider_github(self):
        """Test getting GitHub provider."""
        provider = get_oauth_provider(
            provider=OAuthProvider.GITHUB,
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost",
        )
        
        assert isinstance(provider, GitHubOAuthProvider)

    def test_get_oauth_provider_microsoft_with_tenant(self):
        """Test getting Microsoft provider with tenant ID."""
        provider = get_oauth_provider(
            provider=OAuthProvider.MICROSOFT,
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost",
            tenant_id="custom-tenant",
        )
        
        assert isinstance(provider, MicrosoftOAuthProvider)
        assert provider.tenant_id == "custom-tenant"

    def test_get_oauth_provider_invalid(self):
        """Test getting invalid provider raises error."""
        with pytest.raises(ValueError) as exc_info:
            get_oauth_provider(
                provider="invalid",  # type: ignore
                client_id="test",
                client_secret="test",
                redirect_uri="http://localhost",
            )
        
        assert "Unsupported OAuth provider" in str(exc_info.value)
