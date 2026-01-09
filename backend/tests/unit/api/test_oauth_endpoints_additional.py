"""Additional OAuth endpoint tests for coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC

from fastapi import HTTPException


class TestLinkAccountEndpoint:
    """Tests for OAuth link account endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def mock_current_user(self):
        """Create mock current user."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "user@example.com"
        user.is_superuser = False
        return user

    @pytest.mark.asyncio
    async def test_link_account_invalid_provider(self, mock_session, mock_current_user):
        """Test link account with invalid provider."""
        from app.api.v1.endpoints.oauth import link_account
        
        with pytest.raises(HTTPException) as exc:
            await link_account(
                provider="invalid_provider",
                session=mock_session,
                current_user=mock_current_user,
                tenant_id=None,
                scope=None,
            )
        
        assert exc.value.status_code == 400
        assert "Unsupported OAuth provider" in exc.value.detail

    @pytest.mark.asyncio
    async def test_link_account_valid_provider(self, mock_session, mock_current_user):
        """Test link account with valid provider."""
        from app.api.v1.endpoints.oauth import link_account
        
        with patch("app.api.v1.endpoints.oauth.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.initiate_oauth = AsyncMock(return_value=(
                "https://accounts.google.com/o/oauth2/auth",
                "state123"
            ))
            
            result = await link_account(
                provider="google",
                session=mock_session,
                current_user=mock_current_user,
                tenant_id=None,
                scope="email profile",
            )
            
            assert result.authorization_url == "https://accounts.google.com/o/oauth2/auth"
            assert result.state == "state123"
            mock_service.initiate_oauth.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_account_with_tenant_id(self, mock_session, mock_current_user):
        """Test link account with tenant ID."""
        from app.api.v1.endpoints.oauth import link_account
        
        tenant_id = uuid4()
        
        with patch("app.api.v1.endpoints.oauth.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.initiate_oauth = AsyncMock(return_value=(
                "https://github.com/login/oauth/authorize",
                "state456"
            ))
            
            result = await link_account(
                provider="github",
                session=mock_session,
                current_user=mock_current_user,
                tenant_id=tenant_id,
                scope=None,
            )
            
            assert result.state == "state456"


class TestUnlinkAccountEndpoint:
    """Tests for OAuth unlink account endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_current_user(self):
        """Create mock current user."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "user@example.com"
        return user

    @pytest.mark.asyncio
    async def test_unlink_account_success(self, mock_session, mock_current_user):
        """Test successful account unlink."""
        from app.api.v1.endpoints.oauth import unlink_account
        
        connection_id = uuid4()
        
        with patch("app.api.v1.endpoints.oauth.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.unlink_oauth_account = AsyncMock(return_value=True)
            
            result = await unlink_account(
                connection_id=connection_id,
                session=mock_session,
                current_user=mock_current_user,
            )
            
            assert result is None  # 204 No Content
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unlink_account_not_found(self, mock_session, mock_current_user):
        """Test unlink account when connection not found."""
        from app.api.v1.endpoints.oauth import unlink_account
        
        connection_id = uuid4()
        
        with patch("app.api.v1.endpoints.oauth.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.unlink_oauth_account = AsyncMock(return_value=False)
            
            with pytest.raises(HTTPException) as exc:
                await unlink_account(
                    connection_id=connection_id,
                    session=mock_session,
                    current_user=mock_current_user,
                )
            
            assert exc.value.status_code == 404
            assert "OAuth connection not found" in exc.value.detail

    @pytest.mark.asyncio
    async def test_unlink_account_value_error(self, mock_session, mock_current_user):
        """Test unlink account with validation error."""
        from app.api.v1.endpoints.oauth import unlink_account
        
        connection_id = uuid4()
        
        with patch("app.api.v1.endpoints.oauth.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.unlink_oauth_account = AsyncMock(
                side_effect=ValueError("Cannot unlink last login method")
            )
            
            with pytest.raises(HTTPException) as exc:
                await unlink_account(
                    connection_id=connection_id,
                    session=mock_session,
                    current_user=mock_current_user,
                )
            
            assert exc.value.status_code == 400
            assert "Cannot unlink last login method" in exc.value.detail


class TestListSSOConfigsEndpoint:
    """Tests for SSO configs list endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_superuser(self):
        """Create mock superuser."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = True
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Create mock regular user."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = False
        return user

    @pytest.mark.asyncio
    async def test_list_sso_configs_forbidden_non_superuser(self, mock_session, mock_regular_user):
        """Test that non-superusers cannot list SSO configs."""
        from app.api.v1.endpoints.oauth import list_sso_configs
        
        with pytest.raises(HTTPException) as exc:
            await list_sso_configs(
                session=mock_session,
                current_user=mock_regular_user,
                tenant_id=uuid4(),
            )
        
        assert exc.value.status_code == 403
        assert "Only superadmins" in exc.value.detail

    @pytest.mark.asyncio
    async def test_list_sso_configs_missing_tenant_id(self, mock_session, mock_superuser):
        """Test error when tenant ID is missing."""
        from app.api.v1.endpoints.oauth import list_sso_configs
        
        with pytest.raises(HTTPException) as exc:
            await list_sso_configs(
                session=mock_session,
                current_user=mock_superuser,
                tenant_id=None,
            )
        
        assert exc.value.status_code == 400
        assert "Tenant ID is required" in exc.value.detail

    @pytest.mark.asyncio
    async def test_list_sso_configs_success(self, mock_session, mock_superuser):
        """Test successful SSO configs listing."""
        from app.api.v1.endpoints.oauth import list_sso_configs
        from app.domain.entities.oauth import OAuthProvider
        
        tenant_id = uuid4()
        
        mock_config = MagicMock()
        mock_config.id = uuid4()
        mock_config.provider = OAuthProvider.GOOGLE
        mock_config.name = "Google SSO"
        mock_config.is_enabled = True
        mock_config.auto_create_users = True
        mock_config.auto_update_users = False
        mock_config.default_role_id = None
        mock_config.allowed_domains = ["example.com"]
        mock_config.is_required = False
        mock_config.created_at = datetime.now(UTC)
        
        with patch("app.api.v1.endpoints.oauth.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_sso_config = AsyncMock(return_value=[mock_config])
            
            result = await list_sso_configs(
                session=mock_session,
                current_user=mock_superuser,
                tenant_id=tenant_id,
            )
            
            assert len(result) == 1
            assert result[0].name == "Google SSO"
            assert result[0].provider == "google"


class TestCreateSSOConfigEndpoint:
    """Tests for SSO config creation endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def mock_superuser(self):
        """Create mock superuser."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = True
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Create mock regular user."""
        user = MagicMock()
        user.id = uuid4()
        user.is_superuser = False
        return user

    @pytest.mark.asyncio
    async def test_create_sso_config_forbidden_non_superuser(self, mock_session, mock_regular_user):
        """Test that non-superusers cannot create SSO configs."""
        from app.api.v1.endpoints.oauth import create_sso_config
        
        data = MagicMock()
        data.provider = "google"
        data.name = "Google SSO"
        
        with pytest.raises(HTTPException) as exc:
            await create_sso_config(
                data=data,
                session=mock_session,
                current_user=mock_regular_user,
                tenant_id=uuid4(),
            )
        
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_sso_config_missing_tenant_id(self, mock_session, mock_superuser):
        """Test error when tenant ID is missing."""
        from app.api.v1.endpoints.oauth import create_sso_config
        
        data = MagicMock()
        data.provider = "google"
        data.name = "Google SSO"
        
        with pytest.raises(HTTPException) as exc:
            await create_sso_config(
                data=data,
                session=mock_session,
                current_user=mock_superuser,
                tenant_id=None,
            )
        
        assert exc.value.status_code == 400
        assert "Tenant ID is required" in exc.value.detail

    @pytest.mark.asyncio
    async def test_create_sso_config_invalid_provider(self, mock_session, mock_superuser):
        """Test error with invalid provider."""
        from app.api.v1.endpoints.oauth import create_sso_config
        
        data = MagicMock()
        data.provider = "invalid"
        data.name = "Invalid Provider"
        
        with pytest.raises(HTTPException) as exc:
            await create_sso_config(
                data=data,
                session=mock_session,
                current_user=mock_superuser,
                tenant_id=uuid4(),
            )
        
        assert exc.value.status_code == 400
        assert "Unsupported OAuth provider" in exc.value.detail


class TestListProvidersEndpoint:
    """Tests for OAuth providers list endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_list_providers_without_tenant(self, mock_session):
        """Test listing providers without tenant ID."""
        from app.api.v1.endpoints.oauth import list_providers
        
        with patch("app.config.settings") as mock_settings:
            mock_settings.OAUTH_GOOGLE_CLIENT_ID = "google_client_id"
            mock_settings.OAUTH_GITHUB_CLIENT_ID = ""
            mock_settings.OAUTH_MICROSOFT_CLIENT_ID = "microsoft_client_id"
            mock_settings.OAUTH_DISCORD_CLIENT_ID = ""
            
            result = await list_providers(
                session=mock_session,
                tenant_id=None,
            )
            
            assert isinstance(result, list)
            # Check that Google is available
            google_provider = next((p for p in result if p["provider"] == "google"), None)
            assert google_provider is not None
            assert google_provider["available"] is True

    @pytest.mark.asyncio
    async def test_list_providers_with_tenant(self, mock_session):
        """Test listing providers with tenant ID."""
        from app.api.v1.endpoints.oauth import list_providers
        from app.domain.entities.oauth import OAuthProvider
        
        tenant_id = uuid4()
        
        mock_sso_config = MagicMock()
        mock_sso_config.provider = OAuthProvider.GOOGLE
        mock_sso_config.name = "Custom Google SSO"
        mock_sso_config.is_enabled = True
        mock_sso_config.is_required = False
        
        with patch("app.api.v1.endpoints.oauth.OAuthService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_sso_config = AsyncMock(return_value=[mock_sso_config])
            
            with patch("app.config.settings") as mock_settings:
                mock_settings.OAUTH_GOOGLE_CLIENT_ID = ""
                mock_settings.OAUTH_GITHUB_CLIENT_ID = "github_client_id"
                mock_settings.OAUTH_MICROSOFT_CLIENT_ID = ""
                mock_settings.OAUTH_DISCORD_CLIENT_ID = ""
                
                result = await list_providers(
                    session=mock_session,
                    tenant_id=tenant_id,
                )
                
                assert isinstance(result, list)
                # Check SSO config is present
                sso_provider = next((p for p in result if p.get("is_sso")), None)
                assert sso_provider is not None
                assert sso_provider["name"] == "Custom Google SSO"

