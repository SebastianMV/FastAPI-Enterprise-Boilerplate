# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Comprehensive tests for JWT Handler."""

import pytest
import jwt
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from unittest.mock import patch

from app.infrastructure.auth.jwt_handler import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    BCRYPT_ROUNDS,
)
from app.domain.exceptions.base import AuthenticationError


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Should hash password using bcrypt."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_hash_password_produces_different_hashes(self):
        """Should produce different hashes for same password (salt)."""
        password = "SamePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2

    def test_hash_long_password(self):
        """Should truncate passwords longer than 72 bytes."""
        # Bcrypt has a 72-byte limit
        long_password = "a" * 100
        hashed = hash_password(long_password)
        
        assert hashed is not None

    def test_hash_unicode_password(self):
        """Should handle unicode characters."""
        password = "Contraseña123!ñ中文"
        hashed = hash_password(password)
        
        assert hashed is not None

    def test_verify_password_correct(self):
        """Should verify correct password."""
        password = "MyPassword123!"
        hashed = hash_password(password)
        
        result = verify_password(password, hashed)
        
        assert result is True

    def test_verify_password_incorrect(self):
        """Should reject incorrect password."""
        password = "CorrectPassword"
        wrong_password = "WrongPassword"
        hashed = hash_password(password)
        
        result = verify_password(wrong_password, hashed)
        
        assert result is False

    def test_verify_password_empty_string(self):
        """Should reject empty password."""
        hashed = hash_password("password")
        
        result = verify_password("", hashed)
        
        assert result is False

    def test_verify_password_invalid_hash(self):
        """Should handle invalid hash gracefully."""
        result = verify_password("password", "invalid_hash")
        
        assert result is False

    def test_verify_password_none_hash(self):
        """Should handle None hash gracefully."""
        # This should not raise an exception
        result = verify_password("password", "")
        
        assert result is False


class TestCreateAccessToken:
    """Tests for access token creation."""

    def test_create_access_token_basic(self):
        """Should create access token with user_id."""
        user_id = uuid4()
        
        token = create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode to verify structure
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_create_access_token_with_tenant(self):
        """Should include tenant_id in token."""
        user_id = uuid4()
        tenant_id = uuid4()
        
        token = create_access_token(user_id, tenant_id=tenant_id)
        
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["tenant_id"] == str(tenant_id)

    def test_create_access_token_with_extra_claims(self):
        """Should include extra claims."""
        user_id = uuid4()
        extra_claims = {"role": "admin", "permissions": ["read", "write"]}
        
        token = create_access_token(user_id, extra_claims=extra_claims)
        
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]

    def test_access_token_expiration(self):
        """Should set correct expiration time."""
        user_id = uuid4()
        
        token = create_access_token(user_id)
        
        payload = jwt.decode(token, options={"verify_signature": False})
        exp_time = datetime.fromtimestamp(payload["exp"], UTC)
        iat_time = datetime.fromtimestamp(payload["iat"], UTC)
        
        # Should expire in ~15 minutes (default ACCESS_TOKEN_EXPIRE_MINUTES)
        duration = exp_time - iat_time
        assert duration.total_seconds() > 0
        assert duration.total_seconds() <= 3600  # Less than 1 hour

    def test_access_token_has_jti(self):
        """Should include unique token ID (jti)."""
        user_id = uuid4()
        
        token1 = create_access_token(user_id)
        token2 = create_access_token(user_id)
        
        payload1 = jwt.decode(token1, options={"verify_signature": False})
        payload2 = jwt.decode(token2, options={"verify_signature": False})
        
        assert payload1["jti"] != payload2["jti"]


class TestCreateRefreshToken:
    """Tests for refresh token creation."""

    def test_create_refresh_token_basic(self):
        """Should create refresh token."""
        user_id = uuid4()
        
        token = create_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
        assert "jti" in payload

    def test_create_refresh_token_with_tenant(self):
        """Should include tenant in refresh token."""
        user_id = uuid4()
        tenant_id = uuid4()
        
        token = create_refresh_token(user_id, tenant_id=tenant_id)
        
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["tenant_id"] == str(tenant_id)

    def test_refresh_token_longer_expiration(self):
        """Should have longer expiration than access token."""
        user_id = uuid4()
        
        token = create_refresh_token(user_id)
        
        payload = jwt.decode(token, options={"verify_signature": False})
        exp_time = datetime.fromtimestamp(payload["exp"], UTC)
        iat_time = datetime.fromtimestamp(payload["iat"], UTC)
        
        # Should expire in ~7 days (default REFRESH_TOKEN_EXPIRE_DAYS)
        duration = exp_time - iat_time
        assert duration.total_seconds() > 86400  # More than 1 day


class TestDecodeToken:
    """Tests for token decoding."""

    def test_decode_valid_token(self):
        """Should decode valid token."""
        from app.config import settings
        user_id = uuid4()
        
        token = create_access_token(user_id)
        
        payload = decode_token(token)
        
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_decode_expired_token(self):
        """Should raise error for expired token."""
        from app.config import settings
        user_id = uuid4()
        
        # Create token that expires immediately
        with patch('app.infrastructure.auth.jwt_handler.settings') as mock_settings:
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = -1  # Already expired
            mock_settings.JWT_SECRET_KEY = settings.JWT_SECRET_KEY
            mock_settings.JWT_ALGORITHM = settings.JWT_ALGORITHM
            
            token = create_access_token(user_id)
        
        with pytest.raises(AuthenticationError, match="expired"):
            decode_token(token)

    def test_decode_invalid_signature(self):
        """Should raise error for invalid signature."""
        user_id = uuid4()
        token = create_access_token(user_id)
        
        # Tamper with token
        tampered_token = token[:-10] + "XXXXXXXXXX"
        
        with pytest.raises(AuthenticationError):
            decode_token(tampered_token)

    def test_decode_malformed_token(self):
        """Should raise error for malformed token."""
        with pytest.raises(AuthenticationError):
            decode_token("not.a.valid.jwt.token")

    def test_decode_token_with_wrong_secret(self):
        """Should raise error when secret doesn't match."""
        from app.config import settings
        user_id = uuid4()
        
        token = create_access_token(user_id)
        
        # Try to decode with wrong secret
        with patch('app.infrastructure.auth.jwt_handler.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "wrong-secret-key"
            mock_settings.JWT_ALGORITHM = settings.JWT_ALGORITHM
            
            with pytest.raises(AuthenticationError):
                decode_token(token)


class TestTokenEdgeCases:
    """Edge case tests for token operations."""

    def test_create_token_with_none_tenant(self):
        """Should handle None tenant_id."""
        user_id = uuid4()
        
        token = create_access_token(user_id, tenant_id=None)
        
        payload = jwt.decode(token, options={"verify_signature": False})
        assert "tenant_id" not in payload

    def test_create_token_with_empty_extra_claims(self):
        """Should handle empty extra claims."""
        user_id = uuid4()
        
        token = create_access_token(user_id, extra_claims={})
        
        assert token is not None

    def test_tokens_are_url_safe(self):
        """Should create URL-safe tokens."""
        user_id = uuid4()
        
        token = create_access_token(user_id)
        
        # JWT tokens should only contain URL-safe characters
        import string
        allowed_chars = string.ascii_letters + string.digits + "-_."
        assert all(c in allowed_chars for c in token)

    def test_multiple_tokens_for_same_user(self):
        """Should create different tokens for same user."""
        user_id = uuid4()
        
        token1 = create_access_token(user_id)
        token2 = create_access_token(user_id)
        
        assert token1 != token2


class TestBcryptConfiguration:
    """Tests for bcrypt configuration."""

    def test_bcrypt_rounds_constant(self):
        """Should use secure bcrypt rounds."""
        assert BCRYPT_ROUNDS >= 10
        assert BCRYPT_ROUNDS <= 15  # Reasonable upper limit

    def test_hash_uses_bcrypt_rounds(self):
        """Should use configured bcrypt rounds."""
        password = "test_password"
        hashed = hash_password(password)
        
        # Bcrypt hashes start with $2b${rounds}$
        # Extract rounds from hash
        parts = hashed.split("$")
        rounds = int(parts[2])
        
        assert rounds == BCRYPT_ROUNDS
