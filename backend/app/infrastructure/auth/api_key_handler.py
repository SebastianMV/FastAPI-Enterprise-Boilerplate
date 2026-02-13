# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
API Key authentication handler.

Provides generation, validation, and management of API keys
for machine-to-machine authentication.
"""

import hashlib as _hashlib
import hmac as _hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.api_key import APIKey
from app.domain.exceptions.base import AuthenticationError, AuthorizationError
from app.infrastructure.database.models.api_key import APIKeyModel
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


# API Key format: prefix_randomkey
# Example: krs_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
API_KEY_PREFIX = "krs"  # Short for "kairos"
API_KEY_LENGTH = 32


class APIKeyHandler:
    """
    Handler class for API Key operations.

    Provides methods for API key generation, validation, and management.
    """

    def generate_api_key(self) -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (full_key, prefix, key_hash)
        """
        return generate_api_key()

    def validate_format(self, key: str) -> bool:
        """Validate API key format."""
        return validate_api_key_format(key)

    def hash_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return _hash_api_key(key)

    def verify_key(self, plain_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash."""
        return _verify_api_key_hash(plain_key, hashed_key)

    def extract_prefix(self, key: str) -> str:
        """
        Extract prefix from an API key.

        Args:
            key: Full API key

        Returns:
            Key prefix (first 12 characters)
        """
        prefix_length = 12
        if len(key) <= prefix_length:
            return key
        return key[:prefix_length]


def _hash_api_key(key: str) -> str:
    """Hash an API key with SHA-256.

    API keys are high-entropy random tokens (>256 bits), so they do
    *not* need the slow brute-force resistance that bcrypt provides
    for human-chosen passwords.  SHA-256 is both secure and O(1).
    """
    return _hashlib.sha256(key.encode()).hexdigest()


def _verify_api_key_hash(plain_key: str, stored_hash: str) -> bool:
    """Constant-time comparison of API key hash."""
    return _hmac.compare_digest(_hash_api_key(plain_key), stored_hash)


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, prefix, key_hash)

    Note: The full_key should only be shown once to the user,
    then only the prefix is stored for identification.
    """
    # Generate random key
    random_part = secrets.token_urlsafe(API_KEY_LENGTH)
    full_key = f"{API_KEY_PREFIX}_{random_part}"

    # Extract prefix (first 8 chars of random part)
    prefix = random_part[:8]

    # Hash the full key with SHA-256 (fast, O(1), secure for high-entropy keys)
    key_hash = _hash_api_key(full_key)

    return full_key, prefix, key_hash


def validate_api_key_format(key: str) -> bool:
    """
    Validate API key format.

    Args:
        key: The API key to validate

    Returns:
        True if format is valid
    """
    if not key:
        return False

    if not key.startswith(f"{API_KEY_PREFIX}_"):
        return False

    # Check minimum length
    return len(key) >= len(API_KEY_PREFIX) + 1 + 20


async def authenticate_api_key(
    session: AsyncSession,
    key: str,
    required_scopes: list[str] | None = None,
) -> APIKey:
    """
    Authenticate an API key and return the key entity.

    Args:
        session: Database session
        key: The API key to authenticate
        required_scopes: Optional list of required scopes

    Returns:
        Authenticated APIKey entity

    Raises:
        AuthenticationError: If key is invalid
        AuthorizationError: If key lacks required scopes
    """
    if not validate_api_key_format(key):
        raise AuthenticationError(message="Invalid API key format")

    # Extract prefix for lookup
    random_part = key[len(API_KEY_PREFIX) + 1 :]
    prefix = random_part[:8]

    # Find keys with matching prefix
    stmt = select(APIKeyModel).where(
        APIKeyModel.prefix == prefix,
        APIKeyModel.is_active == True,
        APIKeyModel.is_deleted == False,
    )
    result = await session.execute(stmt)
    key_models = result.scalars().all()

    # Verify against each potential match using constant-time HMAC comparison.
    # With SHA-256 hashing, this loop is O(n) but each comparison is ~1μs
    # instead of ~200ms with bcrypt, making DoS via prefix collision infeasible.
    valid_model = None
    for model in key_models:
        if _verify_api_key_hash(key, model.key_hash):
            valid_model = model
            break

    if not valid_model:
        logger.warning("api_key_auth_failed", prefix=prefix)
        raise AuthenticationError(message="Invalid API key")

    # Check expiration
    if valid_model.expires_at and datetime.now(UTC) > valid_model.expires_at:
        logger.warning("api_key_expired", key_id=str(valid_model.id))
        raise AuthenticationError(message="API key has expired")

    # Convert to entity
    api_key = _model_to_entity(valid_model)

    # Check scopes if required
    if required_scopes:
        if not api_key.has_all_scopes(required_scopes):
            logger.warning(
                "api_key_scope_denied",
                key_id=str(api_key.id),
                required=required_scopes,
                has=api_key.scopes,
            )
            raise AuthorizationError(
                message="API key lacks required permissions",
                resource=required_scopes[0].split(":")[0]
                if required_scopes
                else "unknown",
                action=required_scopes[0].split(":")[1]
                if required_scopes and ":" in required_scopes[0]
                else "unknown",
            )

    # Update usage stats
    valid_model.last_used_at = datetime.now(UTC)
    valid_model.usage_count += 1
    await session.flush()

    logger.info("api_key_authenticated", key_id=str(api_key.id), name=api_key.name)

    return api_key


async def create_api_key(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    name: str,
    scopes: list[str],
    expires_in_days: int | None = None,
) -> tuple[str, APIKey]:
    """
    Create a new API key.

    Args:
        session: Database session
        tenant_id: Tenant ID
        user_id: User who owns the key
        name: Human-readable name
        scopes: Permission scopes
        expires_in_days: Days until expiration (None = never)

    Returns:
        Tuple of (plain_key, APIKey entity)

    Note: The plain_key is only returned once. Store it securely.
    """
    # Generate key
    full_key, prefix, key_hash = generate_api_key()

    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

    # Create model
    model = APIKeyModel(
        tenant_id=tenant_id,
        user_id=user_id,
        name=name,
        prefix=prefix,
        key_hash=key_hash,
        scopes=scopes,
        expires_at=expires_at,
        created_by=user_id,
    )

    session.add(model)
    await session.flush()
    await session.refresh(model)

    logger.info("api_key_created", key_id=str(model.id), name=name, user_id=str(user_id))

    return full_key, _model_to_entity(model)


async def revoke_api_key(
    session: AsyncSession,
    key_id: UUID,
    user_id: UUID,
    tenant_id: UUID | None = None,
) -> bool:
    """
    Revoke an API key.

    Args:
        session: Database session
        key_id: API key ID to revoke
        user_id: User performing the revocation
        tenant_id: Tenant ID for isolation

    Returns:
        True if revoked, False if not found
    """
    stmt = select(APIKeyModel).where(
        APIKeyModel.id == key_id,
        APIKeyModel.user_id == user_id,
        APIKeyModel.is_deleted.is_(False),
    )
    if tenant_id:
        stmt = stmt.where(APIKeyModel.tenant_id == tenant_id)
    result = await session.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        return False

    model.is_active = False
    model.deleted_at = datetime.now(UTC)
    model.is_deleted = True

    await session.flush()

    logger.info("api_key_revoked", key_id=str(key_id), user_id=str(user_id))

    return True


async def list_user_api_keys(
    session: AsyncSession,
    user_id: UUID,
    include_revoked: bool = False,
    tenant_id: UUID | None = None,
) -> list[APIKey]:
    """
    List API keys for a user.

    Args:
        session: Database session
        user_id: User ID
        include_revoked: Include revoked/deleted keys
        tenant_id: Tenant ID for isolation

    Returns:
        List of APIKey entities
    """
    stmt = select(APIKeyModel).where(APIKeyModel.user_id == user_id)

    if tenant_id:
        stmt = stmt.where(APIKeyModel.tenant_id == tenant_id)

    if not include_revoked:
        stmt = stmt.where(
            APIKeyModel.is_active.is_(True),
            APIKeyModel.is_deleted.is_(False),
        )

    stmt = stmt.order_by(APIKeyModel.created_at.desc())

    result = await session.execute(stmt)
    models = result.scalars().all()

    return [_model_to_entity(m) for m in models]


def _model_to_entity(model: APIKeyModel) -> APIKey:
    """Convert database model to domain entity."""
    return APIKey(
        id=model.id,
        tenant_id=model.tenant_id,
        name=model.name,
        prefix=model.prefix,
        key_hash=model.key_hash,
        user_id=model.user_id,
        scopes=model.scopes or [],
        is_active=model.is_active,
        expires_at=model.expires_at,
        last_used_at=model.last_used_at,
        last_used_ip=model.last_used_ip,
        usage_count=model.usage_count,
        created_at=model.created_at,
        updated_at=model.updated_at,
        created_by=model.created_by,
        is_deleted=model.is_deleted,
        deleted_at=model.deleted_at,
    )
