# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
JWT Authentication handler.

Provides stateless authentication with:
- Access tokens (short-lived, 15 min default)
- Refresh tokens (long-lived, 7 days default)
- Token blacklisting via Redis
"""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

import bcrypt
import jwt
from jwt.exceptions import PyJWTError

from app.config import settings
from app.domain.exceptions.base import AuthenticationError

# Bcrypt configuration
BCRYPT_ROUNDS = 12  # Secure default
_BCRYPT_MAX_INPUT_BYTES = 72  # bcrypt truncates input beyond this limit


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_INPUT_BYTES]
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def hash_jti(jti: str) -> str:
    """
    Hash a JTI (JWT ID) using SHA-256.

    JTIs are random UUIDs — they don't need the slow bcrypt work factor.
    SHA-256 is sufficient and ~10 000× faster.

    Args:
        jti: JWT ID string (UUID)

    Returns:
        Hex-encoded SHA-256 digest
    """
    return sha256(jti.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hash to verify against

    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_INPUT_BYTES]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False


def create_access_token(
    user_id: UUID,
    tenant_id: UUID | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a short-lived access token.

    Args:
        user_id: User's unique identifier
        tenant_id: Tenant ID for multi-tenant isolation
        extra_claims: Additional claims to include

    Returns:
        Encoded JWT access token
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Generate unique token ID for session tracking
    jti = str(uuid4())

    payload = {
        "sub": str(user_id),
        "type": "access",
        "iss": settings.APP_NAME,
        "aud": settings.APP_NAME,
        "jti": jti,  # Token ID for session identification
        "iat": now,
        "exp": expire,
    }

    if tenant_id:
        payload["tenant_id"] = str(tenant_id)

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    user_id: UUID,
    tenant_id: UUID | None = None,
) -> str:
    """
    Create a long-lived refresh token.

    Args:
        user_id: User's unique identifier
        tenant_id: Tenant ID for multi-tenant isolation

    Returns:
        Encoded JWT refresh token
    """
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Generate unique token ID for session tracking
    jti = str(uuid4())

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iss": settings.APP_NAME,
        "aud": settings.APP_NAME,
        "jti": jti,  # Token ID for session identification
        "iat": now,
        "exp": expire,
    }

    if tenant_id:
        payload["tenant_id"] = str(tenant_id)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: Encoded JWT token

    Returns:
        Token payload dictionary

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.APP_NAME,
            issuer=settings.APP_NAME,
        )
        return payload

    except PyJWTError as e:
        # Do NOT leak PyJWT internal details (algorithm, key format, etc.)
        from app.infrastructure.observability.logging import get_logger as _get_logger

        _get_logger(__name__).debug("jwt_decode_error", error_type=type(e).__name__)
        raise AuthenticationError(
            message="Invalid or expired token",
            code="INVALID_TOKEN",
        ) from None


def get_token_user_id(token: str) -> UUID:
    """
    Extract user ID from token.

    Args:
        token: Encoded JWT token

    Returns:
        User's UUID

    Raises:
        AuthenticationError: If token is invalid or has no user ID
    """
    payload = decode_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError(
            message="Token missing user ID",
            code="INVALID_TOKEN",
        )

    return UUID(user_id)


def validate_access_token(token: str) -> dict[str, Any]:
    """
    Validate that token is a valid access token.

    Args:
        token: Encoded JWT token

    Returns:
        Token payload

    Raises:
        AuthenticationError: If not a valid access token
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise AuthenticationError(
            message="Invalid token type. Expected access token.",
            code="INVALID_TOKEN_TYPE",
        )

    return payload


def validate_refresh_token(token: str) -> dict[str, Any]:
    """
    Validate that token is a valid refresh token.

    Args:
        token: Encoded JWT token

    Returns:
        Token payload

    Raises:
        AuthenticationError: If not a valid refresh token
    """
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise AuthenticationError(
            message="Invalid token type. Expected refresh token.",
            code="INVALID_TOKEN_TYPE",
        )

    return payload
