"""Additional auth endpoint tests for coverage."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestLogoutEndpoint:
    """Tests for the logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_with_valid_token(self):
        """Test logout with valid token that gets blacklisted."""
        from app.api.v1.endpoints.auth import logout

        user_id = uuid4()
        future_exp = datetime.now(UTC).timestamp() + 3600

        mock_cache = MagicMock()
        mock_cache.set = AsyncMock()

        with patch("app.infrastructure.cache.get_cache", return_value=mock_cache):
            with patch("app.infrastructure.auth.decode_token") as mock_decode:
                mock_decode.return_value = {
                    "sub": str(user_id),
                    "jti": "token-jti-123",
                    "exp": future_exp,
                }

                result = await logout(
                    authorization="Bearer valid_token",
                    current_user_id=user_id,
                )

                assert result.success is True
                assert result.message == "Successfully logged out"

    @pytest.mark.asyncio
    async def test_logout_with_exception(self):
        """Test logout handles exceptions gracefully."""
        from app.api.v1.endpoints.auth import logout

        user_id = uuid4()

        with patch("app.infrastructure.auth.decode_token") as mock_decode:
            mock_decode.side_effect = Exception("Token decode failed")

            result = await logout(
                authorization="Bearer invalid_token",
                current_user_id=user_id,
            )

            # Should succeed even with exception
            assert result.success is True
            assert result.message == "Successfully logged out"


class TestRegisterEndpoint:
    """Tests for register endpoint edge cases."""

    def test_register_request_schema_with_valid_data(self):
        """Test RegisterRequest schema accepts valid data."""
        from app.api.v1.schemas.auth import RegisterRequest

        request = RegisterRequest(
            email="valid@example.com",
            password="SecureP@ss123!",
            first_name="Test",
            last_name="User",
        )

        assert request.email == "valid@example.com"
        assert request.password == "SecureP@ss123!"
        assert request.first_name == "Test"
        assert request.last_name == "User"


class TestGetCurrentUserEndpoint:
    """Tests for get current user endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_info(self):
        """Test getting current user info."""
        from app.api.v1.endpoints.auth import get_current_user_info

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "user@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)
        mock_user.last_login = None
        mock_user.tenant_id = uuid4()

        result = await get_current_user_info(current_user=mock_user)

        assert result.id == mock_user.id
        assert result.email == "user@example.com"


class TestAuthResponseSchemas:
    """Tests for auth response schemas."""

    def test_message_response(self):
        """Test MessageResponse schema."""
        from app.api.v1.schemas.common import MessageResponse

        response = MessageResponse(
            message="Operation successful",
            success=True,
        )

        assert response.message == "Operation successful"
        assert response.success is True

    def test_message_response_failure(self):
        """Test MessageResponse with failure."""
        from app.api.v1.schemas.common import MessageResponse

        response = MessageResponse(
            message="Operation failed",
            success=False,
        )

        assert response.success is False

    def test_login_request_schema(self):
        """Test LoginRequest schema."""
        from app.api.v1.schemas.auth import LoginRequest

        request = LoginRequest(
            email="user@example.com",
            password="SecureP@ss123!",
        )

        assert request.email == "user@example.com"
        assert request.password == "SecureP@ss123!"

    def test_token_response_schema(self):
        """Test TokenResponse schema."""
        from app.api.v1.schemas.auth import TokenResponse

        response = TokenResponse(
            access_token="eyJ...",
            refresh_token="eyJ...",
            token_type="bearer",
            expires_in=3600,
        )

        assert response.access_token == "eyJ..."
        assert response.token_type == "bearer"
        assert response.expires_in == 3600

    def test_change_password_request_schema(self):
        """Test ChangePasswordRequest schema."""
        from app.api.v1.schemas.auth import ChangePasswordRequest

        request = ChangePasswordRequest(
            current_password="OldP@ss123!",
            new_password="NewP@ss456!",
        )

        assert request.current_password == "OldP@ss123!"
        assert request.new_password == "NewP@ss456!"
