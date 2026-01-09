# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for OAuth service with real execution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta, UTC
import pytest

from app.application.services.oauth_service import OAuthService
from app.domain.entities.oauth import (
    OAuthConnection,
    OAuthProvider,
    OAuthState,
    OAuthUserInfo,
    SSOConfiguration,
)


class TestOAuthServiceCreation:
    """Tests for OAuthService creation."""

    def test_service_requires_session(self) -> None:
        """Test OAuthService requires session parameter."""
        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            service = OAuthService(session=mock_session)
            assert service is not None

    def test_service_has_session(self) -> None:
        """Test OAuthService stores session."""
        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            service = OAuthService(session=mock_session)
            assert service._session is mock_session

    def test_state_expiration_constant(self) -> None:
        """Test STATE_EXPIRATION_SECONDS constant."""
        assert OAuthService.STATE_EXPIRATION_SECONDS == 600


class TestOAuthProvider:
    """Tests for OAuthProvider enum."""

    def test_google_provider(self) -> None:
        """Test Google provider enum."""
        assert OAuthProvider.GOOGLE is not None

    def test_github_provider(self) -> None:
        """Test GitHub provider enum."""
        assert OAuthProvider.GITHUB is not None

    def test_microsoft_provider(self) -> None:
        """Test Microsoft provider enum."""
        assert OAuthProvider.MICROSOFT is not None


class TestOAuthState:
    """Tests for OAuthState entity."""

    def test_oauth_state_creation(self) -> None:
        """Test OAuthState creation."""
        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GOOGLE,
            tenant_id=None,
            redirect_uri="http://localhost/callback",
            nonce="test_nonce",
            code_verifier="test_verifier",
            created_at=datetime.now(UTC),
        )
        assert state.state == "test_state"
        assert state.provider == OAuthProvider.GOOGLE

    def test_oauth_state_with_tenant(self) -> None:
        """Test OAuthState with tenant."""
        tenant_id = uuid4()
        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.GITHUB,
            tenant_id=tenant_id,
            redirect_uri="http://localhost/callback",
            nonce="test_nonce",
            code_verifier="test_verifier",
            created_at=datetime.now(UTC),
        )
        assert state.tenant_id == tenant_id

    def test_oauth_state_with_linking(self) -> None:
        """Test OAuthState with linking user."""
        linking_id = uuid4()
        state = OAuthState(
            state="test_state",
            provider=OAuthProvider.MICROSOFT,
            tenant_id=None,
            redirect_uri="http://localhost/callback",
            nonce="test_nonce",
            code_verifier="test_verifier",
            created_at=datetime.now(UTC),
            is_linking=True,
            existing_user_id=linking_id,
        )
        assert state.existing_user_id == linking_id
        assert state.is_linking is True


class TestOAuthUserInfo:
    """Tests for OAuthUserInfo entity."""

    def test_user_info_creation(self) -> None:
        """Test OAuthUserInfo creation."""
        info = OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="12345",
            email="test@example.com",
            email_verified=True,
        )
        assert info.email == "test@example.com"
        assert info.email_verified is True

    def test_user_info_with_name(self) -> None:
        """Test OAuthUserInfo with name."""
        info = OAuthUserInfo(
            provider=OAuthProvider.GITHUB,
            provider_user_id="gh_123",
            email="user@github.com",
            email_verified=True,
            name="John Doe",
        )
        assert info.name == "John Doe"

    def test_user_info_with_avatar(self) -> None:
        """Test OAuthUserInfo with avatar."""
        info = OAuthUserInfo(
            provider=OAuthProvider.MICROSOFT,
            provider_user_id="ms_456",
            email="user@outlook.com",
            email_verified=False,
            picture="https://example.com/avatar.jpg",
        )
        assert info.picture == "https://example.com/avatar.jpg"


class TestOAuthConnection:
    """Tests for OAuthConnection entity."""

    def test_oauth_connection_creation(self) -> None:
        """Test OAuthConnection creation."""
        user_id = uuid4()
        tenant_id = uuid4()
        connection = OAuthConnection(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google_123",
            provider_email="user@example.com",
        )
        assert connection.provider == OAuthProvider.GOOGLE
        assert connection.user_id == user_id

    def test_oauth_connection_with_tokens(self) -> None:
        """Test OAuthConnection with tokens."""
        user_id = uuid4()
        tenant_id = uuid4()
        expires = datetime.now(UTC) + timedelta(hours=1)
        connection = OAuthConnection(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            provider=OAuthProvider.GITHUB,
            provider_user_id="gh_456",
            provider_email="user@github.com",
            access_token="access_123",
            refresh_token="refresh_456",
            token_expires_at=expires,
        )
        assert connection.access_token == "access_123"
        assert connection.refresh_token == "refresh_456"


class TestSSOConfiguration:
    """Tests for SSOConfiguration entity."""

    def test_sso_config_creation(self) -> None:
        """Test SSOConfiguration creation."""
        tenant_id = uuid4()
        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=tenant_id,
            provider=OAuthProvider.GOOGLE,
            name="Corporate SSO",
            client_id="client_123",
            client_secret="secret_456",
            is_enabled=True,
        )
        assert config.client_id == "client_123"
        assert config.is_enabled is True

    def test_sso_config_disabled(self) -> None:
        """Test disabled SSOConfiguration."""
        tenant_id = uuid4()
        config = SSOConfiguration(
            id=uuid4(),
            tenant_id=tenant_id,
            provider=OAuthProvider.MICROSOFT,
            name="MS SSO",
            client_id="client_xyz",
            client_secret="secret_xyz",
            is_enabled=False,
        )
        assert config.is_enabled is False


class TestOAuthServiceMethods:
    """Tests for OAuthService methods."""

    @pytest.mark.asyncio
    async def test_service_has_initiate_oauth_method(self) -> None:
        """Test initiate_oauth method exists."""
        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            service = OAuthService(session=mock_session)
            assert hasattr(service, "initiate_oauth")

    @pytest.mark.asyncio
    async def test_service_has_handle_callback_method(self) -> None:
        """Test handle_callback method exists."""
        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            service = OAuthService(session=mock_session)
            assert hasattr(service, "handle_callback")

    @pytest.mark.asyncio
    async def test_service_has_get_user_connections_method(self) -> None:
        """Test get_user_connections method exists."""
        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            service = OAuthService(session=mock_session)
            assert hasattr(service, "get_user_connections")

    @pytest.mark.asyncio
    async def test_service_has_disconnect_provider_method(self) -> None:
        """Test unlink_oauth_account method exists."""
        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            service = OAuthService(session=mock_session)
            assert hasattr(service, "unlink_oauth_account")

    @pytest.mark.asyncio
    async def test_service_has_get_sso_config_method(self) -> None:
        """Test get_sso_config method exists."""
        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            service = OAuthService(session=mock_session)
            assert hasattr(service, "get_sso_config")
