# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Authentication endpoints."""

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, CurrentUserId, DbSession
from app.api.v1.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyResetTokenRequest,
)
from app.api.v1.schemas.common import MessageResponse
from app.config import settings
from app.domain.exceptions.base import (
    AuthenticationError,
    ConflictError,
    ValidationError,
)
from app.domain.value_objects.password import Password
from app.infrastructure.auth.jwt_handler import (
    hash_password,
    verify_password,
)
from app.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Time conversion constants (seconds)
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400

# Password reset token size (bytes of randomness)
PASSWORD_RESET_TOKEN_BYTES = 32


# =============================================================================
# Cookie helpers
# =============================================================================


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    """Set HttpOnly cookies for access and refresh tokens."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * SECONDS_PER_MINUTE,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * SECONDS_PER_DAY,
        path="/api/v1/auth/refresh",  # Only sent to refresh endpoint
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies on logout."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="/",
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="/api/v1/auth/refresh",
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate with email and password to receive JWT tokens.",
)
async def login(
    request: LoginRequest,
    session: DbSession,
    http_request: Request,
    response: Response = None,  # type: ignore[assignment]  # FastAPI injects Response
) -> TokenResponse:
    """
    Authenticate user and return tokens.

    - **email**: User's email address
    - **password**: User's password

    Returns access token (15 min) and refresh token (7 days).

    Account will be locked after multiple failed attempts.
    """
    from app.application.use_cases.auth.login import LoginRequest as LoginInput
    from app.application.use_cases.auth.login import LoginUseCase
    from app.infrastructure.database.repositories.session_repository import (
        SQLAlchemySessionRepository,
    )

    user_repository = SQLAlchemyUserRepository(session)
    session_repo = SQLAlchemySessionRepository(session)
    use_case = LoginUseCase(user_repository, session_repo, session)

    # Extract real client IP (nginx sets X-Forwarded-For)
    # Only trust proxy headers if connection comes from a trusted proxy network
    direct_ip = http_request.client.host if http_request.client else "Unknown"
    forwarded_for = http_request.headers.get("X-Forwarded-For")
    if forwarded_for:
        from app.middleware.rate_limit import RateLimitMiddleware
        if RateLimitMiddleware._is_trusted_proxy(direct_ip):
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            ip_address = direct_ip
    else:
        ip_address = direct_ip
    user_agent = http_request.headers.get("User-Agent", "Unknown")

    try:
        result = use_case.execute(
            LoginInput(
                email=request.email,
                password=request.password,
                mfa_code=request.mfa_code,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )
        result = await result
    except AuthenticationError as exc:
        status_map = {
            "ACCOUNT_LOCKED": status.HTTP_423_LOCKED,
            "MFA_REQUIRED": status.HTTP_403_FORBIDDEN,
            "INVALID_MFA_CODE": status.HTTP_403_FORBIDDEN,
            "USER_INACTIVE": status.HTTP_403_FORBIDDEN,
        }
        raise HTTPException(
            status_code=status_map.get(exc.code, status.HTTP_401_UNAUTHORIZED),
            detail={"code": exc.code, "message": exc.message},
        ) from None

    # Set HttpOnly cookies
    if response is not None:
        _set_auth_cookies(response, result.access_token, result.refresh_token)

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account.",
)
async def register(
    request: RegisterRequest,
    session: DbSession,
    response: Response = None,  # type: ignore[assignment]  # FastAPI injects Response
) -> AuthResponse:
    """
    Register a new user.

    Password requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    from app.application.use_cases.auth.register import RegisterRequest as RegInput
    from app.application.use_cases.auth.register import RegisterUseCase
    from app.infrastructure.database.repositories.tenant_repository import (
        SQLAlchemyTenantRepository,
    )

    user_repository = SQLAlchemyUserRepository(session)
    tenant_repo = SQLAlchemyTenantRepository(session)
    use_case = RegisterUseCase(user_repository, tenant_repo, session)

    try:
        result = await use_case.execute(
            RegInput(
                email=request.email,
                password=request.password,
                first_name=request.first_name,
                last_name=request.last_name,
            )
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    # Set HttpOnly cookies (only if tokens were issued)
    if response is not None and result.access_token and result.refresh_token:
        _set_auth_cookies(response, result.access_token, result.refresh_token)

    tokens = None
    if result.access_token:
        tokens = TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token or "",
            token_type=result.token_type,
            expires_in=result.expires_in,
        )

    return AuthResponse(
        tokens=tokens,
        user=UserResponse(
            id=result.user.id,
            email=str(result.user.email),
            first_name=result.user.first_name,
            last_name=result.user.last_name,
            is_active=result.user.is_active,
            is_superuser=result.user.is_superuser,
            email_verified=result.user.email_verified,
            created_at=result.user.created_at,
            last_login=None,
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Use refresh token to obtain a new access token.",
)
async def refresh_token(
    request: RefreshTokenRequest,
    session: DbSession,
    http_request: Request,
    response: Response = None,  # type: ignore[assignment]  # FastAPI injects Response
) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.

    The refresh token remains valid until its expiration.
    """
    from app.application.use_cases.auth.refresh import RefreshRequest as RefreshInput
    from app.application.use_cases.auth.refresh import RefreshTokenUseCase
    from app.infrastructure.database.repositories.session_repository import (
        SQLAlchemySessionRepository,
    )

    # Accept refresh token from body or from HttpOnly cookie
    token = request.refresh_token
    if not token and http_request:
        token = http_request.cookies.get("refresh_token", "")

    user_repository = SQLAlchemyUserRepository(session)
    session_repo = SQLAlchemySessionRepository(session)
    use_case = RefreshTokenUseCase(user_repository, session_repo, session)

    try:
        result = await use_case.execute(RefreshInput(refresh_token=token or ""))
    except AuthenticationError as exc:
        status_map = {
            "USER_INACTIVE": status.HTTP_403_FORBIDDEN,
        }
        raise HTTPException(
            status_code=status_map.get(exc.code, status.HTTP_401_UNAUTHORIZED),
            detail={"code": exc.code, "message": exc.message},
        ) from None

    # Set HttpOnly cookies
    if response is not None:
        _set_auth_cookies(response, result.access_token, result.refresh_token)

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Invalidate current session (client should discard tokens).",
)
async def logout(
    current_user_id: CurrentUserId,
    request: Request,
    response: Response,
    authorization: str = Header(default=""),
) -> MessageResponse:
    """
    Logout current user.

    Adds the refresh token to blacklist in Redis to prevent reuse.
    Client should also discard tokens locally.
    """
    from app.application.use_cases.auth.logout import (
        LogoutRequest as LogoutInput,
    )
    from app.application.use_cases.auth.logout import (
        LogoutUseCase,
    )

    # Extract token: try Authorization header first, then HttpOnly cookie
    token = ""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    else:
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            token = cookie_token

    # Also extract refresh token from cookie for blacklisting
    refresh_token = request.cookies.get("refresh_token") or None

    use_case = LogoutUseCase()
    await use_case.execute(
        LogoutInput(
            user_id=current_user_id, token=token or None, refresh_token=refresh_token
        )
    )

    # Clear HttpOnly cookies
    _clear_auth_cookies(response)

    return MessageResponse(
        message="Successfully logged out",
        success=True,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Get current authenticated user's information.
    """
    return UserResponse(
        id=current_user.id,
        email=str(current_user.email),
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password",
    description="Change the current user's password.",
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> MessageResponse:
    """
    Change current user's password.

    Requires current password for verification.
    """
    current_user_id = current_user.id

    # Validate new password strength
    try:
        Password(request.new_password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "WEAK_PASSWORD",
                "message": "Password does not meet security requirements. Must be 8+ characters with uppercase, lowercase, digit, and special character.",
            },
        ) from None

    # Get user from database
    user_repository = SQLAlchemyUserRepository(session)
    user = await user_repository.get_by_id(current_user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Verify current password
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_PASSWORD",
                "message": "Current password is incorrect",
            },
        )

    # Update password
    user.password_hash = hash_password(request.new_password)
    user.updated_at = datetime.now(UTC)

    await user_repository.update(user)
    await session.commit()

    # Invalidate all existing sessions (tokens remain valid until blacklisted)
    try:
        from app.infrastructure.database.repositories.session_repository import (
            SQLAlchemySessionRepository,
        )

        session_repo = SQLAlchemySessionRepository(session)
        await session_repo.revoke_all(current_user_id)
        await session.commit()
    except Exception:
        logger.error(
            "Failed to revoke sessions after password change for user %s — rolling back",
            current_user_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SESSION_REVOCATION_FAILED", "message": "Password changed but failed to invalidate existing sessions. Please contact support."},
        ) from None

    return MessageResponse(
        message="Password changed successfully",
        success=True,
    )


# ===========================================
# Password Recovery (Redis-backed Token Store)
# ===========================================

# Token configuration
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1
PASSWORD_RESET_MAX_TOKENS_PER_EMAIL = 3  # Max active tokens per email (rate limit)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Send password reset email to user.",
)
async def forgot_password(
    request: ForgotPasswordRequest,
    session: DbSession,
) -> MessageResponse:
    """
    Request a password reset email.

    For security, always returns success even if email doesn't exist.
    This prevents email enumeration attacks.
    """
    # Lookup user
    user_repository = SQLAlchemyUserRepository(session)
    user = await user_repository.get_by_email(request.email)

    if user and user.is_active:
        # Rate-limit: check how many active reset tokens this email has
        from app.infrastructure.cache import get_cache

        cache = get_cache()

        rate_key = f"password_reset:rate:{str(user.email).lower()}"
        rate_count_raw = await cache.get(rate_key)
        rate_count = int(rate_count_raw) if rate_count_raw else 0

        if rate_count >= PASSWORD_RESET_MAX_TOKENS_PER_EMAIL:
            # Silently skip — don't reveal to client
            logger.warning("Password reset rate limit hit for email hash %s", hashlib.sha256(str(user.email).lower().encode()).hexdigest()[:8])
        else:
            # Generate secure token
            token = secrets.token_urlsafe(PASSWORD_RESET_TOKEN_BYTES)
            ttl_seconds = PASSWORD_RESET_TOKEN_EXPIRE_HOURS * SECONDS_PER_HOUR

            # Store token in Redis with TTL
            token_data = {
                "user_id": str(user.id),
            }
            await cache.set(
                f"password_reset:token:{token}", token_data, ttl=ttl_seconds
            )

            # Increment rate counter (with same TTL)

            await cache.set(rate_key, rate_count + 1, ttl=ttl_seconds)

            # Send email (async, don't wait for it)
            try:
                from app.infrastructure.email import get_email_service

                email_service = get_email_service()
                reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"

                await email_service.send_password_reset_email(
                    to_email=str(user.email),
                    reset_url=reset_url,
                    to_name=user.first_name,
                    expires_in_hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS,
                )
            except Exception:
                # Log error but don't fail the request (prevents email enumeration)
                logger.warning(
                    "Failed to send password reset email",
                    exc_info=True,
                )
    else:
        # Constant-time delay to prevent timing-based email enumeration.
        # When user exists, the token generation + email sending takes ~0.3-0.6s.
        # Without this delay, the "not found" path returns instantly, leaking existence.
        import asyncio
        import random
        await asyncio.sleep(random.uniform(0.3, 0.6))

    # Always return success to prevent email enumeration
    return MessageResponse(
        message="If an account exists with this email, you will receive a password reset link.",
        success=True,
    )


@router.post(
    "/verify-reset-token",
    response_model=MessageResponse,
    summary="Verify password reset token",
    description="Check if a password reset token is valid.",
)
async def verify_reset_token(
    request: VerifyResetTokenRequest,
) -> MessageResponse:
    """
    Verify if a password reset token is still valid.
    """
    from app.infrastructure.cache import get_cache

    cache = get_cache()

    token_data = await cache.get(f"password_reset:token:{request.token}")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Invalid or expired reset token",
            },
        )

    return MessageResponse(
        message="Token is valid",
        success=True,
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
    description="Reset user password using the token from email.",
)
async def reset_password(
    request: ResetPasswordRequest,
    session: DbSession,
) -> MessageResponse:
    """
    Reset password using a valid reset token.
    """
    # --- 1. Retrieve and validate reset token from cache ---
    token_data = None
    try:
        from app.infrastructure.cache import get_cache

        cache = get_cache()
        token_data = await cache.get(f"password_reset:token:{request.token}")
    except Exception:
        logger.debug("Failed to retrieve reset token from cache", exc_info=True)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Invalid or expired reset token",
            },
        )

    # Validate new password strength
    try:
        Password(request.new_password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "WEAK_PASSWORD",
                "message": "Password does not meet security requirements. Must be 8+ characters with uppercase, lowercase, digit, and special character.",
            },
        ) from None

    # --- 3. Get user and update password ---
    user_repository = SQLAlchemyUserRepository(session)
    user = await user_repository.get_by_id(token_data["user_id"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Update password
    user.password_hash = hash_password(request.new_password)
    user.updated_at = datetime.now(UTC)

    await user_repository.update(user)
    await session.commit()

    # --- 4. Clean up tokens and rate limits ---
    try:
        await cache.delete(f"password_reset:token:{request.token}")
    except Exception:
        logger.debug("Failed to delete reset token from cache", exc_info=True)

    # Invalidate all other active reset tokens for this user's email
    try:
        email_lower = str(user.email).lower()
        # Clear the rate limit counter so user can request new tokens if needed
        await cache.delete(f"password_reset:rate:{email_lower}")
    except Exception:
        logger.debug("Failed to clear rate limit counter from cache", exc_info=True)

    # --- 5. Invalidate all existing sessions for security ---
    try:
        from app.infrastructure.database.repositories.session_repository import (
            SQLAlchemySessionRepository,
        )

        session_repo = SQLAlchemySessionRepository(session)
        await session_repo.revoke_all(user.id)
        await session.commit()
    except Exception:
        logger.error(
            "Failed to revoke sessions after password reset for user %s — rolling back",
            user.id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SESSION_REVOCATION_FAILED", "message": "Password reset but failed to invalidate existing sessions. Please contact support."},
        ) from None

    # --- 6. Send confirmation email ---
    try:
        from app.infrastructure.email import get_email_service

        email_service = get_email_service()
        await email_service.send_password_changed_email(
            to_email=str(user.email),
            to_name=user.first_name,
        )
    except Exception:
        logger.warning(
            "Failed to send password changed email",
            exc_info=True,
        )

    return MessageResponse(
        message="Password reset successfully. You can now login with your new password.",
        success=True,
    )


# ===========================================
# Email Verification Endpoints
# ===========================================


@router.post(
    "/send-verification",
    response_model=MessageResponse,
    summary="Send verification email",
    description="Send or resend email verification link.",
)
async def send_verification_email(
    current_user: CurrentUser,
    session: DbSession,
) -> MessageResponse:
    """
    Send verification email to the current user.

    Can be called multiple times to resend the verification link.
    """
    user_id = current_user.id
    user_repository = SQLAlchemyUserRepository(session)
    user = await user_repository.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    if user.email_verified:
        return MessageResponse(
            message="Email is already verified.",
            success=True,
        )

    # Generate verification token
    token = user.generate_verification_token()
    await user_repository.update(user)
    await session.commit()

    # Send verification email
    try:
        from app.infrastructure.email import get_email_service

        # Build verification URL
        frontend_url = settings.FRONTEND_URL
        verification_url = f"{frontend_url}/verify-email?token={token}"

        email_service = get_email_service()
        await email_service.send_verification_email(
            to_email=str(user.email),
            to_name=user.first_name,
            verification_url=verification_url,
            expires_in_hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
        )
    except Exception:
        # Log error but don't fail the request
        logger.warning(
            "Failed to send verification email", exc_info=True
        )

    return MessageResponse(
        message="Verification email sent. Please check your inbox.",
        success=True,
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email",
    description="Verify email address with token.",
)
async def verify_email(
    request: VerifyResetTokenRequest,
    session: DbSession,
) -> MessageResponse:
    """
    Verify email address using the token from the verification email.
    """
    token = request.token
    # Find user by verification token (SHA-256 hash lookup)
    import hashlib

    from sqlalchemy import select

    from app.infrastructure.database.models.user import UserModel

    # Hash the input token and query by hash (O(1) indexed lookup)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    stmt = select(UserModel).where(
        UserModel.email_verification_token == token_hash,
        UserModel.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    user_model = result.scalars().first()

    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Invalid or expired verification token",
            },
        )

    # Get user entity
    user_repository = SQLAlchemyUserRepository(session)
    user = await user_repository.get_by_id(user_model.id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Verify the email
    success = user.verify_email(
        token=token,
        token_expire_hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "Verification token has expired",
            },
        )

    await user_repository.update(user)
    await session.commit()

    return MessageResponse(
        message="Email verified successfully!",
        success=True,
    )


@router.get(
    "/verification-status",
    response_model=dict[str, Any],
    summary="Get email verification status",
    description="Check if current user's email is verified.",
)
async def get_verification_status(
    user: CurrentUser,
) -> dict[str, Any]:
    """
    Get the email verification status for the current user.
    """
    return {
        "email": str(user.email),
        "email_verified": user.email_verified,
        "verification_required": settings.EMAIL_VERIFICATION_REQUIRED,
    }
