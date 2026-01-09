# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for auth endpoint schemas."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from app.api.v1.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyResetTokenRequest,
    TokenResponse,
    UserResponse,
    AuthResponse,
    MessageResponse,
)


class TestLoginRequest:
    """Tests for LoginRequest schema."""

    def test_login_request_valid(self):
        """Test valid login request."""
        request = LoginRequest(
            email="user@example.com",
            password="SecureP@ss123"
        )
        assert request.email == "user@example.com"
        assert request.password == "SecureP@ss123"

    def test_login_request_invalid_email(self):
        """Test login with invalid email."""
        with pytest.raises(ValidationError):
            LoginRequest(email="not-an-email", password="password123")

    def test_login_request_password_min_length(self):
        """Test password minimum length."""
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com", password="short")

    def test_login_request_password_max_length(self):
        """Test password maximum length."""
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com", password="x" * 129)

    def test_login_request_email_required(self):
        """Test email is required."""
        with pytest.raises(ValidationError):
            LoginRequest(password="password123")


class TestRegisterRequest:
    """Tests for RegisterRequest schema."""

    def test_register_request_valid(self):
        """Test valid register request."""
        request = RegisterRequest(
            email="newuser@example.com",
            password="SecureP@ss123",
            first_name="John",
            last_name="Doe"
        )
        assert request.email == "newuser@example.com"
        assert request.first_name == "John"
        assert request.last_name == "Doe"

    def test_register_request_first_name_min_length(self):
        """Test first_name minimum length."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="password123",
                first_name="",
                last_name="Doe"
            )

    def test_register_request_last_name_max_length(self):
        """Test last_name maximum length."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="password123",
                first_name="John",
                last_name="x" * 101
            )


class TestRefreshTokenRequest:
    """Tests for RefreshTokenRequest schema."""

    def test_refresh_token_valid(self):
        """Test valid refresh token request."""
        request = RefreshTokenRequest(refresh_token="some.valid.token")
        assert request.refresh_token == "some.valid.token"

    def test_refresh_token_required(self):
        """Test refresh_token is required."""
        with pytest.raises(ValidationError):
            RefreshTokenRequest()


class TestChangePasswordRequest:
    """Tests for ChangePasswordRequest schema."""

    def test_change_password_valid(self):
        """Test valid change password request."""
        request = ChangePasswordRequest(
            current_password="oldpassword",
            new_password="newpassword123"
        )
        assert request.current_password == "oldpassword"
        assert request.new_password == "newpassword123"

    def test_change_password_new_password_min_length(self):
        """Test new_password minimum length."""
        with pytest.raises(ValidationError):
            ChangePasswordRequest(
                current_password="oldpassword",
                new_password="short"
            )


class TestForgotPasswordRequest:
    """Tests for ForgotPasswordRequest schema."""

    def test_forgot_password_valid(self):
        """Test valid forgot password request."""
        request = ForgotPasswordRequest(email="user@example.com")
        assert request.email == "user@example.com"

    def test_forgot_password_invalid_email(self):
        """Test invalid email."""
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="not-valid")


class TestResetPasswordRequest:
    """Tests for ResetPasswordRequest schema."""

    def test_reset_password_valid(self):
        """Test valid reset password request."""
        request = ResetPasswordRequest(
            token="reset-token-123",
            new_password="newpassword123"
        )
        assert request.token == "reset-token-123"
        assert request.new_password == "newpassword123"

    def test_reset_password_new_password_min_length(self):
        """Test new_password minimum length."""
        with pytest.raises(ValidationError):
            ResetPasswordRequest(token="token", new_password="short")


class TestVerifyResetTokenRequest:
    """Tests for VerifyResetTokenRequest schema."""

    def test_verify_reset_token_valid(self):
        """Test valid verify token request."""
        request = VerifyResetTokenRequest(token="verify-token-abc")
        assert request.token == "verify-token-abc"

    def test_verify_reset_token_required(self):
        """Test token is required."""
        with pytest.raises(ValidationError):
            VerifyResetTokenRequest()


class TestTokenResponse:
    """Tests for TokenResponse schema."""

    def test_token_response_valid(self):
        """Test valid token response."""
        response = TokenResponse(
            access_token="access.jwt.token",
            refresh_token="refresh.jwt.token",
            expires_in=3600
        )
        assert response.access_token == "access.jwt.token"
        assert response.token_type == "bearer"
        assert response.expires_in == 3600

    def test_token_response_custom_token_type(self):
        """Test custom token type."""
        response = TokenResponse(
            access_token="token",
            refresh_token="refresh",
            token_type="custom",
            expires_in=7200
        )
        assert response.token_type == "custom"


class TestUserResponse:
    """Tests for UserResponse schema."""

    def test_user_response_valid(self):
        """Test valid user response."""
        now = datetime.now(timezone.utc)
        response = UserResponse(
            id=uuid4(),
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            last_login=None
        )
        assert response.email == "user@example.com"
        assert response.full_name == "John Doe"
        assert response.is_active is True

    def test_user_response_superuser(self):
        """Test superuser response."""
        now = datetime.now(timezone.utc)
        response = UserResponse(
            id=uuid4(),
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_superuser=True,
            created_at=now,
            last_login=now
        )
        assert response.is_superuser is True
        assert response.last_login == now


class TestAuthResponse:
    """Tests for AuthResponse schema."""

    def test_auth_response_valid(self):
        """Test valid auth response."""
        now = datetime.now(timezone.utc)
        tokens = TokenResponse(
            access_token="access",
            refresh_token="refresh",
            expires_in=3600
        )
        user = UserResponse(
            id=uuid4(),
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now
        )
        response = AuthResponse(tokens=tokens, user=user)
        assert response.tokens.access_token == "access"
        assert response.user.email == "user@example.com"


class TestMessageResponse:
    """Tests for MessageResponse schema."""

    def test_message_response_success(self):
        """Test success message response."""
        response = MessageResponse(message="Operation completed")
        assert response.message == "Operation completed"
        assert response.success is True

    def test_message_response_failure(self):
        """Test failure message response."""
        response = MessageResponse(message="Operation failed", success=False)
        assert response.success is False
