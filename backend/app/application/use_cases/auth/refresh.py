# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Refresh token use case — rotate tokens."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.config import settings
from app.domain.exceptions.base import AuthenticationError
from app.domain.ports.session_repository import SessionRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort
from app.infrastructure.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_jti,
    validate_refresh_token,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RefreshRequest:
    """Input for refresh use case."""

    refresh_token: str


@dataclass(frozen=True)
class RefreshResult:
    """Output of refresh use case."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0


class RefreshTokenUseCase:
    """Validate refresh token and issue a new token pair."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        session_repository: SessionRepositoryPort,
        db_session: Any,
    ) -> None:
        self._user_repo = user_repository
        self._session_repo = session_repository
        self._db_session = db_session

    async def execute(self, request: RefreshRequest) -> RefreshResult:
        if not request.refresh_token:
            raise AuthenticationError(
                message="Refresh token is required",
                code="MISSING_TOKEN",
            )

        # Validate
        try:
            payload = validate_refresh_token(request.refresh_token)
        except AuthenticationError:
            raise

        user_id = UUID(payload["sub"])

        # B-04: Check if the refresh token's JTI is blacklisted (e.g., after logout)
        old_jti = payload.get("jti", "")
        if old_jti:
            try:
                from app.infrastructure.cache import get_cache

                cache = get_cache()
                is_blacklisted = await cache.get(f"blacklist:token:{old_jti}")
                if is_blacklisted:
                    raise AuthenticationError(
                        message="Token has been revoked",
                        code="TOKEN_REVOKED",
                    )
            except AuthenticationError:
                raise
            except Exception:
                # Fail-closed in production/staging
                if settings.ENVIRONMENT in ("production", "staging"):
                    logger.warning(
                        "redis_unavailable_fail_closed",
                        exc_info=True,
                    )
                    raise AuthenticationError(
                        message="Unable to validate token",
                        code="TOKEN_VALIDATION_FAILED",
                    ) from None

        user = await self._user_repo.get_by_id(user_id)

        if not user:
            raise AuthenticationError(message="User not found", code="USER_NOT_FOUND")
        if not user.is_active:
            raise AuthenticationError(
                message="User account is disabled", code="USER_INACTIVE"
            )

        # Issue new tokens
        new_access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            extra_claims={
                "is_superuser": user.is_superuser,
                "roles": [str(r) for r in user.roles],
            },
        )
        new_refresh_token = create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
        )

        # Rotate session
        if old_jti:
            old_session = await self._session_repo.get_by_token_hash(hash_jti(old_jti))
            if old_session:
                await self._session_repo.revoke(old_session.id)

            # Blacklist old refresh token JTI so it cannot be reused
            try:
                from app.infrastructure.cache import get_cache

                cache = get_cache()
                # Blacklist for the remaining lifetime of the old token
                await cache.set(
                    f"blacklist:token:{old_jti}",
                    "rotated",
                    ttl=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                )
            except Exception:
                logger.warning(
                    "old_refresh_token_blacklist_failed",
                    exc_info=True,
                )

            new_payload = decode_token(new_refresh_token)
            new_jti = new_payload.get("jti", "")

            if new_jti:
                from app.domain.entities.session import UserSession

                user_session = UserSession(
                    user_id=user.id,
                    tenant_id=user.tenant_id,
                    refresh_token_hash=hash_jti(new_jti),
                    device_name=(old_session.device_name if old_session else "Unknown"),
                    device_type=(old_session.device_type if old_session else "desktop"),
                    browser=old_session.browser if old_session else "",
                    os=old_session.os if old_session else "",
                    ip_address=old_session.ip_address if old_session else "",
                    location=old_session.location if old_session else "",
                    last_activity=datetime.now(UTC),
                )
                await self._session_repo.create(user_session)

        await self._db_session.commit()

        return RefreshResult(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
