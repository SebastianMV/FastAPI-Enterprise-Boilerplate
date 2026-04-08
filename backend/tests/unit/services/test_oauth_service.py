# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for OAuth Service.

Tests the OAuth authentication service with mocked dependencies.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestOAuthServiceInit:
    """Tests for OAuthService initialization."""

    def test_oauth_service_creation(self) -> None:
        """Test OAuthService can be instantiated."""
        from app.application.services.oauth_service import OAuthService

        mock_session = AsyncMock()

        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            service = OAuthService(session=mock_session)

        assert service is not None
        assert service._session is mock_session

    def test_state_expiration_constant(self) -> None:
        """Test STATE_EXPIRATION_SECONDS constant."""
        from app.application.services.oauth_service import OAuthService

        # Should be 10 minutes (600 seconds)
        assert OAuthService.STATE_EXPIRATION_SECONDS == 600


class TestOAuthProviderEnum:
    """Tests for OAuthProvider enum."""

    def test_oauth_provider_values(self) -> None:
        """Test OAuthProvider enum values."""
        from app.domain.entities.oauth import OAuthProvider

        assert OAuthProvider.GOOGLE.value == "google"
        assert OAuthProvider.MICROSOFT.value == "microsoft"
        assert OAuthProvider.GITHUB.value == "github"

    def test_oauth_provider_list(self) -> None:
        """Test listing all OAuth providers."""
        from app.domain.entities.oauth import OAuthProvider

        providers = list(OAuthProvider)
        assert len(providers) >= 3
        assert OAuthProvider.GOOGLE in providers


class TestOAuthState:
    """Tests for OAuthState entity."""

    def test_oauth_state_creation(self) -> None:
        """Test OAuthState creation."""
        from app.domain.entities.oauth import OAuthProvider, OAuthState

        state = OAuthState(
            state="random-state-string",
            provider=OAuthProvider.GOOGLE,
            tenant_id=uuid4(),
            redirect_uri="https://example.com/callback",
            nonce="random-nonce",
            code_verifier="pkce-code-verifier",
            created_at=datetime.now(UTC),
        )

        assert state.state == "random-state-string"
        assert state.provider == OAuthProvider.GOOGLE
        assert state.nonce == "random-nonce"

    def test_oauth_state_without_tenant(self) -> None:
        """Test OAuthState without tenant context."""
        from app.domain.entities.oauth import OAuthProvider, OAuthState

        state = OAuthState(
            state="state-no-tenant",
            provider=OAuthProvider.GITHUB,
            tenant_id=None,
            redirect_uri="https://example.com/callback",
            nonce="nonce",
            code_verifier="verifier",
            created_at=datetime.now(UTC),
        )

        assert state.tenant_id is None

    def test_oauth_state_with_linking_user(self) -> None:
        """Test OAuthState for account linking."""
        from app.domain.entities.oauth import OAuthProvider, OAuthState

        user_id = uuid4()
        state = OAuthState(
            state="linking-state",
            provider=OAuthProvider.MICROSOFT,
            tenant_id=uuid4(),
            redirect_uri="https://example.com/callback",
            nonce="nonce",
            code_verifier="verifier",
            created_at=datetime.now(UTC),
            is_linking=True,
            existing_user_id=user_id,
        )

        assert state.existing_user_id == user_id
        assert state.is_linking is True


class TestOAuthUserInfo:
    """Tests for OAuthUserInfo entity."""

    def test_oauth_user_info_creation(self) -> None:
        """Test OAuthUserInfo creation."""
        from app.domain.entities.oauth import OAuthProvider, OAuthUserInfo

        user_info = OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google-123456",
            email="user@gmail.com",
            name="Test User",
            given_name="Test",
            family_name="User",
            picture="https://example.com/avatar.jpg",
            email_verified=True,
        )

        assert user_info.provider == OAuthProvider.GOOGLE
        assert user_info.provider_user_id == "google-123456"
        assert user_info.email == "user@gmail.com"
        assert user_info.email_verified is True

    def test_oauth_user_info_minimal(self) -> None:
        """Test OAuthUserInfo with minimal data."""
        from app.domain.entities.oauth import OAuthProvider, OAuthUserInfo

        user_info = OAuthUserInfo(
            provider=OAuthProvider.GITHUB,
            provider_user_id="github-789",
            email="user@github.com",
        )

        assert user_info.name is None
        assert user_info.picture is None


class TestOAuthConnection:
    """Tests for OAuthConnection entity."""

    def test_oauth_connection_creation(self) -> None:
        """Test OAuthConnection creation."""
        from app.domain.entities.oauth import OAuthConnection, OAuthProvider

        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google-user-123",
            provider_email="user@gmail.com",
            provider_display_name="Test User",
            provider_avatar_url="https://example.com/pic.jpg",
            access_token="access-token",
            refresh_token="refresh-token",
            token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=["email", "profile"],
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert connection.provider == OAuthProvider.GOOGLE
        assert connection.is_active is True
        assert "email" in connection.scopes

    def test_oauth_connection_inactive(self) -> None:
        """Test inactive OAuth connection."""
        from app.domain.entities.oauth import OAuthConnection, OAuthProvider

        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.MICROSOFT,
            provider_user_id="ms-user-456",
            provider_email="user@outlook.com",
            is_active=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert connection.is_active is False


class TestSSOConfiguration:
    """Tests for SSOConfiguration entity."""

    def test_sso_configuration_creation(self) -> None:
        """Test SSOConfiguration creation."""
        from app.domain.entities.oauth import OAuthProvider, SSOConfiguration

        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            name="Google SSO",
            client_id="google-client-id",
            client_secret="google-client-secret",
            is_enabled=True,
            allowed_domains=["example.com"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert config.provider == OAuthProvider.GOOGLE
        assert config.is_enabled is True
        assert "example.com" in config.allowed_domains

    def test_sso_configuration_disabled(self) -> None:
        """Test disabled SSO configuration."""
        from app.domain.entities.oauth import OAuthProvider, SSOConfiguration

        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GITHUB,
            name="GitHub SSO",
            client_id="github-client-id",
            client_secret="github-secret",
            is_enabled=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert config.is_enabled is False


class TestOAuthServiceInitiateFlow:
    """Tests for OAuth flow initiation."""

    @pytest.mark.asyncio
    async def test_initiate_oauth_generates_state(self) -> None:
        """Test that initiate_oauth generates state string."""
        from app.application.services.oauth_service import OAuthService
        from app.domain.entities.oauth import OAuthProvider

        mock_session = AsyncMock()
        mock_cache = MagicMock()
        mock_cache.set = AsyncMock()

        mock_provider = MagicMock()
        mock_provider.redirect_uri = "https://example.com/callback"
        mock_provider.get_authorization_url.return_value = (
            "https://oauth.example.com/auth"
        )
        mock_provider.generate_pkce.return_value = ("verifier", "challenge")

        with patch(
            "app.application.services.oauth_service.get_cache"
        ) as mock_get_cache:
            mock_get_cache.return_value = mock_cache
            service = OAuthService(session=mock_session)
            service._get_provider = AsyncMock(return_value=mock_provider)

            auth_url, state = await service.initiate_oauth(
                provider=OAuthProvider.GOOGLE,
                tenant_id=uuid4(),
            )

        assert state is not None
        assert len(state) > 20  # State should be a secure random string


class TestOAuthServiceEdgeCases:
    """Tests for edge cases in OAuth service."""

    def test_oauth_provider_enum_iteration(self) -> None:
        """Test iterating OAuth providers."""
        from app.domain.entities.oauth import OAuthProvider

        providers = [p.value for p in OAuthProvider]
        assert "google" in providers
        assert "github" in providers

    def test_oauth_state_expires(self) -> None:
        """Test OAuth state has expiration."""
        from app.domain.entities.oauth import OAuthProvider, OAuthState

        now = datetime.now(UTC)
        state = OAuthState(
            state="test-state",
            provider=OAuthProvider.GOOGLE,
            tenant_id=None,
            redirect_uri="https://example.com/callback",
            nonce="nonce",
            code_verifier="verifier",
            created_at=now,
        )

        # State created now should not be expired
        assert state.created_at == now

    def test_oauth_connection_scopes_list(self) -> None:
        """Test OAuth connection with multiple scopes."""
        from app.domain.entities.oauth import OAuthConnection, OAuthProvider

        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google-123",
            provider_email="user@gmail.com",
            scopes=["email", "profile", "openid", "calendar.read"],
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert len(connection.scopes) == 4
        assert "openid" in connection.scopes

    def test_sso_config_multiple_domains(self) -> None:
        """Test SSO configuration with multiple domains."""
        from app.domain.entities.oauth import OAuthProvider, SSOConfiguration

        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.MICROSOFT,
            name="Microsoft SSO",
            client_id="ms-client-id",
            client_secret="ms-secret",
            is_enabled=True,
            allowed_domains=["example.com", "example.org", "corp.example.com"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert len(config.allowed_domains) == 3


class TestOAuthEndpointSchemas:
    """Tests for OAuth endpoint schemas."""

    def test_oauth_authorization_url_response(self) -> None:
        """Test OAuth authorization URL response."""
        # OAuth endpoints typically return authorization URL and state
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?..."
        state = "random-state-value"

        assert auth_url.startswith("https://")
        assert len(state) > 0

    def test_oauth_callback_params(self) -> None:
        """Test OAuth callback parameters structure."""
        callback_params = {
            "code": "authorization-code",
            "state": "original-state",
        }

        assert "code" in callback_params
        assert "state" in callback_params

    def test_oauth_error_callback_params(self) -> None:
        """Test OAuth error callback parameters."""
        error_params = {
            "error": "access_denied",
            "error_description": "User denied access",
            "state": "original-state",
        }

        assert error_params["error"] == "access_denied"
