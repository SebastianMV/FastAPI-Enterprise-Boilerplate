# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Comprehensive tests for OAuth service to improve coverage.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.services.oauth_service import OAuthService
from app.domain.entities.oauth import (
    OAuthConnection,
    OAuthProvider,
    OAuthState,
    OAuthUserInfo,
)
from app.domain.exceptions.base import AuthenticationError


class TestOAuthServiceInitiateOAuth:
    """Tests for OAuth initiation."""

    @pytest.mark.asyncio
    async def test_initiate_oauth_basic(self) -> None:
        """Test initiating OAuth flow."""
        mock_session = AsyncMock()

        # Mock cache
        with patch("app.application.services.oauth_service.get_cache") as mock_cache_fn:
            mock_cache = AsyncMock()
            mock_cache.set.return_value = None
            mock_cache_fn.return_value = mock_cache

            service = OAuthService(mock_session)

            # Mock provider
            mock_provider = MagicMock()
            mock_provider.redirect_uri = "http://localhost/callback"
            mock_provider.generate_pkce.return_value = ("verifier", "challenge")
            mock_provider.get_authorization_url.return_value = (
                "https://oauth.example.com/auth"
            )

            with patch.object(service, "_get_provider", return_value=mock_provider):
                url, state = await service.initiate_oauth(
                    provider=OAuthProvider.GOOGLE,
                    tenant_id=uuid4(),
                )

                assert url == "https://oauth.example.com/auth"
                assert state is not None
                assert len(state) > 0


class TestOAuthServiceCallback:
    """Tests for OAuth callback handling."""

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_state(self) -> None:
        """Test handling callback with invalid state."""
        mock_session = AsyncMock()

        with patch("app.application.services.oauth_service.get_cache") as mock_cache_fn:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None  # No state found
            mock_cache_fn.return_value = mock_cache

            service = OAuthService(mock_session)

            with pytest.raises(AuthenticationError, match="Invalid or expired"):
                await service.handle_callback(
                    provider=OAuthProvider.GOOGLE,
                    code="auth_code",
                    state="invalid_state",
                )


class TestOAuthServiceConnections:
    """Tests for OAuth connection management."""

    @pytest.mark.asyncio
    async def test_get_user_connections_empty(self) -> None:
        """Test getting user OAuth connections when empty."""
        mock_session = AsyncMock()
        user_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        with patch("app.application.services.oauth_service.get_cache") as mock_cache_fn:
            mock_cache = AsyncMock()
            mock_cache_fn.return_value = mock_cache

            service = OAuthService(mock_session)
            connections = await service.get_user_connections(user_id)

            assert connections == []


class TestOAuthState:
    """Tests for OAuthState entity."""

    def test_oauth_state_creation(self) -> None:
        """Test creating OAuth state."""
        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GOOGLE,
            tenant_id=uuid4(),
            redirect_uri="http://localhost/callback",
            nonce="test_nonce",
            code_verifier="test_verifier",
            created_at=datetime.now(UTC),
        )

        assert state.state == "test_state"
        assert state.provider == OAuthProvider.GOOGLE

    def test_oauth_state_with_linking(self) -> None:
        """Test creating OAuth state with linking."""
        user_id = uuid4()
        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GITHUB,
            tenant_id=uuid4(),
            redirect_uri="http://localhost/callback",
            nonce="test_nonce",
            code_verifier="test_verifier",
            created_at=datetime.now(UTC),
            is_linking=True,
            existing_user_id=user_id,
        )

        assert state.is_linking is True
        assert state.existing_user_id == user_id


class TestOAuthUserInfo:
    """Tests for OAuthUserInfo entity."""

    def test_oauth_user_info(self) -> None:
        """Test creating OAuth user info."""
        info = OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google123",
            email="test@gmail.com",
            email_verified=True,
            name="Test User",
            given_name="Test",
            family_name="User",
            picture="https://example.com/photo.jpg",
            locale="en",
        )

        assert info.email == "test@gmail.com"
        assert info.email_verified is True


class TestOAuthConnection:
    """Tests for OAuthConnection entity."""

    def test_oauth_connection(self) -> None:
        """Test creating OAuth connection."""
        connection = OAuthConnection(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google123",
            provider_email="test@gmail.com",
            provider_display_name="Test User",
            is_active=True,
            is_primary=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert connection.provider == OAuthProvider.GOOGLE
        assert connection.is_primary is True


class TestOAuthProviderEnum:
    """Tests for OAuthProvider enum."""

    def test_oauth_providers(self) -> None:
        """Test OAuth provider values."""
        assert OAuthProvider.GOOGLE.value == "google"
        assert OAuthProvider.GITHUB.value == "github"
        assert OAuthProvider.MICROSOFT.value == "microsoft"

    def test_oauth_provider_from_string(self) -> None:
        """Test creating OAuth provider from string."""
        provider = OAuthProvider("google")
        assert provider == OAuthProvider.GOOGLE
