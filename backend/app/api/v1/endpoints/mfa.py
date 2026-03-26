# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
MFA (Multi-Factor Authentication) API endpoints.

Provides endpoints for:
- Setting up MFA (TOTP)
- Verifying MFA codes
- Managing backup codes
- Enabling/disabling MFA
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from uuid import UUID

from app.api.deps import CurrentTenantId, get_current_user, require_permission
from app.api.v1.schemas.mfa import (
    MFABackupCodesResponse,
    MFADisableRequest,
    MFADisableResponse,
    MFAEnableResponse,
    MFASetupResponse,
    MFAStatusResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
)
from app.application.services.mfa_config_service import (
    get_mfa_config,
    save_mfa_config,
)
from app.application.services.mfa_service import MFAService, get_mfa_service
from app.domain.entities.user import User
from app.infrastructure.auth.jwt_handler import verify_password
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/mfa", tags=["MFA"])


@router.get(
    "/status",
    response_model=MFAStatusResponse,
    summary="Get MFA Status",
    description="Get the current MFA status for the authenticated user.",
)
async def get_mfa_status(
    current_user: User = Depends(get_current_user),
    _user_id: UUID = Depends(require_permission("mfa", "read")),
    tenant_id: CurrentTenantId = None,
) -> MFAStatusResponse:
    """Get MFA status for current user."""
    config = await get_mfa_config(str(current_user.id))

    if not config:
        return MFAStatusResponse(
            is_enabled=False,
            backup_codes_remaining=0,
            enabled_at=None,
            last_used_at=None,
        )

    return MFAStatusResponse(
        is_enabled=config.is_enabled,
        enabled_at=config.enabled_at,
        backup_codes_remaining=config.remaining_backup_codes,
        last_used_at=config.last_used_at,
    )


@router.post(
    "/setup",
    response_model=MFASetupResponse,
    summary="Setup MFA",
    description=(
        "Initialize MFA setup for the user. Returns a QR code and secret "
        "for configuring an authenticator app. MFA is not enabled until "
        "the user verifies a code with POST /mfa/verify."
    ),
)
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    _user_id: UUID = Depends(require_permission("mfa", "write")),
    tenant_id: CurrentTenantId = None,
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFASetupResponse:
    """Setup MFA for current user."""
    # Check if MFA is already enabled
    existing_config = await get_mfa_config(str(current_user.id))
    if existing_config and existing_config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MFA_ALREADY_ENABLED",
                "message": "MFA is already enabled. Disable it first to reconfigure.",
            },
        )

    # Generate new MFA setup
    config, qr_code, uri = mfa_service.setup_mfa(
        user_id=current_user.id,
        email=str(current_user.email),
    )

    # Save config (not enabled yet)
    await save_mfa_config(config)

    return MFASetupResponse(
        secret=config.secret,
        qr_code=str(qr_code) if not isinstance(qr_code, str) else qr_code,
        provisioning_uri=uri,
        backup_codes=config.backup_codes,
    )


@router.post(
    "/verify",
    response_model=MFAEnableResponse,
    summary="Verify MFA Setup",
    description=(
        "Verify the MFA setup by providing a code from the authenticator app. "
        "This enables MFA for the user's account."
    ),
)
async def verify_mfa_setup(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    _user_id: UUID = Depends(require_permission("mfa", "write")),
    tenant_id: CurrentTenantId = None,
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFAEnableResponse:
    """Verify MFA setup and enable it."""
    config = await get_mfa_config(str(current_user.id))

    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MFA_NOT_INITIATED",
                "message": "MFA setup not initiated. Call POST /mfa/setup first.",
            },
        )

    if config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MFA_ALREADY_ENABLED",
                "message": "MFA is already enabled.",
            },
        )

    # Verify the code
    if not mfa_service.verify_setup_code(config, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_CODE",
                "message": "Invalid verification code. Please try again.",
            },
        )

    # Save enabled config
    await save_mfa_config(config)

    return MFAEnableResponse(
        success=True,
        message="MFA has been enabled successfully.",
        enabled_at=config.enabled_at or datetime.now(UTC),
        backup_codes_remaining=config.remaining_backup_codes,
    )


@router.post(
    "/disable",
    response_model=MFADisableResponse,
    summary="Disable MFA",
    description="Disable MFA for the user's account. Requires current TOTP code.",
)
async def disable_mfa(
    request: MFADisableRequest,
    current_user: User = Depends(get_current_user),
    _user_id: UUID = Depends(require_permission("mfa", "write")),
    tenant_id: CurrentTenantId = None,
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFADisableResponse:
    """Disable MFA for current user."""
    config = await get_mfa_config(str(current_user.id))

    if not config or not config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MFA_NOT_ENABLED", "message": "MFA is not enabled."},
        )

    # Verify password first (additional security)
    if not current_user.verify_password(request.password, verify_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_PASSWORD", "message": "Invalid password."},
        )

    # Disable MFA
    if not mfa_service.disable_mfa(config, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CODE", "message": "Invalid verification code."},
        )

    # Save updated config
    await save_mfa_config(config)

    return MFADisableResponse(
        success=True,
        message="MFA has been disabled.",
    )


@router.post(
    "/backup-codes/regenerate",
    response_model=MFABackupCodesResponse,
    summary="Regenerate Backup Codes",
    description=(
        "Generate new backup codes. This invalidates all previous backup codes. "
        "Requires a valid TOTP code for verification."
    ),
)
async def regenerate_backup_codes(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    _user_id: UUID = Depends(require_permission("mfa", "write")),
    tenant_id: CurrentTenantId = None,
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFABackupCodesResponse:
    """Regenerate backup codes."""
    config = await get_mfa_config(str(current_user.id))

    if not config or not config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MFA_NOT_ENABLED", "message": "MFA is not enabled."},
        )

    # Verify code first
    is_valid, _ = mfa_service.verify_code(config, request.code, allow_backup=False)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CODE", "message": "Invalid verification code."},
        )

    # Regenerate codes
    new_codes = mfa_service.regenerate_backup_codes(config)

    # Save updated config
    await save_mfa_config(config)

    return MFABackupCodesResponse(
        backup_codes=new_codes,
        message="New backup codes generated. Previous codes are now invalid.",
    )


@router.post(
    "/validate",
    response_model=MFAVerifyResponse,
    summary="Validate MFA Code",
    description="Validate an MFA code without changing any state. Useful for testing.",
)
async def validate_mfa_code(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFAVerifyResponse:
    """Validate an MFA code."""
    config = await get_mfa_config(str(current_user.id))

    if not config or not config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MFA_NOT_ENABLED", "message": "MFA is not enabled."},
        )

    is_valid, was_backup = mfa_service.verify_code(
        config, request.code, allow_backup=False
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CODE", "message": "Invalid verification code."},
        )

    return MFAVerifyResponse(
        success=True,
        message="Code verified successfully.",
        backup_codes_remaining=None,
    )


# ===========================================
# Email OTP Endpoints
# ===========================================

from app.api.v1.schemas.mfa import (
    EmailOTPRequestResponse,
    EmailOTPVerifyRequest,
    EmailOTPVerifyResponse,
)
from app.infrastructure.auth.email_otp_handler import get_email_otp_handler
from app.infrastructure.email.service import get_email_service
from app.infrastructure.email.templates import EmailTemplateType


@router.post(
    "/email-otp/request",
    response_model=EmailOTPRequestResponse,
    summary="Request Email OTP",
    description=(
        "Request a one-time verification code sent via email. "
        "Use this as an alternative to TOTP for users without authenticator apps."
    ),
)
async def request_email_otp(
    current_user: User = Depends(get_current_user),
) -> EmailOTPRequestResponse:
    """Request an Email OTP code."""
    otp_handler = get_email_otp_handler()
    email_service = get_email_service()

    # Check cooldown
    can_request, remaining = await otp_handler.can_generate_otp(str(current_user.id))
    if not can_request:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "OTP_COOLDOWN",
                "message": "Please try again shortly.",
            },
        )

    # Generate OTP
    code = await otp_handler.generate_otp(str(current_user.id), purpose="login")
    if not code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "OTP_GENERATION_FAILED",
                "message": "Failed to generate verification code.",
            },
        )

    # Send email
    recipient_name = current_user.full_name or str(current_user.email).split("@")[0]
    await email_service.send_template_email(
        to_email=str(current_user.email),
        to_name=recipient_name,
        template_type=EmailTemplateType.EMAIL_OTP,
        context={
            "recipient_name": recipient_name,
            "otp_code": code,
            "expires_in_minutes": otp_handler.OTP_EXPIRY_MINUTES,
        },
    )

    return EmailOTPRequestResponse(
        success=True,
        message="Verification code sent to your email.",
        expires_in_minutes=otp_handler.OTP_EXPIRY_MINUTES,
    )


@router.post(
    "/email-otp/verify",
    response_model=EmailOTPVerifyResponse,
    summary="Verify Email OTP",
    description="Verify a one-time code received via email.",
)
async def verify_email_otp(
    request: EmailOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
) -> EmailOTPVerifyResponse:
    """Verify an Email OTP code."""
    otp_handler = get_email_otp_handler()

    # Get remaining attempts for better error messages
    remaining_attempts = await otp_handler.get_remaining_attempts(
        str(current_user.id),
        purpose="login",
    )

    if remaining_attempts == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_PENDING_OTP",
                "message": "No pending verification code. Please request a new one.",
            },
        )

    # Verify
    is_valid = await otp_handler.verify_otp(
        user_id=str(current_user.id),
        code=request.code,
        purpose="login",
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_CODE",
                "message": "Invalid code. Please try again.",
            },
        )

    return EmailOTPVerifyResponse(
        success=True,
        message="Email verification successful.",
    )
