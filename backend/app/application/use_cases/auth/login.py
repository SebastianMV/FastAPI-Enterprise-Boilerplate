# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Login use case — authenticates user and issues tokens."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.config import settings
from app.domain.exceptions.base import AuthenticationError
from app.domain.value_objects.email import Email
from app.domain.ports.session_repository import SessionRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort
from app.infrastructure.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_jti,
    verify_password,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class LoginRequest:
    """Input for login use case."""

    email: str
    password: str
    mfa_code: str | None = None
    user_agent: str = "Unknown"
    ip_address: str = "Unknown"


@dataclass(frozen=True)
class LoginResult:
    """Output of login use case."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    mfa_required: bool = False


class LoginUseCase:
    """Authenticate user, verify MFA if enabled, issue JWT tokens."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        session_repository: SessionRepositoryPort,
        db_session: Any,
    ) -> None:
        self._user_repo = user_repository
        self._session_repo = session_repository
        self._db_session = db_session

    async def execute(self, request: LoginRequest) -> LoginResult:
        # Validate email format
        try:
            Email(request.email)
        except ValueError:
            raise AuthenticationError(
                message="Invalid email or password",
                code="INVALID_CREDENTIALS",
            ) from None

        # Lookup user
        user = await self._user_repo.get_by_email(request.email)
        if not user:
            # Dummy bcrypt verify to prevent timing-based user enumeration
            verify_password(
                request.password,
                "$2b$12$LJ3m4ys3Lg2VEFIgWkWBSe000000000000000000000000000000",
            )
            raise AuthenticationError(
                message="Invalid email or password",
                code="INVALID_CREDENTIALS",
            )

        # Account lockout
        if settings.ACCOUNT_LOCKOUT_ENABLED and user.is_locked() and user.locked_until:
            raise AuthenticationError(
                message="Account is temporarily locked. Please try again later.",
                code="ACCOUNT_LOCKED",
            )

        # Guard: OAuth-only accounts cannot login with password
        if user.password_hash == "!oauth":
            raise AuthenticationError(
                code="INVALID_CREDENTIALS",
                message="Invalid email or password",
            )

        # Verify password
        if not verify_password(request.password, user.password_hash):
            if settings.ACCOUNT_LOCKOUT_ENABLED:
                is_now_locked = user.record_failed_login(
                    settings.ACCOUNT_LOCKOUT_THRESHOLD,
                    settings.ACCOUNT_LOCKOUT_DURATION_MINUTES,
                )
                await self._user_repo.update(user)
                await self._db_session.commit()
                if is_now_locked:
                    raise AuthenticationError(
                        message="Account is temporarily locked. Please try again later.",
                        code="ACCOUNT_LOCKED",
                    )
            raise AuthenticationError(
                message="Invalid email or password",
                code="INVALID_CREDENTIALS",
            )

        # Active check
        if not user.is_active:
            raise AuthenticationError(
                message="User account is disabled",
                code="USER_INACTIVE",
            )

        # MFA check
        await self._verify_mfa_if_enabled(user, request.mfa_code)

        # Reset failed attempts & update last login
        user.last_login = datetime.now(UTC)
        user.reset_failed_attempts()
        await self._user_repo.update(user)

        # Issue tokens
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

        # Create session record
        payload = decode_token(refresh_token)
        jti = payload.get("jti", "")

        from app.domain.entities.session import UserSession

        ua_info = UserSession.parse_user_agent(request.user_agent or "")

        user_session = UserSession(
            user_id=user.id,
            tenant_id=user.tenant_id,
            refresh_token_hash=hash_jti(jti),
            device_name=(request.user_agent[:100] if request.user_agent else "Unknown"),
            device_type=ua_info["device_type"],
            browser=ua_info["browser"],
            os=ua_info["os"],
            ip_address=request.ip_address,
            location="",
            last_activity=datetime.now(UTC),
        )
        await self._session_repo.create(user_session)
        await self._db_session.commit()

        return LoginResult(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ------------------------------------------------------------------
    async def _verify_mfa_if_enabled(self, user, mfa_code: str | None) -> None:
        from app.application.services.mfa_config_service import (
            get_mfa_config,
            save_mfa_config,
        )

        mfa_config = await get_mfa_config(str(user.id))

        if not mfa_config:
            # No MFA configured for this user — DB is authoritative
            return

        if not mfa_config.is_enabled:
            return

        if not mfa_code:
            raise AuthenticationError(
                message="MFA code is required",
                code="MFA_REQUIRED",
            )

        from app.application.services.mfa_service import get_mfa_service

        mfa_service = get_mfa_service()
        is_valid, _was_backup = mfa_service.verify_code(
            mfa_config, mfa_code, allow_backup=True
        )
        if not is_valid:
            raise AuthenticationError(
                message="Invalid MFA code",
                code="INVALID_MFA_CODE",
            )
        await save_mfa_config(mfa_config)
