# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for OAuth endpoints to improve coverage.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.endpoints.oauth import (
    OAuthConnectionResponse,
    authorize,
    authorize_redirect,
    callback,
    callback_redirect,
    list_connections,
)
from app.domain.entities.oauth import OAuthProvider


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock request."""
    return MagicMock()


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.tenant_id = uuid4()
    user.email = "test@example.com"
    return user


class TestAuthorizeEndpoint:
    """Tests for authorize endpoint."""

    @pytest.mark.asyncio
    async def test_authorize_invalid_provider(
        self, mock_session: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test authorize with invalid provider."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await authorize(
                provider="invalid_provider",
                request=mock_request,
                session=mock_session,
                tenant_id=None,
                redirect_uri=None,
                scope=None,
            )

        assert exc.value.status_code == 400
        assert "Unsupported OAuth provider" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_authorize_success(
        self, mock_session: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test successful authorization."""
        with patch("app.api.v1.endpoints.oauth.OAuthService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.initiate_oauth.return_value = (
                "https://accounts.google.com/oauth/authorize?...",
                "random-state-string",
            )
            mock_service_cls.return_value = mock_service

            result = await authorize(
                provider="google",
                request=mock_request,
                session=mock_session,
                tenant_id=uuid4(),
                redirect_uri="http://localhost:3000/callback",
                scope="email profile",
            )

            assert result.authorization_url.startswith("https://")
            assert result.state == "random-state-string"

    @pytest.mark.asyncio
    async def test_authorize_github(
        self, mock_session: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test authorize with GitHub provider."""
        with patch("app.api.v1.endpoints.oauth.OAuthService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.initiate_oauth.return_value = (
                "https://github.com/login/oauth/authorize?...",
                "github-state",
            )
            mock_service_cls.return_value = mock_service

            result = await authorize(
                provider="github",
                request=mock_request,
                session=mock_session,
                tenant_id=None,
                redirect_uri=None,
                scope=None,
            )

            assert result.state == "github-state"


class TestAuthorizeRedirectEndpoint:
    """Tests for authorize_redirect endpoint."""

    @pytest.mark.asyncio
    async def test_authorize_redirect_invalid_provider(
        self, mock_session: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test authorize redirect with invalid provider."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await authorize_redirect(
                provider="invalid",
                request=mock_request,
                session=mock_session,
                tenant_id=None,
                redirect_uri=None,
                scope=None,
            )

        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_authorize_redirect_success(
        self, mock_session: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test successful authorize redirect."""
        with patch("app.api.v1.endpoints.oauth.OAuthService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.initiate_oauth.return_value = (
                "https://accounts.google.com/oauth/authorize",
                "state",
            )
            mock_service_cls.return_value = mock_service

            result = await authorize_redirect(
                provider="google",
                request=mock_request,
                session=mock_session,
                tenant_id=uuid4(),
                redirect_uri=None,
                scope=None,
            )

            assert result.status_code == 302


class TestCallbackEndpoint:
    """Tests for callback endpoint."""

    @pytest.mark.asyncio
    async def test_callback_with_error(self, mock_session: MagicMock) -> None:
        """Test callback with error from provider."""
        from fastapi import HTTPException

        mock_response = MagicMock()

        with pytest.raises(HTTPException) as exc:
            await callback(
                provider="google",
                session=mock_session,
                response=mock_response,
                code="code",
                state="state",
                error="access_denied",
                error_description="User denied access",
            )

        assert exc.value.status_code == 400
        assert "AUTH_FAILED" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_callback_invalid_provider(self, mock_session: MagicMock) -> None:
        """Test callback with invalid provider."""
        from fastapi import HTTPException

        mock_response = MagicMock()

        with pytest.raises(HTTPException) as exc:
            await callback(
                provider="invalid",
                session=mock_session,
                response=mock_response,
                code="code",
                state="state",
                error=None,
                error_description=None,
            )

        assert exc.value.status_code == 400
        assert "Unsupported OAuth provider" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_callback_service_error(self, mock_session: MagicMock) -> None:
        """Test callback when service raises error."""
        from fastapi import HTTPException

        from app.domain.exceptions.base import DomainException

        mock_response = MagicMock()

        with patch("app.api.v1.endpoints.oauth.OAuthService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.handle_callback.side_effect = DomainException(
                message="Invalid state"
            )
            mock_service_cls.return_value = mock_service

            with pytest.raises(HTTPException) as exc:
                await callback(
                    provider="google",
                    session=mock_session,
                    response=mock_response,
                    code="invalid_code",
                    state="invalid_state",
                    error=None,
                    error_description=None,
                )

            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_callback_success(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test successful callback."""
        mock_connection = MagicMock()
        mock_connection.id = uuid4()
        mock_response = MagicMock()
        mock_user.is_superuser = False
        mock_user.roles = None

        with (
            patch("app.api.v1.endpoints.oauth.OAuthService") as mock_service_cls,
            patch(
                "app.api.v1.endpoints.oauth.create_access_token",
                return_value="access_token",
            ),
            patch(
                "app.api.v1.endpoints.oauth.create_refresh_token",
                return_value="refresh_token",
            ),
            patch(
                "app.api.v1.endpoints.oauth.decode_token",
                return_value={"jti": "test-jti"},
            ),
            patch("app.api.v1.endpoints.oauth.hash_jti", return_value="hashed-jti"),
            patch(
                "app.api.v1.endpoints.oauth.SQLAlchemySessionRepository"
            ) as mock_repo_cls,
        ):
            mock_service = AsyncMock()
            mock_service.handle_callback.return_value = (
                mock_user,
                mock_connection,
                True,
            )
            mock_service_cls.return_value = mock_service
            mock_repo_cls.return_value = AsyncMock()

            result = await callback(
                provider="google",
                session=mock_session,
                response=mock_response,
                code="valid_code",
                state="valid_state",
                error=None,
                error_description=None,
            )

            assert result.is_new_user is True
            assert result.user_id == mock_user.id


class TestCallbackRedirectEndpoint:
    """Tests for callback_redirect endpoint."""

    @pytest.mark.asyncio
    async def test_callback_redirect_with_error(self, mock_session: MagicMock) -> None:
        """Test callback redirect with error."""
        result = await callback_redirect(
            provider="google",
            session=mock_session,
            code="code",
            state="state",
            error="access_denied",
            error_description="User denied",
            frontend_url="http://localhost:3000",
        )

        assert result.status_code == 302
        assert "error=provider_error" in str(result.headers.get("location", ""))

    @pytest.mark.asyncio
    async def test_callback_redirect_invalid_provider(
        self, mock_session: MagicMock
    ) -> None:
        """Test callback redirect with invalid provider."""
        result = await callback_redirect(
            provider="invalid_provider",
            session=mock_session,
            code="code",
            state="state",
            error=None,
            error_description=None,
            frontend_url="http://localhost:3000",
        )

        assert result.status_code == 302
        assert "error=invalid_provider" in str(result.headers.get("location", ""))

    @pytest.mark.asyncio
    async def test_callback_redirect_service_error(
        self, mock_session: MagicMock
    ) -> None:
        """Test callback redirect when service fails."""
        from app.domain.exceptions.base import DomainException

        with patch("app.api.v1.endpoints.oauth.OAuthService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.handle_callback.side_effect = DomainException(
                message="Auth failed"
            )
            mock_service_cls.return_value = mock_service

            result = await callback_redirect(
                provider="google",
                session=mock_session,
                code="bad_code",
                state="bad_state",
                error=None,
                error_description=None,
                frontend_url="http://localhost:3000",
            )

            assert result.status_code == 302
            assert "error=auth_failed" in str(result.headers.get("location", ""))

    @pytest.mark.asyncio
    async def test_callback_redirect_success(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test successful callback redirect."""
        mock_connection = MagicMock()
        mock_connection.id = uuid4()
        mock_user.is_superuser = False
        mock_user.roles = None

        with (
            patch("app.api.v1.endpoints.oauth.OAuthService") as mock_service_cls,
            patch(
                "app.api.v1.endpoints.oauth.create_access_token",
                return_value="token123",
            ),
            patch(
                "app.api.v1.endpoints.oauth.create_refresh_token",
                return_value="refresh123",
            ),
            patch(
                "app.api.v1.endpoints.oauth.decode_token",
                return_value={"jti": "test-jti"},
            ),
            patch("app.api.v1.endpoints.oauth.hash_jti", return_value="hashed-jti"),
            patch(
                "app.api.v1.endpoints.oauth.SQLAlchemySessionRepository"
            ) as mock_repo_cls,
        ):
            mock_service = AsyncMock()
            mock_service.handle_callback.return_value = (
                mock_user,
                mock_connection,
                False,
            )
            mock_service_cls.return_value = mock_service
            mock_repo_cls.return_value = AsyncMock()

            result = await callback_redirect(
                provider="google",
                session=mock_session,
                code="valid_code",
                state="valid_state",
                error=None,
                error_description=None,
                frontend_url="http://localhost:3000",
            )

            assert result.status_code == 302
            location = str(result.headers.get("location", ""))
            assert "is_new_user=False" in location


class TestListConnectionsEndpoint:
    """Tests for list_connections endpoint."""

    @pytest.mark.asyncio
    async def test_list_connections_empty(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test list connections with no connections."""
        with patch("app.api.v1.endpoints.oauth.OAuthService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.get_user_connections.return_value = []
            mock_service_cls.return_value = mock_service

            result = await list_connections(
                session=mock_session,
                current_user=mock_user,
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_list_connections_with_data(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test list connections with existing connections."""
        mock_connection = MagicMock()
        mock_connection.id = uuid4()
        mock_connection.provider = OAuthProvider.GOOGLE
        mock_connection.provider_email = "test@gmail.com"
        mock_connection.provider_username = None
        mock_connection.provider_display_name = "Test User"
        mock_connection.provider_avatar_url = "https://example.com/avatar.jpg"
        mock_connection.is_primary = True
        mock_connection.last_used_at = datetime.now(UTC)
        mock_connection.created_at = datetime.now(UTC)

        with patch("app.api.v1.endpoints.oauth.OAuthService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.get_user_connections.return_value = [mock_connection]
            mock_service_cls.return_value = mock_service

            result = await list_connections(
                session=mock_session,
                current_user=mock_user,
            )

            assert len(result) == 1
            assert result[0].provider == "google"
            assert result[0].is_primary is True


class TestOAuthSchemas:
    """Tests for OAuth schemas."""

    def test_oauth_connection_response(self) -> None:
        """Test OAuthConnectionResponse schema."""
        response = OAuthConnectionResponse(
            id=uuid4(),
            provider="google",
            provider_email="test@example.com",
            provider_username=None,
            provider_display_name="Test",
            provider_avatar_url=None,
            is_primary=True,
            last_used_at=None,
            created_at=datetime.now(UTC),
        )

        assert response.provider == "google"
        assert response.is_primary is True
