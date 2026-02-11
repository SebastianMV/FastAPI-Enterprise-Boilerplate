# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for OAuth Service.

Tests for OAuth2/SSO authentication flows and connection management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.entities.oauth import OAuthProvider, OAuthState, OAuthUserInfo

if TYPE_CHECKING:
    from app.application.services.oauth_service import OAuthService


class TestOAuthServiceInit:
    """Tests for OAuthService initialization."""

    def test_init_with_session(self) -> None:
        """Test OAuthService initializes with session."""
        from app.application.services.oauth_service import OAuthService

        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            service = OAuthService(session=mock_session)

        assert service._session == mock_session
        assert service._cache is not None


class TestOAuthServiceConstants:
    """Tests for OAuthService constants."""

    def test_state_expiration_seconds(self) -> None:
        """Test STATE_EXPIRATION_SECONDS is defined."""
        from app.application.services.oauth_service import OAuthService

        assert OAuthService.STATE_EXPIRATION_SECONDS == 600


class TestOAuthServiceGetDefaultOAuthConfig:
    """Tests for _get_default_oauth_config method."""

    @pytest.fixture
    def oauth_service(self) -> OAuthService:
        """Create OAuthService."""
        from app.application.services.oauth_service import OAuthService

        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            return OAuthService(session=mock_session)

    def test_get_google_config(self, oauth_service) -> None:
        """Test getting Google OAuth config."""
        with patch("app.application.services.oauth_service.settings") as mock_settings:
            mock_settings.OAUTH_GOOGLE_CLIENT_ID = "google-client-id"
            mock_settings.OAUTH_GOOGLE_CLIENT_SECRET = "google-secret"

            client_id, client_secret = oauth_service._get_default_oauth_config(
                OAuthProvider.GOOGLE
            )

            assert client_id == "google-client-id"
            assert client_secret == "google-secret"

    def test_get_github_config(self, oauth_service) -> None:
        """Test getting GitHub OAuth config."""
        with patch("app.application.services.oauth_service.settings") as mock_settings:
            mock_settings.OAUTH_GITHUB_CLIENT_ID = "github-client-id"
            mock_settings.OAUTH_GITHUB_CLIENT_SECRET = "github-secret"

            client_id, client_secret = oauth_service._get_default_oauth_config(
                OAuthProvider.GITHUB
            )

            assert client_id == "github-client-id"
            assert client_secret == "github-secret"

    def test_get_microsoft_config(self, oauth_service) -> None:
        """Test getting Microsoft OAuth config."""
        with patch("app.application.services.oauth_service.settings") as mock_settings:
            mock_settings.OAUTH_MICROSOFT_CLIENT_ID = "ms-client-id"
            mock_settings.OAUTH_MICROSOFT_CLIENT_SECRET = "ms-secret"

            client_id, client_secret = oauth_service._get_default_oauth_config(
                OAuthProvider.MICROSOFT
            )

            assert client_id == "ms-client-id"
            assert client_secret == "ms-secret"

    # Discord provider removed - not implemented
    # def test_get_discord_config(self, oauth_service) -> None:
    #     """Test getting Discord OAuth config."""


class TestOAuthServiceGetRedirectUri:
    """Tests for _get_redirect_uri method."""

    @pytest.fixture
    def oauth_service(self) -> OAuthService:
        """Create OAuthService."""
        from app.application.services.oauth_service import OAuthService

        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            return OAuthService(session=mock_session)

    def test_get_redirect_uri_google(self, oauth_service) -> None:
        """Test getting redirect URI for Google."""
        with patch("app.application.services.oauth_service.settings") as mock_settings:
            mock_settings.APP_BASE_URL = "https://example.com"

            uri = oauth_service._get_redirect_uri(OAuthProvider.GOOGLE)

            assert uri == "https://example.com/api/v1/auth/oauth/google/callback"

    def test_get_redirect_uri_github(self, oauth_service) -> None:
        """Test getting redirect URI for GitHub."""
        with patch("app.application.services.oauth_service.settings") as mock_settings:
            mock_settings.APP_BASE_URL = "https://example.com"

            uri = oauth_service._get_redirect_uri(OAuthProvider.GITHUB)

            assert uri == "https://example.com/api/v1/auth/oauth/github/callback"


class TestOAuthServiceStoreState:
    """Tests for _store_oauth_state method."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.set = AsyncMock()
        cache.get = AsyncMock()
        cache.delete = AsyncMock()
        return cache

    @pytest.fixture
    def oauth_service(self, mock_cache: MagicMock) -> OAuthService:
        """Create OAuthService with mock cache."""
        from app.application.services.oauth_service import OAuthService

        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as cache_factory:
            cache_factory.return_value = mock_cache
            return OAuthService(session=mock_session)

    @pytest.mark.asyncio
    async def test_store_oauth_state(
        self, oauth_service, mock_cache: MagicMock
    ) -> None:
        """Test storing OAuth state."""
        state_data = OAuthState(
            state="test-state",
            provider=OAuthProvider.GOOGLE,
            tenant_id=uuid4(),
            redirect_uri="https://example.com/callback",
            nonce="test-nonce",
            code_verifier="code-verifier",
            is_linking=False,
        )

        await oauth_service._store_oauth_state("test-state", state_data)

        mock_cache.set.assert_awaited_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == "oauth_state:test-state"
        assert call_args[1]["ttl"] == 600


class TestOAuthServiceGetState:
    """Tests for _get_oauth_state method."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.set = AsyncMock()
        cache.get = AsyncMock()
        cache.delete = AsyncMock()
        return cache

    @pytest.fixture
    def oauth_service(self, mock_cache: MagicMock) -> OAuthService:
        """Create OAuthService with mock cache."""
        from app.application.services.oauth_service import OAuthService

        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as cache_factory:
            cache_factory.return_value = mock_cache
            return OAuthService(session=mock_session)

    @pytest.mark.asyncio
    async def test_get_oauth_state_not_found(
        self, oauth_service, mock_cache: MagicMock
    ) -> None:
        """Test getting OAuth state when not found."""
        mock_cache.get.return_value = None

        result = await oauth_service._get_oauth_state("missing-state")

        assert result is None
        mock_cache.get.assert_awaited_once_with("oauth_state:missing-state")

    @pytest.mark.asyncio
    async def test_get_oauth_state_found(
        self, oauth_service, mock_cache: MagicMock
    ) -> None:
        """Test getting OAuth state when found."""
        tenant_id = uuid4()
        mock_cache.get.return_value = {
            "state": "test-state",
            "provider": "google",
            "tenant_id": str(tenant_id),
            "redirect_uri": "https://example.com/callback",
            "nonce": "test-nonce",
            "code_verifier": "verifier",
            "is_linking": False,
            "existing_user_id": None,
        }

        result = await oauth_service._get_oauth_state("test-state")

        assert result is not None
        assert result.state == "test-state"
        assert result.provider == OAuthProvider.GOOGLE
        assert result.tenant_id == tenant_id


class TestOAuthServiceDeleteState:
    """Tests for _delete_oauth_state method."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.delete = AsyncMock()
        return cache

    @pytest.fixture
    def oauth_service(self, mock_cache: MagicMock) -> OAuthService:
        """Create OAuthService with mock cache."""
        from app.application.services.oauth_service import OAuthService

        mock_session = AsyncMock()
        with patch("app.application.services.oauth_service.get_cache") as cache_factory:
            cache_factory.return_value = mock_cache
            return OAuthService(session=mock_session)

    @pytest.mark.asyncio
    async def test_delete_oauth_state(
        self, oauth_service, mock_cache: MagicMock
    ) -> None:
        """Test deleting OAuth state."""
        await oauth_service._delete_oauth_state("test-state")

        mock_cache.delete.assert_awaited_once_with("oauth_state:test-state")


class TestOAuthServiceGetUserConnections:
    """Tests for get_user_connections method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session."""
        return AsyncMock()

    @pytest.fixture
    def oauth_service(self, mock_session: AsyncMock) -> OAuthService:
        """Create OAuthService with mock session."""
        from app.application.services.oauth_service import OAuthService

        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            return OAuthService(session=mock_session)

    @pytest.mark.asyncio
    async def test_get_user_connections_empty(
        self, oauth_service, mock_session: AsyncMock
    ) -> None:
        """Test getting user connections when none exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await oauth_service.get_user_connections(user_id=uuid4())

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_connections_with_results(
        self, oauth_service, mock_session: AsyncMock
    ) -> None:
        """Test getting user connections."""
        connection_id = uuid4()
        user_id = uuid4()
        tenant_id = uuid4()

        mock_model = MagicMock()
        mock_model.id = connection_id
        mock_model.user_id = user_id
        mock_model.tenant_id = tenant_id
        mock_model.provider = "google"
        mock_model.provider_user_id = "12345"
        mock_model.provider_email = "test@example.com"
        mock_model.provider_username = None
        mock_model.provider_display_name = "Test User"
        mock_model.provider_avatar_url = "https://example.com/avatar.jpg"
        mock_model.is_primary = True
        mock_model.is_active = True
        mock_model.scopes = ["email", "profile"]
        mock_model.last_used_at = datetime.now(UTC)
        mock_model.created_at = datetime.now(UTC)
        mock_model.updated_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute.return_value = mock_result

        result = await oauth_service.get_user_connections(user_id=user_id)

        assert len(result) == 1
        assert result[0].provider == OAuthProvider.GOOGLE


class TestOAuthServiceUnlinkAccount:
    """Tests for unlink_oauth_account method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session."""
        session = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def oauth_service(self, mock_session: AsyncMock) -> OAuthService:
        """Create OAuthService with mock session."""
        from app.application.services.oauth_service import OAuthService

        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            return OAuthService(session=mock_session)

    @pytest.mark.asyncio
    async def test_unlink_account_not_found(
        self, oauth_service, mock_session: AsyncMock
    ) -> None:
        """Test unlinking account that doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await oauth_service.unlink_oauth_account(
            user_id=uuid4(),
            connection_id=uuid4(),
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_unlink_non_primary_account(
        self, oauth_service, mock_session: AsyncMock
    ) -> None:
        """Test unlinking non-primary account."""
        mock_connection = MagicMock()
        mock_connection.is_primary = False
        mock_connection.is_active = True
        mock_connection.updated_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_connection
        mock_session.execute.return_value = mock_result

        result = await oauth_service.unlink_oauth_account(
            user_id=uuid4(),
            connection_id=uuid4(),
        )

        assert result is True
        assert mock_connection.is_active is False

    @pytest.mark.asyncio
    async def test_unlink_primary_without_password_raises(
        self, oauth_service, mock_session: AsyncMock
    ) -> None:
        """Test unlinking primary account without password raises."""
        mock_connection = MagicMock()
        mock_connection.is_primary = True

        mock_user = MagicMock()
        mock_user.password_hash = None  # No password set

        mock_result_conn = MagicMock()
        mock_result_conn.scalar_one_or_none.return_value = mock_connection

        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = mock_user

        mock_session.execute.side_effect = [mock_result_conn, mock_result_user]

        with pytest.raises(ValueError, match="Cannot unlink primary"):
            await oauth_service.unlink_oauth_account(
                user_id=uuid4(),
                connection_id=uuid4(),
            )


class TestOAuthServiceGetSSOConfig:
    """Tests for get_sso_config method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session."""
        return AsyncMock()

    @pytest.fixture
    def oauth_service(self, mock_session: AsyncMock) -> OAuthService:
        """Create OAuthService with mock session."""
        from app.application.services.oauth_service import OAuthService

        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            return OAuthService(session=mock_session)

    @pytest.mark.asyncio
    async def test_get_sso_config_empty(
        self, oauth_service, mock_session: AsyncMock
    ) -> None:
        """Test getting SSO config when none exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await oauth_service.get_sso_config(tenant_id=uuid4())

        assert result == []

    @pytest.mark.asyncio
    async def test_get_sso_config_with_provider_filter(
        self, oauth_service, mock_session: AsyncMock
    ) -> None:
        """Test getting SSO config with provider filter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await oauth_service.get_sso_config(
            tenant_id=uuid4(),
            provider=OAuthProvider.GOOGLE,
        )

        mock_session.execute.assert_awaited_once()


class TestOAuthServiceCreateSSOConfig:
    """Tests for create_sso_config method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def oauth_service(self, mock_session: AsyncMock) -> OAuthService:
        """Create OAuthService with mock session."""
        from app.application.services.oauth_service import OAuthService

        with patch("app.application.services.oauth_service.get_cache") as mock_cache:
            mock_cache.return_value = MagicMock()
            return OAuthService(session=mock_session)

    @pytest.mark.asyncio
    async def test_create_sso_config(
        self, oauth_service, mock_session: AsyncMock
    ) -> None:
        """Test creating SSO configuration."""
        tenant_id = uuid4()

        result = await oauth_service.create_sso_config(
            tenant_id=tenant_id,
            provider=OAuthProvider.GOOGLE,
            name="Google SSO",
            client_id="google-client-id",
            client_secret="google-secret",
            scopes=["email", "profile"],
            allowed_domains=["example.com"],
        )

        assert result.provider == OAuthProvider.GOOGLE
        assert result.name == "Google SSO"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()


class TestOAuthServiceInitiateOAuth:
    """Tests for initiate_oauth method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session."""
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.set = AsyncMock()
        return cache

    @pytest.fixture
    def oauth_service(
        self, mock_session: AsyncMock, mock_cache: MagicMock
    ) -> OAuthService:
        """Create OAuthService with mocks."""
        from app.application.services.oauth_service import OAuthService

        with patch("app.application.services.oauth_service.get_cache") as cache_factory:
            cache_factory.return_value = mock_cache
            return OAuthService(session=mock_session)

    @pytest.mark.asyncio
    async def test_initiate_oauth_google(
        self, oauth_service, mock_session: AsyncMock, mock_cache: MagicMock
    ) -> None:
        """Test initiating OAuth flow for Google."""
        mock_provider = MagicMock()
        mock_provider.generate_pkce.return_value = ("verifier", "challenge")
        mock_provider.redirect_uri = "https://example.com/callback"
        mock_provider.get_authorization_url.return_value = (
            "https://accounts.google.com/oauth"
        )

        with patch.object(
            oauth_service, "_get_provider", return_value=mock_provider
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            auth_url, state = await oauth_service.initiate_oauth(
                provider=OAuthProvider.GOOGLE,
            )

        assert "https://accounts.google.com" in auth_url
        assert len(state) > 0
        mock_cache.set.assert_awaited_once()


class TestOAuthServiceHandleCallback:
    """Tests for handle_callback method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session."""
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock cache."""
        cache = MagicMock()
        cache.get = AsyncMock()
        cache.delete = AsyncMock()
        return cache

    @pytest.fixture
    def oauth_service(
        self, mock_session: AsyncMock, mock_cache: MagicMock
    ) -> OAuthService:
        """Create OAuthService with mocks."""
        from app.application.services.oauth_service import OAuthService

        with patch("app.application.services.oauth_service.get_cache") as cache_factory:
            cache_factory.return_value = mock_cache
            return OAuthService(session=mock_session)

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_state(
        self, oauth_service, mock_cache: MagicMock
    ) -> None:
        """Test handle_callback with invalid state."""
        mock_cache.get.return_value = None

        with pytest.raises(ValueError, match="Invalid or expired OAuth state"):
            await oauth_service.handle_callback(
                provider=OAuthProvider.GOOGLE,
                code="auth-code",
                state="invalid-state",
            )

    @pytest.mark.asyncio
    async def test_handle_callback_provider_mismatch(
        self, oauth_service, mock_cache: MagicMock
    ) -> None:
        """Test handle_callback with provider mismatch."""
        mock_cache.get.return_value = {
            "state": "test-state",
            "provider": "github",  # Different provider
            "tenant_id": None,
            "redirect_uri": "https://example.com/callback",
            "nonce": "nonce",
            "code_verifier": "verifier",
            "is_linking": False,
            "existing_user_id": None,
        }

        with pytest.raises(ValueError, match="Provider mismatch"):
            await oauth_service.handle_callback(
                provider=OAuthProvider.GOOGLE,
                code="auth-code",
                state="test-state",
            )


class TestOAuthProvider:
    """Tests for OAuthProvider enum."""

    def test_provider_values(self) -> None:
        """Test OAuth provider values."""
        assert OAuthProvider.GOOGLE.value == "google"
        assert OAuthProvider.GITHUB.value == "github"
        assert OAuthProvider.MICROSOFT.value == "microsoft"
        # Discord provider removed - not implemented
        # assert OAuthProvider.DISCORD.value == "discord"


class TestOAuthState:
    """Tests for OAuthState entity."""

    def test_create_state(self) -> None:
        """Test creating OAuth state."""
        state = OAuthState(
            state="test-state",
            provider=OAuthProvider.GOOGLE,
            tenant_id=uuid4(),
            redirect_uri="https://example.com/callback",
        )

        assert state.state == "test-state"
        assert state.provider == OAuthProvider.GOOGLE

    def test_state_with_linking(self) -> None:
        """Test OAuth state for account linking."""
        user_id = uuid4()
        state = OAuthState(
            state="linking-state",
            provider=OAuthProvider.GITHUB,
            is_linking=True,
            existing_user_id=user_id,
        )

        assert state.is_linking is True
        assert state.existing_user_id == user_id


class TestOAuthUserInfo:
    """Tests for OAuthUserInfo entity."""

    def test_create_user_info(self) -> None:
        """Test creating OAuth user info."""
        user_info = OAuthUserInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="12345",
            email="user@example.com",
            name="Test User",
            picture="https://example.com/avatar.jpg",
            raw_data={"email_verified": True},
        )

        assert user_info.provider == OAuthProvider.GOOGLE
        assert user_info.email == "user@example.com"
        assert user_info.name == "Test User"

    def test_user_info_minimal(self) -> None:
        """Test OAuth user info with minimal data."""
        user_info = OAuthUserInfo(
            provider=OAuthProvider.GITHUB,
            provider_user_id="67890",
            raw_data={},
        )

        assert user_info.provider_user_id == "67890"
        assert user_info.email is None
        assert user_info.name is None
