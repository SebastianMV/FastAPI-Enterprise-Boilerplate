# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Authentication schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.api.v1.schemas.common import NameStr, TokenStr

# ===========================================
# Request Schemas
# ===========================================


class LoginRequest(BaseModel):
    """Login request with email and password."""

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password",
        examples=["SecureP@ss123"],
    )
    mfa_code: str | None = Field(
        None,
        min_length=6,
        max_length=8,
        description="MFA code: 6-digit TOTP or 8-char backup code",
        examples=["123456"],
    )


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["newuser@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, uppercase, lowercase, digit, special)",
        examples=["SecureP@ss123"],
    )
    first_name: NameStr = Field(
        ...,
        min_length=1,
        description="User's first name",
        examples=["John"],
    )
    last_name: NameStr = Field(
        ...,
        min_length=1,
        description="User's last name",
        examples=["Doe"],
    )


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str = Field(
        default="",
        max_length=2048,
        description="Valid refresh token (optional if sent via HttpOnly cookie)",
    )


class ChangePasswordRequest(BaseModel):
    """Request to change user's password."""

    current_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Current password for verification",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password",
    )


class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset."""

    email: EmailStr = Field(
        ...,
        description="Email address to send reset link",
        examples=["user@example.com"],
    )


class ResetPasswordRequest(BaseModel):
    """Request to reset password with token."""

    token: str = Field(
        ...,
        max_length=256,
        description="Password reset token from email",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password",
        examples=["NewSecureP@ss123"],
    )


class VerifyResetTokenRequest(BaseModel):
    """Request to verify a password reset token."""

    token: str = Field(
        ...,
        max_length=256,
        description="Password reset token to verify",
    )


class VerifyEmailTokenRequest(BaseModel):
    """Request to verify an email verification token."""

    token: str = Field(
        ...,
        max_length=256,
        description="Email verification token",
    )


# ===========================================
# Response Schemas
# ===========================================


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: TokenStr = Field(
        ...,
        description="JWT access token (short-lived)",
    )
    refresh_token: TokenStr = Field(
        ...,
        description="JWT refresh token (long-lived)",
    )
    token_type: str = Field(
        default="bearer",
        max_length=20,
        description="Token type (always 'bearer')",
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration in seconds",
    )


class UserResponse(BaseModel):
    """User information response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str = Field(max_length=320)
    first_name: str = Field(max_length=200)
    last_name: str = Field(max_length=200)
    is_active: bool
    is_superuser: bool
    email_verified: bool = False
    created_at: datetime
    last_login: datetime | None = None

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()


class AuthResponse(BaseModel):
    """Combined auth response with tokens and user info."""

    tokens: TokenResponse | None = None
    user: UserResponse


class VerificationStatusResponse(BaseModel):
    """Email verification status response."""

    email: str = Field(max_length=320)
    email_verified: bool
    verification_required: bool


# Note: MessageResponse moved to common.py - import from there instead
# from app.api.v1.schemas.common import MessageResponse
