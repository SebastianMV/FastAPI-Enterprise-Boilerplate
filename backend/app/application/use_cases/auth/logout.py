# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Logout use case — blacklist token in Redis."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class LogoutRequest:
    """Input for logout use case."""

    user_id: UUID
    token: str | None = None
    refresh_token: str | None = None


class LogoutUseCase:
    """Blacklist the current access and refresh tokens so they cannot be reused."""

    async def execute(self, request: LogoutRequest) -> None:
        if not request.token:
            logger.warning("logout_without_token")
            return

        try:
            from app.infrastructure.auth import decode_token
            from app.infrastructure.auth.jwt_handler import hash_jti
            from app.infrastructure.cache import get_cache

            cache = get_cache()
            blacklist_data = {
                "user_id": str(request.user_id),
                "logout_at": datetime.now(UTC).isoformat(),
            }

            # Blacklist the access token
            payload = decode_token(request.token)
            token_id = payload.get("jti") or hash_jti(request.token[:32])

            exp = payload.get("exp")
            if exp:
                ttl = int(exp - datetime.now(UTC).timestamp())
                if ttl > 0:
                    await cache.set(
                        f"blacklist:token:{token_id}",
                        blacklist_data,
                        ttl=ttl,
                    )

            # Blacklist the refresh token if provided
            if request.refresh_token:
                try:
                    from app.infrastructure.auth.jwt_handler import (
                        validate_refresh_token,
                    )

                    rf_payload = validate_refresh_token(request.refresh_token)
                    rf_jti = rf_payload.get("jti")
                    rf_exp = rf_payload.get("exp")
                    if rf_jti and rf_exp:
                        rf_ttl = int(rf_exp - datetime.now(UTC).timestamp())
                        if rf_ttl > 0:
                            await cache.set(
                                f"blacklist:token:{rf_jti}",
                                blacklist_data,
                                ttl=rf_ttl,
                            )
                except Exception:
                    logger.warning(
                        "refresh_token_blacklist_failed",
                        user_id=str(request.user_id),
                    )

        except Exception as exc:
            from app.config import settings

            if settings.ENVIRONMENT in ("production", "staging"):
                logger.error(
                    "token_blacklist_failed", error=type(exc).__name__
                )
                raise
            logger.warning("token_blacklist_failed", error=type(exc).__name__)
