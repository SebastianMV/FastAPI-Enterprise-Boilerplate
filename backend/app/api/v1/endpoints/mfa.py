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

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status

if TYPE_CHECKING:
    from app.infrastructure.cache import RedisCache

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
from app.application.services.mfa_service import MFAService, get_mfa_service
from app.domain.entities.mfa import MFAConfig
from app.domain.entities.user import User
from app.infrastructure.auth.jwt_handler import verify_password

router = APIRouter(prefix="/mfa", tags=["MFA"])


async def _get_redis() -> "RedisCache":
    """Get async Redis connection for MFA storage via infrastructure cache."""
    from app.infrastructure.cache import get_cache

    return get_cache()


def _mfa_config_to_dict(config: MFAConfig) -> dict[str, Any]:
    """Convert MFAConfig to dictionary for Redis storage.

    The TOTP secret is encrypted before storage.
    """
    from app.infrastructure.auth.encryption import encrypt_value

    return {
        "user_id": str(config.user_id),
        "secret": encrypt_value(config.secret),
        "is_enabled": config.is_enabled,
        "backup_codes": config.backup_codes,
        "enabled_at": config.enabled_at.isoformat() if config.enabled_at else None,
        "last_used_at": config.last_used_at.isoformat()
        if config.last_used_at
        else None,
    }


def _dict_to_mfa_config(data: dict[str, Any]) -> MFAConfig:
    """Convert dictionary from Redis to MFAConfig.

    The TOTP secret is decrypted after retrieval.
    """
    from uuid import UUID

    from app.infrastructure.auth.encryption import decrypt_value

    config = MFAConfig(
        user_id=UUID(data["user_id"]),
        secret=decrypt_value(data["secret"]),
        is_enabled=data["is_enabled"],
        backup_codes=data["backup_codes"],
    )
    if data.get("enabled_at"):
        config.enabled_at = datetime.fromisoformat(data["enabled_at"])
    if data.get("last_used_at"):
        config.last_used_at = datetime.fromisoformat(data["last_used_at"])
    return config


async def get_mfa_config(
    user_id: str,
    session: Any | None = None,
) -> MFAConfig | None:
    """Get MFA config for user.

    Uses Redis as a cache layer with DB (``mfa_configs`` table) as the
    authoritative source of truth.  If the cache is empty the config is
    loaded from the database and repopulated into Redis.
    """
    from app.infrastructure.observability.logging import get_logger as _get_logger

    _logger = _get_logger(__name__)

    # 1. Try Redis cache first
    cache = await _get_redis()
    cache_key = f"mfa:config:{user_id}"
    data = await cache.get(cache_key)
    if data:
        if isinstance(data, str):
            data = json.loads(data)
        return _dict_to_mfa_config(data)

    # 2. Cache miss — load from database
    try:
        from uuid import UUID as _UUID

        from app.infrastructure.database.models.mfa import MFAConfigModel

        _own_session = False
        if session is None:
            from app.infrastructure.database.connection import async_session_maker

            session = async_session_maker()
            _own_session = True

        try:
            from sqlalchemy import select

            stmt = select(MFAConfigModel).where(
                MFAConfigModel.user_id == _UUID(user_id)
            )
            result = await session.execute(stmt)
            model = result.scalars().first()

            if model is None:
                return None

            from app.infrastructure.auth.encryption import decrypt_value

            config = MFAConfig(
                id=model.id,
                user_id=model.user_id,
                secret=decrypt_value(model.secret),
                is_enabled=model.is_enabled,
                backup_codes=model.backup_codes or [],
                created_at=model.created_at,
                enabled_at=model.enabled_at,
                last_used_at=model.last_used_at,
            )

            # Re-populate cache
            cache_data = _mfa_config_to_dict(config)
            await cache.set(cache_key, cache_data)

            return config
        finally:
            if _own_session:
                await session.close()
    except Exception:
        _logger.warning(
            "Failed to load MFA config from DB for user %s",
            user_id,
            exc_info=True,
        )
        return None


async def save_mfa_config(
    config: MFAConfig,
    session: Any | None = None,
) -> None:
    """Persist MFA config to the database and update the Redis cache.

    The database is the source of truth; Redis is updated afterwards.
    """
    from app.infrastructure.observability.logging import get_logger as _get_logger

    _logger = _get_logger(__name__)

    from app.infrastructure.auth.encryption import encrypt_value
    from app.infrastructure.database.models.mfa import MFAConfigModel

    _own_session = False
    if session is None:
        from app.infrastructure.database.connection import async_session_maker

        session = async_session_maker()
        _own_session = True

    try:
        from sqlalchemy import select

        stmt = select(MFAConfigModel).where(
            MFAConfigModel.user_id == config.user_id
        )
        result = await session.execute(stmt)
        model = result.scalars().first()

        encrypted_secret = encrypt_value(config.secret)

        if model is None:
            model = MFAConfigModel(
                id=config.id,
                user_id=config.user_id,
                secret=encrypted_secret,
                is_enabled=config.is_enabled,
                backup_codes=config.backup_codes,
                created_at=config.created_at,
                enabled_at=config.enabled_at,
                last_used_at=config.last_used_at,
            )
            session.add(model)
        else:
            model.secret = encrypted_secret
            model.is_enabled = config.is_enabled
            model.backup_codes = config.backup_codes
            model.enabled_at = config.enabled_at
            model.last_used_at = config.last_used_at

        await session.commit()
        _logger.info("MFA config persisted to DB for user %s", config.user_id)
    except Exception:
        await session.rollback()
        _logger.error(
            "Failed to persist MFA config to DB for user %s",
            config.user_id,
            exc_info=True,
        )
        raise
    finally:
        if _own_session:
            await session.close()

    # Update Redis cache
    try:
        cache = await _get_redis()
        cache_key = f"mfa:config:{config.user_id}"
        cache_data = _mfa_config_to_dict(config)
        await cache.set(cache_key, cache_data)
    except Exception:
        _logger.warning(
            "Failed to update MFA Redis cache for user %s (DB is authoritative)",
            config.user_id,
        )


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
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFASetupResponse:
    """Setup MFA for current user."""
    # Check if MFA is already enabled
    existing_config = await get_mfa_config(str(current_user.id))
    if existing_config and existing_config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MFA_ALREADY_ENABLED", "message": "MFA is already enabled. Disable it first to reconfigure."},
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
    mfa_service: MFAService = Depends(get_mfa_service),
) -> MFAEnableResponse:
    """Verify MFA setup and enable it."""
    config = await get_mfa_config(str(current_user.id))

    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MFA_NOT_INITIATED", "message": "MFA setup not initiated. Call POST /mfa/setup first."},
        )

    if config.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MFA_ALREADY_ENABLED", "message": "MFA is already enabled."},
        )

    # Verify the code
    if not mfa_service.verify_setup_code(config, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CODE", "message": "Invalid verification code. Please try again."},
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
            detail={"code": "OTP_GENERATION_FAILED", "message": "Failed to generate verification code."},
        )

    # Send email
    recipient_name = current_user.full_name or current_user.email.split("@")[0]
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
