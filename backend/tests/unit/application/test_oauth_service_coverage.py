# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Additional OAuth service tests for coverage improvement.
"""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.domain.entities.oauth import (
    OAuthProvider,
    OAuthState,
    OAuthUserInfo,
    OAuthConnection,
    SSOConfiguration,
)


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_oauth_state():
    """Create mock OAuth state."""
    return OAuthState(
        state="test_state",
        provider=OAuthProvider.GOOGLE,
        tenant_id=uuid4(),
        redirect_uri="http://localhost/callback",
        nonce="test_nonce",
        code_verifier="test_verifier",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        is_linking=False,
        existing_user_id=None,
    )


@pytest.fixture
def mock_user_info():
    """Create mock OAuth user info."""
    return OAuthUserInfo(
        provider=OAuthProvider.GOOGLE,
        provider_user_id="12345",
        email="test@example.com",
        name="Test User",
        given_name="Test",
        family_name="User",
        picture="http://example.com/pic.jpg",
        email_verified=True,
        locale="en",
        raw_data={},
    )


class TestOAuthServiceInitiation:
    """Test OAuth initiation."""

    @pytest.mark.asyncio
    async def test_initiate_oauth_basic(self, mock_session):
        """Test basic OAuth initiation."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        mock_provider = MagicMock()
        mock_provider.redirect_uri = "http://localhost/callback"
        mock_provider.generate_pkce = MagicMock(return_value=("verifier", "challenge"))
        mock_provider.get_authorization_url = MagicMock(return_value="https://auth.example.com")
        
        with patch.object(service, '_get_provider', new_callable=AsyncMock) as mock_get:
            with patch.object(service, '_store_oauth_state', new_callable=AsyncMock) as mock_store:
                mock_get.return_value = mock_provider
                
                auth_url, state = await service.initiate_oauth(OAuthProvider.GOOGLE)
                
                assert auth_url == "https://auth.example.com"
                assert len(state) > 0
                mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_initiate_oauth_with_linking_user(self, mock_session):
        """Test OAuth initiation for account linking."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        linking_user_id = uuid4()
        
        mock_provider = MagicMock()
        mock_provider.redirect_uri = "http://localhost/callback"
        mock_provider.generate_pkce = MagicMock(return_value=("verifier", "challenge"))
        mock_provider.get_authorization_url = MagicMock(return_value="https://auth.example.com")
        
        with patch.object(service, '_get_provider', new_callable=AsyncMock) as mock_get:
            with patch.object(service, '_store_oauth_state', new_callable=AsyncMock) as mock_store:
                mock_get.return_value = mock_provider
                
                auth_url, state = await service.initiate_oauth(
                    OAuthProvider.GITHUB,
                    linking_user_id=linking_user_id,
                )
                
                # Verify state contains linking info
                call_args = mock_store.call_args[0]
                state_data = call_args[1]
                assert state_data.is_linking is True
                assert state_data.existing_user_id == linking_user_id


class TestOAuthServiceCallback:
    """Test OAuth callback handling."""

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_state(self, mock_session):
        """Test callback with invalid state."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        with patch.object(service, '_get_oauth_state', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(ValueError, match="Invalid or expired"):
                await service.handle_callback(OAuthProvider.GOOGLE, "code", "invalid_state")

    @pytest.mark.asyncio
    async def test_handle_callback_provider_mismatch(self, mock_session, mock_oauth_state):
        """Test callback with provider mismatch."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        mock_oauth_state.provider = OAuthProvider.GOOGLE
        
        with patch.object(service, '_get_oauth_state', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_oauth_state
            
            with pytest.raises(ValueError, match="Provider mismatch"):
                await service.handle_callback(OAuthProvider.GITHUB, "code", "state")


class TestOAuthServiceConnections:
    """Test OAuth connection management."""

    @pytest.mark.asyncio
    async def test_get_user_connections_empty(self, mock_session):
        """Test getting user connections when none exist."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute.return_value = mock_result
        
        result = await service.get_user_connections(uuid4())
        
        assert result == []

    @pytest.mark.asyncio
    async def test_unlink_oauth_account_not_found(self, mock_session):
        """Test unlinking non-existent connection."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result
        
        result = await service.unlink_oauth_account(uuid4(), uuid4())
        
        assert result is False

    @pytest.mark.asyncio
    async def test_unlink_primary_without_password(self, mock_session):
        """Test unlinking primary OAuth when user has no password."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        user_id = uuid4()
        
        # Mock connection
        mock_connection = MagicMock()
        mock_connection.is_primary = True
        mock_connection.user_id = user_id
        
        # Mock user without password
        mock_user = MagicMock()
        mock_user.password_hash = None
        
        mock_result_conn = MagicMock()
        mock_result_conn.scalar_one_or_none = MagicMock(return_value=mock_connection)
        
        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none = MagicMock(return_value=mock_user)
        
        mock_session.execute.side_effect = [mock_result_conn, mock_result_user]
        
        with pytest.raises(ValueError, match="Cannot unlink primary"):
            await service.unlink_oauth_account(user_id, uuid4())

    @pytest.mark.asyncio
    async def test_unlink_oauth_success(self, mock_session):
        """Test successfully unlinking OAuth account."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        mock_connection = MagicMock()
        mock_connection.is_primary = False
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_connection)
        mock_session.execute.return_value = mock_result
        
        result = await service.unlink_oauth_account(uuid4(), uuid4())
        
        assert result is True
        assert mock_connection.is_active is False


class TestOAuthServiceSSOConfig:
    """Test SSO configuration management."""

    @pytest.mark.asyncio
    async def test_get_sso_config_empty(self, mock_session):
        """Test getting SSO config when none exists."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute.return_value = mock_result
        
        result = await service.get_sso_config(uuid4())
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_sso_config_with_provider(self, mock_session):
        """Test getting SSO config filtered by provider."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute.return_value = mock_result
        
        result = await service.get_sso_config(uuid4(), OAuthProvider.GOOGLE)
        
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sso_config(self, mock_session):
        """Test creating SSO configuration."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        tenant_id = uuid4()
        
        with patch.object(service, '_model_to_sso_config') as mock_convert:
            mock_convert.return_value = MagicMock(spec=SSOConfiguration)
            
            result = await service.create_sso_config(
                tenant_id=tenant_id,
                provider=OAuthProvider.GOOGLE,
                name="Google SSO",
                client_id="test_client_id",
                client_secret="test_secret",
                scopes=["email", "profile"],
                auto_create_users=True,
            )
            
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()


class TestOAuthServiceHelpers:
    """Test helper methods."""

    def test_get_default_oauth_config_google(self, mock_session):
        """Test getting default Google OAuth config."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        with patch('app.application.services.oauth_service.settings') as mock_settings:
            mock_settings.OAUTH_GOOGLE_CLIENT_ID = "google_id"
            mock_settings.OAUTH_GOOGLE_CLIENT_SECRET = "google_secret"
            
            client_id, client_secret = service._get_default_oauth_config(OAuthProvider.GOOGLE)
            
            assert client_id == "google_id"
            assert client_secret == "google_secret"

    def test_get_default_oauth_config_github(self, mock_session):
        """Test getting default GitHub OAuth config."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        with patch('app.application.services.oauth_service.settings') as mock_settings:
            mock_settings.OAUTH_GITHUB_CLIENT_ID = "github_id"
            mock_settings.OAUTH_GITHUB_CLIENT_SECRET = "github_secret"
            
            client_id, client_secret = service._get_default_oauth_config(OAuthProvider.GITHUB)
            
            assert client_id == "github_id"
            assert client_secret == "github_secret"

    def test_get_default_oauth_config_microsoft(self, mock_session):
        """Test getting default Microsoft OAuth config."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        with patch('app.application.services.oauth_service.settings') as mock_settings:
            mock_settings.OAUTH_MICROSOFT_CLIENT_ID = "ms_id"
            mock_settings.OAUTH_MICROSOFT_CLIENT_SECRET = "ms_secret"
            
            client_id, client_secret = service._get_default_oauth_config(OAuthProvider.MICROSOFT)
            
            assert client_id == "ms_id"
            assert client_secret == "ms_secret"

    def test_get_default_oauth_config_discord(self, mock_session):
        """Test getting default Discord OAuth config."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        with patch('app.application.services.oauth_service.settings') as mock_settings:
            mock_settings.OAUTH_DISCORD_CLIENT_ID = "discord_id"
            mock_settings.OAUTH_DISCORD_CLIENT_SECRET = "discord_secret"
            
            client_id, client_secret = service._get_default_oauth_config(OAuthProvider.DISCORD)
            
            assert client_id == "discord_id"
            assert client_secret == "discord_secret"

    def test_get_redirect_uri(self, mock_session):
        """Test building redirect URI."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        with patch('app.application.services.oauth_service.settings') as mock_settings:
            mock_settings.APP_BASE_URL = "https://myapp.com"
            
            uri = service._get_redirect_uri(OAuthProvider.GOOGLE)
            
            assert uri == "https://myapp.com/api/v1/auth/oauth/google/callback"

    def test_get_redirect_uri_default(self, mock_session):
        """Test building redirect URI with default base URL."""
        from app.application.services.oauth_service import OAuthService
        
        service = OAuthService(mock_session)
        
        with patch('app.application.services.oauth_service.settings') as mock_settings:
            # Remove APP_BASE_URL
            del mock_settings.APP_BASE_URL
            mock_settings.APP_BASE_URL = None
            
            uri = service._get_redirect_uri(OAuthProvider.GITHUB)
            
            assert "github" in uri
