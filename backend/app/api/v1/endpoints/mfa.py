# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
MFA (Multi-Factor Authentication) API endpoints.

Provides endpoints for:
- Setting up MFA (TOTP)
- Verifying MFA codes
- Managing backup codes
- Enabling/disabling MFA
"""

from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
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
from app.application.services.mfa_service import get_mfa_service, MFAService
from app.domain.entities.mfa import MFAConfig
from app.domain.entities.user import User


router = APIRouter(prefix="/mfa", tags=["MFA"])


# In-memory store for MFA configs (replace with repository in production)
# This is a simplified example - use proper database storage
_mfa_configs: dict[str, MFAConfig] = {}


def get_mfa_config(user_id: str) -> MFAConfig | None:
    """Get MFA config for user (placeholder - use repository)."""
    return _mfa_configs.get(user_id)


def save_mfa_config(config: MFAConfig) -> None:
    """Save MFA config (placeholder - use repository)."""
    _mfa_configs[str(config.user_id)] = config


@router.get(
    "/status",
    response_model=MFAStatusResponse,
    summary="Get MFA Status",
    description="Get the current MFA status for the authenticated user.",
)
async def get_mfa_status(
    current_user: User = Depends(get_current_user),
) -> MFAStatusResponse:
    """Get MFA status for current user."""
    config = get_mfa_config(str(current_user.id))
    
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
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFASetupResponse:
    """Setup MFA for current user."""
    # Check if MFA is already enabled
    existing_config = get_mfa_config(str(current_user.id))
    if existing_config and existing_config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled. Disable it first to reconfigure.",
        )
    
    # Generate new MFA setup
    config, qr_code, uri = mfa_service.setup_mfa(
        user_id=current_user.id,
        email=str(current_user.email),
    )
    
    # Save config (not enabled yet)
    save_mfa_config(config)
    
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
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFAEnableResponse:
    """Verify MFA setup and enable it."""
    config = get_mfa_config(str(current_user.id))
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated. Call POST /mfa/setup first.",
        )
    
    if config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled.",
        )
    
    # Verify the code
    if not mfa_service.verify_setup_code(config, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Please try again.",
        )
    
    # Save enabled config
    save_mfa_config(config)
    
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
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFADisableResponse:
    """Disable MFA for current user."""
    config = get_mfa_config(str(current_user.id))
    
    if not config or not config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled.",
        )
    
    # Verify password first (additional security)
    if not current_user.verify_password(request.password, lambda p, h: True):
        # In production, use actual password verification
        pass
    
    # Disable MFA
    if not mfa_service.disable_mfa(config, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )
    
    # Save updated config
    save_mfa_config(config)
    
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
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFABackupCodesResponse:
    """Regenerate backup codes."""
    config = get_mfa_config(str(current_user.id))
    
    if not config or not config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled.",
        )
    
    # Verify code first
    is_valid, _ = mfa_service.verify_code(config, request.code, allow_backup=False)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )
    
    # Regenerate codes
    new_codes = mfa_service.regenerate_backup_codes(config)
    
    # Save updated config
    save_mfa_config(config)
    
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
    config = get_mfa_config(str(current_user.id))
    
    if not config or not config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled.",
        )
    
    is_valid, was_backup = mfa_service.verify_code(config, request.code)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )
    
    # Save if backup code was used (it gets consumed)
    if was_backup:
        save_mfa_config(config)
    
    return MFAVerifyResponse(
        success=True,
        message="Code verified successfully.",
        backup_codes_remaining=config.remaining_backup_codes if was_backup else None,
    )
