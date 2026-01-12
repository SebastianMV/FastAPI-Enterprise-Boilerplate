# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Authentication endpoints - Connected to PostgreSQL."""

from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4
import secrets

from fastapi import APIRouter, HTTPException, Request, status, Header

from app.api.deps import CurrentUserId, CurrentUser, DbSession
from app.api.v1.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyResetTokenRequest,
)
from app.config import settings
from app.domain.entities.user import User
from app.domain.exceptions.base import (
    AuthenticationError,
    ConflictError,
    EntityNotFoundError,
)
from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password
from app.infrastructure.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_refresh_token,
    verify_password,
)
from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository

router = APIRouter()


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
) -> TokenResponse:
    """
    Authenticate user and return tokens.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns access token (15 min) and refresh token (7 days).
    
    Account will be locked after multiple failed attempts.
    """
    # Validate email format
    try:
        Email(request.email)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_EMAIL", "message": str(e)},
        )
    
    # Lookup user in database
    user_repository = SQLAlchemyUserRepository(session)
    user = await user_repository.get_by_email(request.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )
    
    # Check if account is locked
    if settings.ACCOUNT_LOCKOUT_ENABLED and user.is_locked():
        remaining = user.locked_until - datetime.now(UTC)
        minutes = max(1, int(remaining.total_seconds() / 60))
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "code": "ACCOUNT_LOCKED",
                "message": f"Account is locked. Try again in {minutes} minute(s).",
            },
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        # Record failed attempt
        if settings.ACCOUNT_LOCKOUT_ENABLED:
            is_now_locked = user.record_failed_login(
                settings.ACCOUNT_LOCKOUT_THRESHOLD,
                settings.ACCOUNT_LOCKOUT_DURATION_MINUTES,
            )
            await user_repository.update(user)
            await session.commit()
            
            if is_now_locked:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail={
                        "code": "ACCOUNT_LOCKED",
                        "message": f"Account locked after {settings.ACCOUNT_LOCKOUT_THRESHOLD} failed attempts. Try again in {settings.ACCOUNT_LOCKOUT_DURATION_MINUTES} minutes.",
                    },
                )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_INACTIVE", "message": "User account is disabled"},
        )
    
    # Check if MFA is required
    from app.api.v1.endpoints.mfa import get_mfa_config
    mfa_config = get_mfa_config(str(user.id))
    
    if mfa_config and mfa_config.is_enabled:
        # MFA is enabled, verify code
        if not request.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "MFA_REQUIRED", "message": "MFA code is required"},
            )
        
        # Verify MFA code
        from app.application.services.mfa_service import get_mfa_service
        mfa_service = get_mfa_service()
        
        is_valid, was_backup = mfa_service.verify_code(
            mfa_config, 
            request.mfa_code,
            allow_backup=True
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "INVALID_MFA_CODE", "message": "Invalid MFA code"},
            )
        
        # Save updated config (in case backup code was used)
        from app.api.v1.endpoints.mfa import save_mfa_config
        save_mfa_config(mfa_config)
    
    # Update last login and reset failed attempts
    user.last_login = datetime.now(UTC)
    user.reset_failed_attempts()
    await user_repository.update(user)
    await session.commit()
    
    # Create tokens
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        extra_claims={
            "is_superuser": user.is_superuser,
            "roles": [str(r) for r in user.roles],
        },
    )
    
    refresh_token = create_refresh_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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
    # Validate email format
    try:
        email = Email(request.email)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_EMAIL", "message": str(e)},
        )
    
    # Validate password strength
    try:
        password = Password(request.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WEAK_PASSWORD", "message": str(e)},
        )
    
    # Check if email already exists
    user_repository = SQLAlchemyUserRepository(session)
    existing_user = await user_repository.get_by_email(request.email)
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_EXISTS", "message": "Email already registered"},
        )
    
    # For new users, we need a default tenant or create one
    # In production, you'd either: assign to existing tenant, or create new tenant
    from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
    
    tenant_repo = SQLAlchemyTenantRepository(session)
    default_tenant = await tenant_repo.get_default_tenant()
    
    if not default_tenant:
        # Create default tenant if it doesn't exist
        from app.domain.entities.tenant import Tenant
        default_tenant = Tenant(
            id=uuid4(),
            name="Default",
            slug="default",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        default_tenant = await tenant_repo.create(default_tenant)
    
    # Create user in database
    now = datetime.now(UTC)
    new_user = User(
        id=uuid4(),
        tenant_id=default_tenant.id,
        email=email,
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        is_active=True,
        is_superuser=False,
        roles=[],
        created_at=now,
        updated_at=now,
        last_login=None,
        email_verified=False,  # Require verification
    )
    
    # Generate verification token if required
    verification_token = None
    if settings.EMAIL_VERIFICATION_REQUIRED:
        verification_token = new_user.generate_verification_token()
    
    try:
        created_user = await user_repository.create(new_user)
        await session.commit()
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_EXISTS", "message": str(e)},
        )
    
    # Send verification email if required
    if settings.EMAIL_VERIFICATION_REQUIRED and verification_token:
        try:
            from app.infrastructure.email import get_email_service
            
            frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
            verification_url = f"{frontend_url}/verify-email?token={verification_token}"
            
            email_service = get_email_service()
            await email_service.send_verification_email(
                to_email=str(created_user.email),
                to_name=created_user.first_name,
                verification_url=verification_url,
                expires_in_hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
            )
        except Exception:
            pass  # Don't fail registration if email fails
    
    # Create tokens
    access_token = create_access_token(
        user_id=created_user.id,
        tenant_id=created_user.tenant_id,
    )
    
    refresh_token = create_refresh_token(
        user_id=created_user.id,
        tenant_id=created_user.tenant_id,
    )
    
    return AuthResponse(
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
        user=UserResponse(
            id=created_user.id,
            email=str(created_user.email),
            first_name=created_user.first_name,
            last_name=created_user.last_name,
            is_active=created_user.is_active,
            is_superuser=created_user.is_superuser,
            email_verified=created_user.email_verified,
            created_at=created_user.created_at,
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
) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.
    
    The refresh token remains valid until its expiration.
    """
    try:
        payload = validate_refresh_token(request.refresh_token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
        )
    
    user_id = UUID(payload["sub"])
    tenant_id = UUID(payload["tenant_id"]) if payload.get("tenant_id") else None
    
    # Verify user still exists and is active
    user_repository = SQLAlchemyUserRepository(session)
    user = await user_repository.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_INACTIVE", "message": "User account is disabled"},
        )
    
    # Create new access token with current user info
    new_access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        extra_claims={
            "is_superuser": user.is_superuser,
            "roles": [str(r) for r in user.roles],
        },
    )
    
    # Rotate refresh token
    new_refresh_token = create_refresh_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Invalidate current session (client should discard tokens).",
)
async def logout(
    current_user_id: CurrentUserId,
    authorization: str = Header(...),
) -> MessageResponse:
    """
    Logout current user.
    
    Adds the refresh token to blacklist in Redis to prevent reuse.
    Client should also discard tokens locally.
    """
    from app.infrastructure.cache import get_cache
    from app.infrastructure.auth import decode_token
    from app.config import settings
    
    try:
        # Extract token from Authorization header
        token = authorization.replace("Bearer ", "")
        
        # Decode to get JTI (if present) or use token hash
        payload = decode_token(token)
        token_id = payload.get("jti", token[:32])  # Use first 32 chars if no JTI
        
        # Calculate TTL based on token expiration
        exp = payload.get("exp")
        if exp:
            from datetime import datetime, UTC
            ttl = int(exp - datetime.now(UTC).timestamp())
            if ttl > 0:
                # Add to blacklist with remaining TTL
                cache = get_cache()
                await cache.set(
                    f"blacklist:token:{token_id}",
                    {"user_id": str(current_user_id), "logout_at": datetime.now(UTC).isoformat()},
                    ttl=ttl,
                )
    except Exception as e:
        # Log error but don't fail logout
        import logging
        logging.warning(f"Failed to blacklist token: {e}")
    
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
    current_user_id: CurrentUserId,
    session: DbSession,
) -> MessageResponse:
    """
    Change current user's password.
    
    Requires current password for verification.
    """
    # Validate new password strength
    try:
        Password(request.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WEAK_PASSWORD", "message": str(e)},
        )
    
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
            detail={"code": "INVALID_PASSWORD", "message": "Current password is incorrect"},
        )
    
    # Update password
    user.password_hash = hash_password(request.new_password)
    user.updated_at = datetime.now(UTC)
    
    await user_repository.update(user)
    await session.commit()
    
    return MessageResponse(
        message="Password changed successfully",
        success=True,
    )


# ===========================================
# Password Recovery (In-Memory Token Store)
# For production, use Redis or database table
# ===========================================

# Simple in-memory store for password reset tokens
# Format: {token: {"user_id": UUID, "email": str, "expires_at": datetime}}
_password_reset_tokens: dict[str, dict] = {}

# Token configuration
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1


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
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        
        # Store token
        _password_reset_tokens[token] = {
            "user_id": user.id,
            "email": str(user.email),
            "expires_at": expires_at,
        }
        
        # Clean up expired tokens
        now = datetime.now(UTC)
        expired = [t for t, data in _password_reset_tokens.items() if data["expires_at"] < now]
        for t in expired:
            del _password_reset_tokens[t]
        
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
            # Log error but don't fail the request
            pass
    
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
    token_data = _password_reset_tokens.get(request.token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired reset token"},
        )
    
    # Check expiration
    if token_data["expires_at"] < datetime.now(UTC):
        del _password_reset_tokens[request.token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TOKEN_EXPIRED", "message": "Reset token has expired"},
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
    token_data = _password_reset_tokens.get(request.token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired reset token"},
        )
    
    # Check expiration
    if token_data["expires_at"] < datetime.now(UTC):
        del _password_reset_tokens[request.token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TOKEN_EXPIRED", "message": "Reset token has expired"},
        )
    
    # Validate new password strength
    try:
        Password(request.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WEAK_PASSWORD", "message": str(e)},
        )
    
    # Get user
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
    
    # Remove used token
    del _password_reset_tokens[request.token]
    
    # Send confirmation email
    try:
        from app.infrastructure.email import get_email_service
        
        email_service = get_email_service()
        await email_service.send_password_changed_email(
            to_email=str(user.email),
            to_name=user.first_name,
        )
    except Exception:
        pass
    
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
    user_id: CurrentUserId,
    session: DbSession,
) -> MessageResponse:
    """
    Send verification email to the current user.
    
    Can be called multiple times to resend the verification link.
    """
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
        frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
        verification_url = f"{frontend_url}/verify-email?token={token}"
        
        email_service = get_email_service()
        await email_service.send_verification_email(
            to_email=str(user.email),
            to_name=user.first_name,
            verification_url=verification_url,
            expires_in_hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
        )
    except Exception as e:
        # Log error but don't fail the request
        pass
    
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
    token: str,
    session: DbSession,
) -> MessageResponse:
    """
    Verify email address using the token from the verification email.
    """
    # Find user by verification token
    from sqlalchemy import select
    from app.infrastructure.database.models.user import UserModel
    
    stmt = select(UserModel).where(
        UserModel.email_verification_token == token,
        UserModel.is_deleted == False,
    )
    result = await session.execute(stmt)
    user_model = result.scalar_one_or_none()
    
    if not user_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired verification token"},
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
            detail={"code": "TOKEN_EXPIRED", "message": "Verification token has expired"},
        )
    
    await user_repository.update(user)
    await session.commit()
    
    return MessageResponse(
        message="Email verified successfully!",
        success=True,
    )


@router.get(
    "/verification-status",
    response_model=dict,
    summary="Get email verification status",
    description="Check if current user's email is verified.",
)
async def get_verification_status(
    user: CurrentUser,
) -> dict:
    """
    Get the email verification status for the current user.
    """
    return {
        "email": str(user.email),
        "email_verified": user.email_verified,
        "verification_required": settings.EMAIL_VERIFICATION_REQUIRED,
    }

