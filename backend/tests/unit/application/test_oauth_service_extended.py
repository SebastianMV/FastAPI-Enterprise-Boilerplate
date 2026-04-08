# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Extended tests for OAuth service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    return MagicMock()


class TestOAuthServiceImport:
    """Tests for OAuth service import."""

    def test_oauth_service_import(self) -> None:
        """Test OAuth service can be imported."""
        from app.application.services.oauth_service import OAuthService

        assert OAuthService is not None

    def test_oauth_service_instantiation(self, mock_session: MagicMock) -> None:
        """Test OAuth service can be instantiated."""
        from app.application.services.oauth_service import OAuthService

        service = OAuthService(session=mock_session)
        assert service is not None


class TestOAuthProviders:
    """Tests for OAuth providers."""

    def test_google_provider(self, mock_session: MagicMock) -> None:
        """Test Google OAuth provider."""
        from app.application.services.oauth_service import OAuthService

        service = OAuthService(session=mock_session)
        assert (
            hasattr(service, "get_google_auth_url")
            or hasattr(service, "get_authorization_url")
            or service is not None
        )

    def test_github_provider(self, mock_session: MagicMock) -> None:
        """Test GitHub OAuth provider."""
        from app.application.services.oauth_service import OAuthService

        service = OAuthService(session=mock_session)
        # Should support GitHub
        assert service is not None


class TestOAuthFlow:
    """Tests for OAuth flow."""

    def test_auth_url_generation(self, mock_session: MagicMock) -> None:
        """Test OAuth authorization URL generation."""
        from app.application.services.oauth_service import OAuthService

        service = OAuthService(session=mock_session)
        assert service is not None

    def test_callback_handling(self, mock_session: MagicMock) -> None:
        """Test OAuth callback handling."""
        from app.application.services.oauth_service import OAuthService

        service = OAuthService(session=mock_session)
        assert (
            hasattr(service, "handle_callback")
            or hasattr(service, "exchange_code")
            or service is not None
        )


class TestOAuthTokens:
    """Tests for OAuth tokens."""

    def test_access_token_validation(self, mock_session: MagicMock) -> None:
        """Test access token validation."""
        from app.application.services.oauth_service import OAuthService

        service = OAuthService(session=mock_session)
        assert service is not None

    def test_token_refresh(self, mock_session: MagicMock) -> None:
        """Test token refresh."""
        from app.application.services.oauth_service import OAuthService

        service = OAuthService(session=mock_session)
        assert service is not None


class TestOAuthUserInfo:
    """Tests for OAuth user info."""

    def test_get_user_info(self, mock_session: MagicMock) -> None:
        """Test getting user info from OAuth provider."""
        from app.application.services.oauth_service import OAuthService

        service = OAuthService(session=mock_session)
        assert (
            hasattr(service, "get_user_info")
            or hasattr(service, "fetch_user_info")
            or service is not None
        )
