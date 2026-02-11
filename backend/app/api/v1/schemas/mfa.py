# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""MFA (Multi-Factor Authentication) schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field

# ===========================================
# Request Schemas
# ===========================================


class MFASetupRequest(BaseModel):
    """Request to initiate MFA setup."""

    # No body required - user must be authenticated


class MFAVerifyRequest(BaseModel):
    """Request to verify MFA code during setup or login."""

    code: str = Field(
        ...,
        min_length=6,
        max_length=8,
        pattern=r"^[0-9A-Za-z]+$",
        description="6-digit TOTP code or 8-character backup code",
        examples=["123456", "AB12CD34"],
    )


class MFADisableRequest(BaseModel):
    """Request to disable MFA (requires password confirmation)."""

    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="Current TOTP code for verification",
        examples=["123456"],
    )
    password: str = Field(
        ...,
        max_length=128,
        description="User's password for additional verification",
    )


class MFALoginRequest(BaseModel):
    """Request to complete login with MFA code."""

    mfa_token: str = Field(
        ...,
        max_length=512,
        description="Temporary MFA token from initial login",
    )
    code: str = Field(
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

    secret: str = Field(
        ...,
        description="TOTP secret for manual entry (base32 encoded)",
        examples=["JBSWY3DPEHPK3PXP"],
    )
    qr_code: str = Field(
        ...,
        description="Base64-encoded QR code image (data URI)",
    )
    provisioning_uri: str = Field(
        ...,
        description="otpauth:// URI for authenticator apps",
    )
    backup_codes: list[str] = Field(
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
    message: str = "MFA verification successful"
    backup_codes_remaining: int | None = Field(
        None,
        description="Remaining backup codes (if a backup code was used)",
    )


class MFAEnableResponse(BaseModel):
    """Response after successfully enabling MFA."""

    success: bool = True
    message: str = "MFA has been enabled"
    enabled_at: datetime
    backup_codes_remaining: int


class MFADisableResponse(BaseModel):
    """Response after successfully disabling MFA."""

    success: bool = True
    message: str = "MFA has been disabled"


class MFABackupCodesResponse(BaseModel):
    """Response containing regenerated backup codes."""

    backup_codes: list[str] = Field(
        ...,
        description="New one-time backup codes (save these securely)",
    )
    message: str = "New backup codes generated. Previous codes are now invalid."


class MFARequiredResponse(BaseModel):
    """Response indicating MFA is required to complete login."""

    mfa_required: bool = True
    mfa_token: str = Field(
        ...,
        description="Temporary token to use with MFA verification",
    )
    message: str = "MFA verification required. Please provide your authentication code."


# ===========================================
# Email OTP Schemas
# ===========================================


class EmailOTPRequestResponse(BaseModel):
    """Response after requesting an Email OTP."""

    success: bool = True
    message: str = "Verification code sent to your email."
    expires_in_minutes: int = Field(
        default=10,
        description="Minutes until the code expires",
    )


class EmailOTPVerifyRequest(BaseModel):
    """Request to verify an Email OTP code."""

    code: str = Field(
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
    message: str = "Email verification successful."
