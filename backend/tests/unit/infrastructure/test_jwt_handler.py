# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for JWT handler."""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from app.infrastructure.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_user_id,
    hash_password,
    validate_access_token,
    validate_refresh_token,
    verify_password,
)
from app.domain.exceptions.base import AuthenticationError


class TestPasswordHashing:
    """Tests for password hashing."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "SecureP@ss123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
    
    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "SecureP@ss123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        hashed = hash_password("SecureP@ss123")
        
        assert verify_password("WrongPassword!", hashed) is False
    
    def test_different_hashes_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "SecureP@ss123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestAccessToken:
    """Tests for access tokens."""
    
    def test_create_access_token(self):
        """Test creating access token."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)
        
        assert token is not None
        assert len(token) > 100  # JWT tokens are long
    
    def test_create_access_token_with_tenant(self):
        """Test creating access token with tenant."""
        user_id = uuid4()
        tenant_id = uuid4()
        
        token = create_access_token(user_id=user_id, tenant_id=tenant_id)
        payload = decode_token(token)
        
        assert payload["tenant_id"] == str(tenant_id)
    
    def test_create_access_token_with_extra_claims(self):
        """Test creating access token with extra claims."""
        user_id = uuid4()
        
        token = create_access_token(
            user_id=user_id,
            extra_claims={"is_superuser": True},
        )
        payload = decode_token(token)
        
        assert payload["is_superuser"] is True
    
    def test_validate_access_token(self):
        """Test validating access token."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)
        
        payload = validate_access_token(token)
        
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
    
    def test_validate_access_token_wrong_type(self):
        """Test that refresh token fails access validation."""
        user_id = uuid4()
        refresh_token = create_refresh_token(user_id=user_id)
        
        with pytest.raises(AuthenticationError, match="access token"):
            validate_access_token(refresh_token)


class TestRefreshToken:
    """Tests for refresh tokens."""
    
    def test_create_refresh_token(self):
        """Test creating refresh token."""
        user_id = uuid4()
        token = create_refresh_token(user_id=user_id)
        
        assert token is not None
        assert len(token) > 100
    
    def test_validate_refresh_token(self):
        """Test validating refresh token."""
        user_id = uuid4()
        token = create_refresh_token(user_id=user_id)
        
        payload = validate_refresh_token(token)
        
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
    
    def test_validate_refresh_token_wrong_type(self):
        """Test that access token fails refresh validation."""
        user_id = uuid4()
        access_token = create_access_token(user_id=user_id)
        
        with pytest.raises(AuthenticationError, match="refresh token"):
            validate_refresh_token(access_token)


class TestTokenDecode:
    """Tests for token decoding."""
    
    def test_decode_valid_token(self):
        """Test decoding valid token."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)
        
        payload = decode_token(token)
        
        assert payload["sub"] == str(user_id)
        assert "exp" in payload
        assert "iat" in payload
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token raises error."""
        with pytest.raises(AuthenticationError):
            decode_token("invalid.token.here")
    
    def test_decode_tampered_token(self):
        """Test decoding tampered token raises error."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)
        
        # Tamper with token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "XXXXX"
        tampered = ".".join(parts)
        
        with pytest.raises(AuthenticationError):
            decode_token(tampered)
    
    def test_get_token_user_id(self):
        """Test extracting user ID from token."""
        user_id = uuid4()
        token = create_access_token(user_id=user_id)
        
        extracted_id = get_token_user_id(token)
        
        assert extracted_id == user_id
