# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
MFA Config persistence service.

Manages MFA configuration storage in Redis (cache) and PostgreSQL (source of
truth).  Extracted from the MFA endpoint module so that the login use-case
can access MFA configs **without** importing from the API layer, preserving
hexagonal architecture boundaries.
"""

from __future__ import annotations

import json
from datetime import UTC
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from app.domain.entities.mfa import MFAConfig
from app.infrastructure.observability.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
#  Redis helpers
# ---------------------------------------------------------------------------


async def _get_redis() -> Any:
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
    from datetime import datetime
    from uuid import UUID

    from app.infrastructure.auth.encryption import decrypt_value

    config = MFAConfig(
        user_id=UUID(data["user_id"]),
        secret=decrypt_value(data["secret"]),
        is_enabled=data["is_enabled"],
        backup_codes=data["backup_codes"],
    )
    if data.get("enabled_at"):
        dt = datetime.fromisoformat(data["enabled_at"])
        config.enabled_at = dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    if data.get("last_used_at"):
        dt = datetime.fromisoformat(data["last_used_at"])
        config.last_used_at = dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return config


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


async def get_mfa_config(
    user_id: str,
    session: AsyncSession | None = None,
) -> MFAConfig | None:
    """Get MFA config for user.

    Uses Redis as a cache layer with DB (``mfa_configs`` table) as the
    authoritative source of truth.  If the cache is empty the config is
    loaded from the database and repopulated into Redis.
    """
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
                id=cast("UUID", model.id),
                user_id=cast("UUID", model.user_id),
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
        logger.error(
            "mfa_config_load_failed",
            user_id=user_id,
            exc_info=True,
        )
        # Re-raise: login must FAIL if MFA status cannot be verified.
        # Returning None here would silently skip MFA — a security bypass.
        from app.domain.exceptions.base import ServiceUnavailableError

        raise ServiceUnavailableError(
            service="mfa_config",
            message="Unable to verify MFA status",
        ) from None


async def save_mfa_config(
    config: MFAConfig,
    session: AsyncSession | None = None,
) -> None:
    """Persist MFA config to the database and update the Redis cache.

    The database is the source of truth; Redis is updated afterwards.
    """
    from app.infrastructure.auth.encryption import encrypt_value
    from app.infrastructure.database.models.mfa import MFAConfigModel

    _own_session = False
    if session is None:
        from app.infrastructure.database.connection import async_session_maker

        session = async_session_maker()
        _own_session = True

    try:
        from sqlalchemy import select

        stmt = select(MFAConfigModel).where(MFAConfigModel.user_id == config.user_id)
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
        logger.info("mfa_config_persisted", user_id=str(config.user_id))
    except Exception:
        await session.rollback()
        logger.error(
            "mfa_config_persist_failed",
            user_id=str(config.user_id),
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
        logger.warning(
            "mfa_cache_update_failed",
            user_id=str(config.user_id),
        )
