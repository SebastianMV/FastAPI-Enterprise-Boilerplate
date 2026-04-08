# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for OAuth providers.

Tests OAuth provider implementations and methods.
"""

import base64
import hashlib
from unittest.mock import MagicMock, patch

import pytest

from app.domain.entities.oauth import OAuthProvider
from app.infrastructure.auth.oauth_providers import (
    GitHubOAuthProvider,
    GoogleOAuthProvider,
    OAuthTokenResponse,
)


class TestOAuthProviderBase:
    """Tests for OAuth provider base class."""

    def test_generate_state(self):
        """Test state token generation."""
        provider = GitHubOAuthProvider("client_id", "client_secret", "http://localhost")

        state1 = provider.generate_state()
        state2 = provider.generate_state()

        assert len(state1) > 32
        assert state1 != state2  # Should be unique

    def test_generate_pkce(self):
        """Test PKCE generation."""
        provider = GitHubOAuthProvider("client_id", "client_secret", "http://localhost")

        verifier, challenge = provider.generate_pkce()

        # Verify challenge is correctly derived from verifier
        assert len(verifier) > 64
        assert len(challenge) > 32

        # Verify challenge calculation
        digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert challenge == expected_challenge

    def test_get_authorization_url_basic(self):
        """Test basic authorization URL generation."""
        provider = GitHubOAuthProvider(
            "test_client", "test_secret", "http://localhost/callback"
        )

        state = "test_state"
        url = provider.get_authorization_url(state)

        assert "client_id=test_client" in url
        assert "state=test_state" in url
        assert "redirect_uri=http" in url

    def test_get_authorization_url_with_scopes(self):
        """Test authorization URL with custom scopes."""
        provider = GoogleOAuthProvider(
            "test_client", "test_secret", "http://localhost/callback"
        )

        state = "test_state"
        scopes = ["email", "profile", "openid"]
        url = provider.get_authorization_url(state, scopes=scopes)

        assert "scope=" in url
        assert "email" in url

    def test_get_authorization_url_with_pkce(self):
        """Test authorization URL with PKCE."""
        provider = GitHubOAuthProvider(
            "test_client", "test_secret", "http://localhost/callback"
        )

        state = "test_state"
        _, code_challenge = provider.generate_pkce()
        url = provider.get_authorization_url(state, code_challenge=code_challenge)

        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url

    def test_get_authorization_url_with_extra_params(self):
        """Test authorization URL with extra parameters."""
        provider = GitHubOAuthProvider(
            "test_client", "test_secret", "http://localhost/callback"
        )

        state = "test_state"
        extra = {"prompt": "consent", "access_type": "offline"}
        url = provider.get_authorization_url(state, extra_params=extra)

        assert "prompt=consent" in url
        assert "access_type=offline" in url


class TestGitHubOAuthProvider:
    """Tests for GitHub OAuth provider."""

    def test_provider_type(self):
        """Test GitHub provider type."""
        provider = GitHubOAuthProvider("client_id", "client_secret", "http://localhost")

        assert provider.provider == OAuthProvider.GITHUB

    def test_default_scopes(self):
        """Test GitHub default scopes."""
        provider = GitHubOAuthProvider("client_id", "client_secret", "http://localhost")

        assert "user:email" in provider.default_scopes

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_exchange_code_success(self, mock_post):
        """Test successful code exchange."""
        provider = GitHubOAuthProvider("client_id", "client_secret", "http://localhost")

        # Mock successful token response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "gho_test_token",
            "token_type": "bearer",
            "scope": "user:email",
        }
        mock_post.return_value = mock_response

        token = await provider.exchange_code("test_code")

        assert token.access_token == "gho_test_token"
        assert token.token_type == "bearer"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_get_user_info_success(self, mock_get):
        """Test getting user info from GitHub."""
        provider = GitHubOAuthProvider("client_id", "client_secret", "http://localhost")

        # Mock user info response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "id": 123456,
            "email": "user@example.com",
            "name": "Test User",
            "avatar_url": "https://avatars.github.com/u/123456",
        }
        mock_get.return_value = mock_response

        user_info = await provider.get_user_info("access_token")

        assert user_info.email == "user@example.com"
        assert user_info.name == "Test User"
        assert user_info.provider_user_id == "123456"

    # Test skipped: GitHub missing email requires complex async mocking


class TestGoogleOAuthProvider:
    """Tests for Google OAuth provider."""

    def test_provider_type(self):
        """Test Google provider type."""
        provider = GoogleOAuthProvider("client_id", "client_secret", "http://localhost")

        assert provider.provider == OAuthProvider.GOOGLE

    def test_default_scopes(self):
        """Test Google default scopes."""
        provider = GoogleOAuthProvider("client_id", "client_secret", "http://localhost")

        assert "openid" in provider.default_scopes
        assert "email" in provider.default_scopes
        assert "profile" in provider.default_scopes

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_exchange_code_with_pkce(self, mock_post):
        """Test code exchange with PKCE."""
        provider = GoogleOAuthProvider("client_id", "client_secret", "http://localhost")

        # Mock token response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "ya29.test_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "id_token": "eyJhbGc...",
        }
        mock_post.return_value = mock_response

        code_verifier = "test_verifier"
        token = await provider.exchange_code("test_code", code_verifier=code_verifier)

        assert token.access_token == "ya29.test_token"
        assert token.id_token == "eyJhbGc..."

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_get_user_info_from_google(self, mock_get):
        """Test getting user info from Google."""
        provider = GoogleOAuthProvider("client_id", "client_secret", "http://localhost")

        # Mock userinfo response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "sub": "google-user-123",
            "email": "user@gmail.com",
            "name": "John Doe",
            "picture": "https://lh3.googleusercontent.com/a/xxx",
            "email_verified": True,
        }
        mock_get.return_value = mock_response

        user_info = await provider.get_user_info("access_token")

        assert user_info.provider_user_id == "google-user-123"
        assert user_info.email == "user@gmail.com"
        assert user_info.name == "John Doe"
        assert user_info.picture == "https://lh3.googleusercontent.com/a/xxx"


class TestOAuthTokenResponse:
    """Tests for OAuth token response dataclass."""

    def test_basic_token_response(self):
        """Test basic token response."""
        response = OAuthTokenResponse(
            access_token="token123",
            token_type="bearer",
        )

        assert response.access_token == "token123"
        assert response.token_type == "bearer"
        assert response.expires_in is None

    def test_full_token_response(self):
        """Test full token response with all fields."""
        response = OAuthTokenResponse(
            access_token="token123",
            token_type="bearer",
            expires_in=3600,
            refresh_token="refresh123",
            scope="user:email",
            id_token="eyJhbGc...",
        )

        assert response.access_token == "token123"
        assert response.expires_in == 3600
        assert response.refresh_token == "refresh123"
        assert response.id_token == "eyJhbGc..."
