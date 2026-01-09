# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Authentication schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's first name",
        examples=["John"],
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's last name",
        examples=["Doe"],
    )


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    
    refresh_token: str = Field(
        ...,
        description="Valid refresh token",
    )


class ChangePasswordRequest(BaseModel):
    """Request to change user's password."""
    
    current_password: str = Field(
        ...,
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
        description="Password reset token to verify",
    )


# ===========================================
# Response Schemas
# ===========================================

class TokenResponse(BaseModel):
    """Authentication token response."""
    
    access_token: str = Field(
        ...,
        description="JWT access token (short-lived)",
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token (long-lived)",
    )
    token_type: str = Field(
        default="bearer",
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
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: datetime | None = None
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()


class AuthResponse(BaseModel):
    """Combined auth response with tokens and user info."""
    
    tokens: TokenResponse
    user: UserResponse


class MessageResponse(BaseModel):
    """Simple message response."""
    
    message: str
    success: bool = True
