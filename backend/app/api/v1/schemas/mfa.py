# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""MFA (Multi-Factor Authentication) schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.api.v1.schemas.common import (
    DescriptionStr,
    LargeTextStr,
    PasswordStr,
    ShortStr,
    TokenStr,
    UrlStr,
)

# ===========================================
# Request Schemas
# ===========================================


class MFASetupRequest(BaseModel):
    """Request to initiate MFA setup."""

    # No body required - user must be authenticated


class MFAVerifyRequest(BaseModel):
    """Request to verify MFA code during setup or login."""

    code: ShortStr = Field(
        ...,
        min_length=6,
        max_length=8,
        pattern=r"^[0-9A-Za-z]+$",
        description="6-digit TOTP code or 8-character backup code",
        examples=["123456", "AB12CD34"],
    )


class MFADisableRequest(BaseModel):
    """Request to disable MFA (requires password confirmation)."""

    code: ShortStr = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="Current TOTP code for verification",
        examples=["123456"],
    )
    password: PasswordStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password for additional verification",
    )


class MFALoginRequest(BaseModel):
    """Request to complete login with MFA code."""

    mfa_token: TokenStr = Field(
        ...,
        max_length=512,
        description="Temporary MFA token from initial login",
    )
    code: ShortStr = Field(
        ...,
        min_length=6,
        max_length=8,
        pattern=r"^[0-9A-Za-z]+$",
        description="6-digit TOTP code or 8-character backup code",
        examples=["123456"],
    )


# ===========================================
# Response Schemas
# ===========================================


class MFASetupResponse(BaseModel):
    """Response containing MFA setup data."""

    secret: TokenStr = Field(
        ...,
        max_length=200,
        description="TOTP secret for manual entry (base32 encoded)",
        examples=["JBSWY3DPEHPK3PXP"],
    )
    qr_code: LargeTextStr = Field(
        ...,
        max_length=50000,
        description="Base64-encoded QR code image (data URI)",
    )
    provisioning_uri: UrlStr = Field(
        ...,
        max_length=2048,
        description="otpauth:// URI for authenticator apps",
    )
    backup_codes: list[ShortStr] = Field(
        ...,
        description="One-time backup codes (save these securely)",
    )


class MFAStatusResponse(BaseModel):
    """Response containing MFA status for a user."""

    is_enabled: bool = Field(
        ...,
        description="Whether MFA is currently enabled",
    )
    enabled_at: datetime | None = Field(
        None,
        description="When MFA was enabled",
    )
    backup_codes_remaining: int = Field(
        ...,
        description="Number of unused backup codes",
    )
    last_used_at: datetime | None = Field(
        None,
        description="Last successful MFA verification",
    )


class MFAVerifyResponse(BaseModel):
    """Response after successful MFA verification."""

    success: bool = True
    message: DescriptionStr = Field(
        default="MFA verification successful", max_length=500
    )
    backup_codes_remaining: int | None = Field(
        None,
        description="Remaining backup codes (if a backup code was used)",
    )


class MFAEnableResponse(BaseModel):
    """Response after successfully enabling MFA."""

    success: bool = True
    message: DescriptionStr = Field(default="MFA has been enabled", max_length=500)
    enabled_at: datetime
    backup_codes_remaining: int


class MFADisableResponse(BaseModel):
    """Response after successfully disabling MFA."""

    success: bool = True
    message: DescriptionStr = Field(default="MFA has been disabled", max_length=500)


class MFABackupCodesResponse(BaseModel):
    """Response containing regenerated backup codes."""

    backup_codes: list[ShortStr] = Field(
        ...,
        description="New one-time backup codes (save these securely)",
    )
    message: DescriptionStr = Field(
        default="New backup codes generated. Previous codes are now invalid.",
        max_length=500,
    )


class MFARequiredResponse(BaseModel):
    """Response indicating MFA is required to complete login."""

    mfa_required: bool = True
    mfa_token: TokenStr = Field(
        ...,
        max_length=2048,
        description="Temporary token to use with MFA verification",
    )
    message: DescriptionStr = Field(
        default="MFA verification required. Please provide your authentication code.",
        max_length=500,
    )


# ===========================================
# Email OTP Schemas
# ===========================================


class EmailOTPRequestResponse(BaseModel):
    """Response after requesting an Email OTP."""

    success: bool = True
    message: DescriptionStr = Field(
        default="Verification code sent to your email.",
        max_length=500,
    )
    expires_in_minutes: int = Field(
        default=10,
        description="Minutes until the code expires",
    )


class EmailOTPVerifyRequest(BaseModel):
    """Request to verify an Email OTP code."""

    code: ShortStr = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit verification code from email",
        examples=["123456"],
    )


class EmailOTPVerifyResponse(BaseModel):
    """Response after successful Email OTP verification."""

    success: bool = True
    message: DescriptionStr = Field(
        default="Email verification successful.", max_length=500
    )
