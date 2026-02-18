# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for OAuth Service to improve coverage.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.oauth_service import OAuthService
from app.domain.entities.oauth import (
    OAuthProvider,
    OAuthState,
    OAuthUserInfo,
)
from app.domain.entities.user import User
from app.domain.exceptions.base import (
    AuthenticationError,
    BusinessRuleViolationError,
    ConflictError,
    EntityNotFoundError,
)
from app.infrastructure.auth.oauth_providers import OAuthTokenResponse


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def oauth_service(mock_session):
    """OAuth service instance."""
    with patch("app.application.services.oauth_service.get_cache"):
        service = OAuthService(mock_session)
        service._cache = MagicMock()
        return service


@pytest.fixture
def sample_user():
    """Sample user entity."""
    return User(
        id=uuid4(),
        tenant_id=uuid4(),
        email="test@example.com",
        password_hash="hash",
        is_active=True,
        is_superuser=False,
        email_verified=True,
        roles=[],
    )


@pytest.fixture
def sample_oauth_tokens():
    """Sample OAuth token response."""
    return OAuthTokenResponse(
        access_token="access_token_123",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="refresh_token_123",
        scope="email profile",
    )


@pytest.fixture
def sample_oauth_user_info():
    """Sample OAuth user info."""
    return OAuthUserInfo(
        provider=OAuthProvider.GOOGLE,
        provider_user_id="google_123",
        email="oauth@example.com",
        email_verified=True,
        name="OAuth User",
        picture="https://example.com/pic.jpg",
    )


class TestInitiateOAuth:
    """Tests for initiate_oauth method."""

    @pytest.mark.asyncio
    async def test_initiate_oauth_generates_state_and_url(self, oauth_service):
        """Test OAuth initiation generates state and authorization URL."""
        mock_provider = MagicMock()
        mock_provider.generate_pkce = MagicMock(return_value=("verifier", "challenge"))
        mock_provider.get_authorization_url = MagicMock(
            return_value="https://oauth.com/auth"
        )
        mock_provider.redirect_uri = "https://app.com/callback"

        with (
            patch.object(oauth_service, "_get_provider", return_value=mock_provider),
            patch.object(oauth_service, "_store_oauth_state", new_callable=AsyncMock),
        ):
            auth_url, state = await oauth_service.initiate_oauth(
                provider=OAuthProvider.GOOGLE, tenant_id=uuid4()
            )

            assert auth_url == "https://oauth.com/auth"
            assert len(state) > 0
            mock_provider.generate_pkce.assert_called_once()
            mock_provider.get_authorization_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_initiate_oauth_with_custom_redirect(self, oauth_service):
        """Test OAuth initiation with custom redirect URI."""
        mock_provider = MagicMock()
        mock_provider.generate_pkce = MagicMock(return_value=("verifier", "challenge"))
        mock_provider.get_authorization_url = MagicMock(
            return_value="https://oauth.com/auth"
        )
        mock_provider.redirect_uri = "https://app.com/callback"

        custom_redirect = "https://custom.com/callback"

        with (
            patch.object(oauth_service, "_get_provider", return_value=mock_provider),
            patch.object(
                oauth_service, "_store_oauth_state", new_callable=AsyncMock
            ) as mock_store,
        ):
            await oauth_service.initiate_oauth(
                provider=OAuthProvider.GITHUB, redirect_uri=custom_redirect
            )

            # Verify state data includes custom redirect
            call_args = mock_store.call_args
            state_data = call_args[0][1]
            assert state_data.redirect_uri == custom_redirect

    @pytest.mark.asyncio
    async def test_initiate_oauth_for_linking(self, oauth_service):
        """Test OAuth initiation for account linking."""
        mock_provider = MagicMock()
        mock_provider.generate_pkce = MagicMock(return_value=("verifier", "challenge"))
        mock_provider.get_authorization_url = MagicMock(
            return_value="https://oauth.com/auth"
        )
        mock_provider.redirect_uri = "https://app.com/callback"

        user_id = uuid4()

        with (
            patch.object(oauth_service, "_get_provider", return_value=mock_provider),
            patch.object(
                oauth_service, "_store_oauth_state", new_callable=AsyncMock
            ) as mock_store,
        ):
            await oauth_service.initiate_oauth(
                provider=OAuthProvider.MICROSOFT, linking_user_id=user_id
            )

            # Verify linking flag is set
            state_data = mock_store.call_args[0][1]
            assert state_data.is_linking is True
            assert state_data.existing_user_id == user_id


class TestHandleCallback:
    """Tests for handle_callback method."""

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_state(self, oauth_service):
        """Test callback with invalid state."""
        with patch.object(oauth_service, "_get_oauth_state", return_value=None):
            with pytest.raises(
                AuthenticationError, match="Invalid or expired OAuth state"
            ):
                await oauth_service.handle_callback(
                    provider=OAuthProvider.GOOGLE,
                    code="auth_code",
                    state="invalid_state",
                )

    @pytest.mark.asyncio
    async def test_handle_callback_provider_mismatch(self, oauth_service):
        """Test callback with provider mismatch."""
        state_data = OAuthState(
            state="valid_state",
            provider=OAuthProvider.GOOGLE,
            tenant_id=uuid4(),
            redirect_uri="https://app.com/callback",
            nonce="nonce",
            code_verifier="verifier",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            is_linking=False,
            existing_user_id=None,
        )

        with patch.object(oauth_service, "_get_oauth_state", return_value=state_data):
            with pytest.raises(AuthenticationError, match="Provider mismatch"):
                await oauth_service.handle_callback(
                    provider=OAuthProvider.GITHUB,  # Different provider
                    code="auth_code",
                    state="valid_state",
                )

    @pytest.mark.asyncio
    async def test_handle_callback_success_new_user(
        self, oauth_service, sample_user, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test successful callback creating new user."""
        tenant_id = uuid4()
        state_data = OAuthState(
            state="valid_state",
            provider=OAuthProvider.GOOGLE,
            tenant_id=tenant_id,
            redirect_uri="https://app.com/callback",
            nonce="nonce",
            code_verifier="verifier",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            is_linking=False,
            existing_user_id=None,
        )

        mock_provider = AsyncMock()
        mock_provider.exchange_code = AsyncMock(return_value=sample_oauth_tokens)
        mock_provider.get_user_info = AsyncMock(return_value=sample_oauth_user_info)

        mock_connection = MagicMock()

        with (
            patch.object(oauth_service, "_get_oauth_state", return_value=state_data),
            patch.object(oauth_service, "_delete_oauth_state", new_callable=AsyncMock),
            patch.object(oauth_service, "_get_provider", return_value=mock_provider),
            patch.object(
                oauth_service,
                "_find_or_create_user",
                new_callable=AsyncMock,
                return_value=(sample_user, mock_connection, True),
            ),
        ):
            user, connection, is_new = await oauth_service.handle_callback(
                provider=OAuthProvider.GOOGLE, code="auth_code", state="valid_state"
            )

            assert user == sample_user
            assert is_new is True
            mock_provider.exchange_code.assert_called_once_with(
                code="auth_code", code_verifier="verifier"
            )

    @pytest.mark.asyncio
    async def test_handle_callback_linking_existing_user(
        self, oauth_service, sample_user, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test callback for linking OAuth to existing user."""
        user_id = uuid4()
        tenant_id = uuid4()

        state_data = OAuthState(
            state="valid_state",
            provider=OAuthProvider.GOOGLE,
            tenant_id=tenant_id,
            redirect_uri="https://app.com/callback",
            nonce="nonce",
            code_verifier="verifier",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            is_linking=True,
            existing_user_id=user_id,
        )

        mock_provider = AsyncMock()
        mock_provider.exchange_code = AsyncMock(return_value=sample_oauth_tokens)
        mock_provider.get_user_info = AsyncMock(return_value=sample_oauth_user_info)

        mock_connection = MagicMock()

        with (
            patch.object(oauth_service, "_get_oauth_state", return_value=state_data),
            patch.object(oauth_service, "_delete_oauth_state", new_callable=AsyncMock),
            patch.object(oauth_service, "_get_provider", return_value=mock_provider),
            patch.object(
                oauth_service,
                "_link_oauth_account",
                new_callable=AsyncMock,
                return_value=(sample_user, mock_connection),
            ),
        ):
            user, connection, is_new = await oauth_service.handle_callback(
                provider=OAuthProvider.GOOGLE, code="auth_code", state="valid_state"
            )

            assert user == sample_user
            assert is_new is False


class TestFindOrCreateUser:
    """Tests for _find_or_create_user method."""

    @pytest.mark.asyncio
    async def test_find_existing_oauth_connection(
        self, oauth_service, sample_user, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test finding existing OAuth connection."""
        existing_connection = MagicMock()
        existing_connection.id = uuid4()
        existing_connection.user_id = sample_user.id

        with (
            patch.object(
                oauth_service,
                "_check_allowed_domains",
                new_callable=AsyncMock,
            ),
            patch.object(
                oauth_service,
                "_get_oauth_connection",
                new_callable=AsyncMock,
                return_value=existing_connection,
            ),
            patch.object(
                oauth_service, "_update_oauth_connection", new_callable=AsyncMock
            ),
            patch.object(
                oauth_service,
                "_get_user_by_id",
                new_callable=AsyncMock,
                return_value=sample_user,
            ),
        ):
            user, connection, is_new = await oauth_service._find_or_create_user(
                tenant_id=sample_user.tenant_id,
                user_info=sample_oauth_user_info,
                tokens=sample_oauth_tokens,
            )

            assert user == sample_user
            assert is_new is False

    @pytest.mark.asyncio
    async def test_create_new_user_from_oauth(
        self, oauth_service, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test creating new user from OAuth."""
        new_user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=sample_oauth_user_info.email,
            password_hash="",
            is_active=True,
            is_superuser=False,
            email_verified=True,
            roles=[],
        )

        mock_connection = MagicMock()

        with (
            patch.object(
                oauth_service,
                "_check_allowed_domains",
                new_callable=AsyncMock,
            ),
            patch.object(
                oauth_service,
                "_get_oauth_connection",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                oauth_service,
                "_get_user_by_email",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                oauth_service,
                "_create_user_from_oauth",
                new_callable=AsyncMock,
                return_value=new_user,
            ),
            patch.object(
                oauth_service,
                "_create_oauth_connection",
                new_callable=AsyncMock,
                return_value=mock_connection,
            ),
        ):
            user, connection, is_new = await oauth_service._find_or_create_user(
                tenant_id=uuid4(),
                user_info=sample_oauth_user_info,
                tokens=sample_oauth_tokens,
            )

            assert is_new is True


class TestLinkOAuthAccount:
    """Tests for _link_oauth_account method."""

    @pytest.mark.asyncio
    async def test_link_oauth_to_user(
        self, oauth_service, sample_user, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test linking OAuth account to existing user."""
        mock_connection = MagicMock()

        with (
            patch.object(
                oauth_service,
                "_get_user_by_id",
                new_callable=AsyncMock,
                return_value=sample_user,
            ),
            patch.object(
                oauth_service,
                "_get_oauth_connection",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                oauth_service,
                "_create_oauth_connection",
                new_callable=AsyncMock,
                return_value=mock_connection,
            ),
        ):
            user, connection = await oauth_service._link_oauth_account(
                user_id=sample_user.id,
                tenant_id=sample_user.tenant_id,
                user_info=sample_oauth_user_info,
                tokens=sample_oauth_tokens,
            )

            assert user == sample_user
            assert connection == mock_connection


class TestUserConnections:
    """Tests for get_user_connections method."""

    @pytest.mark.asyncio
    async def test_get_user_connections(self, oauth_service, sample_user):
        """Test retrieving user's OAuth connections."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock())
        mock_result.scalars.return_value.all = MagicMock(return_value=[])

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        connections = await oauth_service.get_user_connections(sample_user.id)

        assert isinstance(connections, list)
        oauth_service._session.execute.assert_called_once()


class TestUnlinkOAuthAccount:
    """Tests for unlink_oauth_account method."""

    @pytest.mark.asyncio
    async def test_unlink_oauth_account(self, oauth_service):
        """Test unlinking OAuth account."""
        connection_id = uuid4()
        user_id = uuid4()

        mock_result = MagicMock()
        mock_connection = MagicMock()
        mock_connection.user_id = user_id
        mock_connection.is_primary = False
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_connection)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)
        oauth_service._session.flush = AsyncMock()

        result = await oauth_service.unlink_oauth_account(user_id, connection_id)

        assert result is True
        assert mock_connection.is_active is False
        oauth_service._session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlink_nonexistent_connection(self, oauth_service):
        """Test unlinking non-existent connection."""
        connection_id = uuid4()
        user_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        result = await oauth_service.unlink_oauth_account(user_id, connection_id)

        assert result is False


class TestSSOConfiguration:
    """Tests for SSO configuration methods."""

    @pytest.mark.asyncio
    async def test_get_sso_config(self, oauth_service):
        """Test retrieving SSO configuration."""
        tenant_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock())
        mock_result.scalars.return_value.all = MagicMock(return_value=[])

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        config = await oauth_service.get_sso_config(tenant_id, OAuthProvider.GOOGLE)

        assert config == []

    @pytest.mark.asyncio
    async def test_create_sso_config(self, oauth_service):
        """Test creating SSO configuration."""
        tenant_id = uuid4()

        oauth_service._session.add = MagicMock()

        with patch.object(oauth_service, "_model_to_sso_config") as mock_convert:
            mock_sso = MagicMock()
            mock_convert.return_value = mock_sso

            config = await oauth_service.create_sso_config(
                tenant_id=tenant_id,
                provider=OAuthProvider.GOOGLE,
                name="Corporate SSO",
                client_id="client_123",
                client_secret="secret_123",
                is_enabled=True,
            )

            assert config is not None
            oauth_service._session.add.assert_called_once()
            oauth_service._session.flush.assert_called_once()


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.mark.asyncio
    async def test_store_oauth_state(self, oauth_service):
        """Test storing OAuth state in cache."""
        state = "test_state"
        state_data = OAuthState(
            state=state,
            provider=OAuthProvider.GOOGLE,
            tenant_id=uuid4(),
            redirect_uri="https://app.com/callback",
            nonce="nonce",
            code_verifier="verifier",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            is_linking=False,
            existing_user_id=None,
        )

        oauth_service._cache.set = AsyncMock()

        await oauth_service._store_oauth_state(state, state_data)

        oauth_service._cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_oauth_state(self, oauth_service):
        """Test retrieving OAuth state from cache."""
        state = "test_state"

        oauth_service._cache.get = AsyncMock(return_value=None)

        result = await oauth_service._get_oauth_state(state)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_oauth_state(self, oauth_service):
        """Test deleting OAuth state from cache."""
        state = "test_state"

        oauth_service._cache.delete = AsyncMock()

        await oauth_service._delete_oauth_state(state)

        oauth_service._cache.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_default_tenant_id(self, oauth_service):
        """Test getting default tenant ID."""
        mock_result = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_tenant)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        tenant_id = await oauth_service._get_default_tenant_id()

        assert tenant_id == mock_tenant.id

    @pytest.mark.asyncio
    async def test_get_default_tenant_id_not_found(self, oauth_service):
        """Test getting default tenant when none exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(EntityNotFoundError, match="No default tenant found"):
            await oauth_service._get_default_tenant_id()

    @pytest.mark.asyncio
    async def test_get_provider_with_sso_config(self, oauth_service):
        """Test getting provider with tenant SSO config."""
        tenant_id = uuid4()

        mock_sso_config = MagicMock()
        mock_sso_config.client_id = "custom_client_id"
        mock_sso_config.client_secret = "custom_secret"

        with (
            patch.object(
                oauth_service,
                "get_sso_config",
                new_callable=AsyncMock,
                return_value=[mock_sso_config],
            ),
            patch(
                "app.application.services.oauth_service.get_oauth_provider"
            ) as mock_get_provider,
        ):
            await oauth_service._get_provider(OAuthProvider.GOOGLE, tenant_id)

            mock_get_provider.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_provider_without_sso_config(self, oauth_service):
        """Test getting provider without SSO config."""
        with (
            patch.object(
                oauth_service, "get_sso_config", new_callable=AsyncMock, return_value=[]
            ),
            patch(
                "app.application.services.oauth_service.get_oauth_provider"
            ) as mock_get_provider,
        ):
            await oauth_service._get_provider(OAuthProvider.GOOGLE, None)

            mock_get_provider.assert_called_once()

    def test_get_default_oauth_config(self, oauth_service):
        """Test getting default OAuth config."""
        config = oauth_service._get_default_oauth_config(OAuthProvider.GOOGLE)

        assert isinstance(config, tuple)
        assert len(config) == 2

    def test_get_redirect_uri(self, oauth_service):
        """Test building redirect URI."""
        uri = oauth_service._get_redirect_uri(OAuthProvider.GOOGLE)

        assert "/api/v1/auth/oauth/google/callback" in uri

    @pytest.mark.asyncio
    async def test_link_oauth_already_linked_to_same_user(
        self, oauth_service, sample_user, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test linking OAuth when already linked to same user."""
        mock_connection = MagicMock()
        mock_connection.user_id = sample_user.id

        with (
            patch.object(
                oauth_service,
                "_get_oauth_connection",
                new_callable=AsyncMock,
                return_value=mock_connection,
            ),
            patch.object(
                oauth_service,
                "_get_user_by_id",
                new_callable=AsyncMock,
                return_value=sample_user,
            ),
        ):
            user, connection = await oauth_service._link_oauth_account(
                user_id=sample_user.id,
                tenant_id=sample_user.tenant_id,
                user_info=sample_oauth_user_info,
                tokens=sample_oauth_tokens,
            )

            assert user == sample_user
            assert connection == mock_connection

    @pytest.mark.asyncio
    async def test_link_oauth_already_linked_to_different_user(
        self, oauth_service, sample_user, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test linking OAuth when already linked to different user."""
        different_user_id = uuid4()

        mock_connection = MagicMock()
        mock_connection.user_id = different_user_id  # Different user

        with (
            patch.object(
                oauth_service,
                "_get_oauth_connection",
                new_callable=AsyncMock,
                return_value=mock_connection,
            ),
            pytest.raises(
                ConflictError, match="This OAuth account is linked to another user"
            ),
        ):
            await oauth_service._link_oauth_account(
                user_id=sample_user.id,
                tenant_id=sample_user.tenant_id,
                user_info=sample_oauth_user_info,
                tokens=sample_oauth_tokens,
            )

    @pytest.mark.asyncio
    async def test_find_or_create_user_with_existing_email(
        self, oauth_service, sample_user, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test finding user when email already exists."""
        mock_connection = MagicMock()

        with (
            patch.object(
                oauth_service,
                "_check_allowed_domains",
                new_callable=AsyncMock,
            ),
            patch.object(
                oauth_service,
                "_get_oauth_connection",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                oauth_service,
                "_get_user_by_email",
                new_callable=AsyncMock,
                return_value=sample_user,
            ),
            patch.object(
                oauth_service,
                "_create_oauth_connection",
                new_callable=AsyncMock,
                return_value=mock_connection,
            ),
        ):
            user, connection, is_new = await oauth_service._find_or_create_user(
                tenant_id=sample_user.tenant_id,
                user_info=sample_oauth_user_info,
                tokens=sample_oauth_tokens,
            )

            assert user == sample_user
            assert is_new is False

    @pytest.mark.asyncio
    async def test_unlink_primary_oauth_without_password(self, oauth_service):
        """Test unlinking primary OAuth when user has no password."""
        connection_id = uuid4()
        user_id = uuid4()

        mock_connection = MagicMock()
        mock_connection.user_id = user_id
        mock_connection.is_primary = True

        mock_user = MagicMock()
        mock_user.password_hash = None  # No password

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_connection)

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none = MagicMock(return_value=mock_user)

        oauth_service._session.execute = AsyncMock(
            side_effect=[mock_result, mock_user_result]
        )

        with pytest.raises(
            BusinessRuleViolationError,
            match="Cannot unlink primary OAuth account without setting a password",
        ):
            await oauth_service.unlink_oauth_account(user_id, connection_id)


class TestPrivateMethods:
    """Tests for private helper methods."""

    @pytest.mark.asyncio
    async def test_get_oauth_state_with_data(self, oauth_service):
        """Test getting OAuth state with cache data."""
        state = "test_state"
        tenant_id = uuid4()
        user_id = uuid4()

        cache_data = {
            "state": state,
            "provider": "google",
            "tenant_id": str(tenant_id),
            "redirect_uri": "https://app.com/callback",
            "nonce": "nonce123",
            "code_verifier": "verifier123",
            "is_linking": True,
            "existing_user_id": str(user_id),
        }

        oauth_service._cache.get = AsyncMock(return_value=cache_data)

        result = await oauth_service._get_oauth_state(state)

        assert result is not None
        assert result.state == state
        assert result.provider == OAuthProvider.GOOGLE
        assert result.tenant_id == tenant_id
        assert result.is_linking is True

    @pytest.mark.asyncio
    async def test_get_oauth_connection_exists(self, oauth_service):
        """Test getting existing OAuth connection."""
        provider_user_id = "google_123"

        mock_model = MagicMock()
        mock_model.id = uuid4()
        mock_model.user_id = uuid4()
        mock_model.tenant_id = uuid4()
        mock_model.provider = "google"
        mock_model.provider_user_id = provider_user_id
        mock_model.provider_email = "test@example.com"
        mock_model.provider_username = None
        mock_model.provider_display_name = "Test User"
        mock_model.provider_avatar_url = "https://example.com/avatar.jpg"
        mock_model.access_token = None
        mock_model.refresh_token = None
        mock_model.token_expires_at = datetime.now(UTC)
        mock_model.scopes = ["email", "profile"]
        mock_model.raw_data = {}
        mock_model.is_primary = False
        mock_model.is_active = True
        mock_model.last_used_at = datetime.now(UTC)
        mock_model.created_at = datetime.now(UTC)
        mock_model.updated_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_model)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        result = await oauth_service._get_oauth_connection(
            provider=OAuthProvider.GOOGLE, provider_user_id=provider_user_id
        )

        assert result is not None
        assert result.provider_user_id == provider_user_id

    @pytest.mark.asyncio
    async def test_create_oauth_connection_with_all_data(
        self, oauth_service, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test creating OAuth connection with complete data."""
        user_id = uuid4()
        tenant_id = uuid4()

        oauth_service._session.add = MagicMock()
        oauth_service._session.flush = AsyncMock()

        result = await oauth_service._create_oauth_connection(
            user_id=user_id,
            tenant_id=tenant_id,
            user_info=sample_oauth_user_info,
            tokens=sample_oauth_tokens,
            is_primary=True,
        )

        assert result is not None
        oauth_service._session.add.assert_called_once()
        oauth_service._session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_oauth_connection_with_all_tokens(self, oauth_service):
        """Test updating OAuth connection with new tokens."""
        connection_id = uuid4()

        mock_model = MagicMock()
        mock_model.id = connection_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_model)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)
        oauth_service._session.flush = AsyncMock()

        with patch(
            "app.application.services.oauth_service.encrypt_value",
            side_effect=lambda x: x,
        ):
            await oauth_service._update_oauth_connection(
                connection_id=connection_id,
                access_token="new_access_token",
                refresh_token="new_refresh_token",
                expires_in=3600,
            )

        assert mock_model.access_token == "new_access_token"
        assert mock_model.refresh_token == "new_refresh_token"
        oauth_service._session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_id_exists(self, oauth_service):
        """Test getting user by ID when exists."""
        user_id = uuid4()
        tenant_id = uuid4()

        mock_user_model = MagicMock()
        mock_user_model.id = user_id
        mock_user_model.tenant_id = tenant_id
        mock_user_model.email = "user@example.com"
        mock_user_model.password_hash = "hashed_password"
        mock_user_model.first_name = "John"
        mock_user_model.last_name = "Doe"
        mock_user_model.is_active = True
        mock_user_model.is_superuser = False
        mock_user_model.email_verified = True
        mock_user_model.created_at = datetime.now(UTC)
        mock_user_model.updated_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user_model)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        result = await oauth_service._get_user_by_id(user_id)

        assert result is not None
        assert result.id == user_id
        assert result.email.value == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, oauth_service):
        """Test getting user by ID when not found."""
        user_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        result = await oauth_service._get_user_by_id(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_exists(self, oauth_service):
        """Test getting user by email when exists."""
        email = "test@example.com"
        tenant_id = uuid4()

        mock_user_model = MagicMock()
        mock_user_model.id = uuid4()
        mock_user_model.tenant_id = tenant_id
        mock_user_model.email = email
        mock_user_model.password_hash = "hashed"
        mock_user_model.first_name = "Jane"
        mock_user_model.last_name = "Smith"
        mock_user_model.is_active = True
        mock_user_model.is_superuser = False
        mock_user_model.email_verified = True
        mock_user_model.created_at = datetime.now(UTC)
        mock_user_model.updated_at = datetime.now(UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user_model)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        result = await oauth_service._get_user_by_email(email, tenant_id)

        assert result is not None
        assert result.email.value == email

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, oauth_service):
        """Test getting user by email when not found."""
        email = "notfound@example.com"
        tenant_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        oauth_service._session.execute = AsyncMock(return_value=mock_result)

        result = await oauth_service._get_user_by_email(email, tenant_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_user_from_oauth_with_full_name(
        self, oauth_service, sample_oauth_user_info
    ):
        """Test creating user from OAuth with complete name."""
        tenant_id = uuid4()

        # User info with full name parts
        sample_oauth_user_info.given_name = "John"
        sample_oauth_user_info.family_name = "Doe"

        oauth_service._session.add = MagicMock()
        oauth_service._session.flush = AsyncMock()

        result = await oauth_service._create_user_from_oauth(
            tenant_id=tenant_id, user_info=sample_oauth_user_info
        )

        assert result is not None
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        oauth_service._session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_from_oauth_split_full_name(
        self, oauth_service, sample_oauth_user_info
    ):
        """Test creating user from OAuth by splitting full name."""
        tenant_id = uuid4()

        # User info with only full name
        sample_oauth_user_info.given_name = None
        sample_oauth_user_info.family_name = None
        sample_oauth_user_info.name = "Jane Smith"

        oauth_service._session.add = MagicMock()
        oauth_service._session.flush = AsyncMock()

        result = await oauth_service._create_user_from_oauth(
            tenant_id=tenant_id, user_info=sample_oauth_user_info
        )

        assert result is not None
        assert result.first_name == "Jane"
        assert result.last_name == "Smith"

    @pytest.mark.asyncio
    async def test_create_user_from_oauth_email_fallback(
        self, oauth_service, sample_oauth_user_info
    ):
        """Test creating user from OAuth using email as fallback for name."""
        tenant_id = uuid4()

        # User info with no name data
        sample_oauth_user_info.given_name = None
        sample_oauth_user_info.family_name = None
        sample_oauth_user_info.name = None
        sample_oauth_user_info.email = "testuser@example.com"

        oauth_service._session.add = MagicMock()
        oauth_service._session.flush = AsyncMock()

        result = await oauth_service._create_user_from_oauth(
            tenant_id=tenant_id, user_info=sample_oauth_user_info
        )

        assert result is not None
        assert result.first_name == "testuser"

    @pytest.mark.asyncio
    async def test_find_or_create_user_not_found_error(
        self, oauth_service, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test _find_or_create_user when user not found after connection exists."""
        tenant_id = uuid4()

        mock_connection = MagicMock()
        mock_connection.user_id = uuid4()

        with (
            patch.object(
                oauth_service,
                "_check_allowed_domains",
                new_callable=AsyncMock,
            ),
            patch.object(
                oauth_service,
                "_get_oauth_connection",
                new_callable=AsyncMock,
                return_value=mock_connection,
            ),
            patch.object(
                oauth_service, "_update_oauth_connection", new_callable=AsyncMock
            ),
            patch.object(
                oauth_service,
                "_get_user_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(
                EntityNotFoundError, match="User not found for OAuth connection"
            ),
        ):
            await oauth_service._find_or_create_user(
                tenant_id=tenant_id,
                user_info=sample_oauth_user_info,
                tokens=sample_oauth_tokens,
            )

    @pytest.mark.asyncio
    async def test_link_oauth_user_not_found_error(
        self, oauth_service, sample_oauth_tokens, sample_oauth_user_info
    ):
        """Test _link_oauth_account when user not found."""
        user_id = uuid4()
        tenant_id = uuid4()

        mock_connection = MagicMock()

        with (
            patch.object(
                oauth_service,
                "_get_oauth_connection",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                oauth_service,
                "_create_oauth_connection",
                new_callable=AsyncMock,
                return_value=mock_connection,
            ),
            patch.object(
                oauth_service,
                "_get_user_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(EntityNotFoundError, match="User not found"),
        ):
            await oauth_service._link_oauth_account(
                user_id=user_id,
                tenant_id=tenant_id,
                user_info=sample_oauth_user_info,
                tokens=sample_oauth_tokens,
            )

    def test_model_to_sso_config(self, oauth_service):
        """Test SSO config model to entity conversion."""
        from app.infrastructure.database.models.oauth import SSOConfigurationModel

        mock_model = SSOConfigurationModel(
            id=uuid4(),
            tenant_id=uuid4(),
            provider="google",
            client_id="test_client_id",
            client_secret="test_secret",
            is_enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch(
            "app.application.services.oauth_service.decrypt_value",
            side_effect=lambda x: x,
        ):
            result = oauth_service._model_to_sso_config(mock_model)

        assert result is not None
        assert str(result.id) == str(mock_model.id)
        assert str(result.tenant_id) == str(mock_model.tenant_id)
        assert result.provider.value == mock_model.provider
