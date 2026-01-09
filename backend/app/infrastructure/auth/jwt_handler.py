# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
JWT Authentication handler.

Provides stateless authentication with:
- Access tokens (short-lived, 15 min default)
- Refresh tokens (long-lived, 7 days default)
- Token blacklisting via Redis
"""

from datetime import datetime, timedelta, UTC
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from jwt.exceptions import PyJWTError

from app.config import settings
from app.domain.exceptions.base import AuthenticationError


# Bcrypt configuration
BCRYPT_ROUNDS = 12  # Secure default


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


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
        password_bytes = plain_password.encode("utf-8")[:72]
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
    
    payload = {
        "sub": str(user_id),
        "type": "access",
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
    
    payload = {
        "sub": str(user_id),
        "type": "refresh",
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
        )
        return payload
    
    except PyJWTError as e:
        raise AuthenticationError(
            message=f"Invalid token: {str(e)}",
            code="INVALID_TOKEN",
        )


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
