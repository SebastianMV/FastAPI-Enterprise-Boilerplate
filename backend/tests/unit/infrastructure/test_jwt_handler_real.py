# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for JWT authentication handler with real execution."""

from __future__ import annotations

from uuid import uuid4

import pytest


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_import(self) -> None:
        """Test hash_password can be imported."""
        from app.infrastructure.auth.jwt_handler import hash_password

        assert hash_password is not None
        assert callable(hash_password)

    def test_hash_password_returns_string(self) -> None:
        """Test hash_password returns a string."""
        from app.infrastructure.auth.jwt_handler import hash_password

        result = hash_password("testpassword123")
        assert isinstance(result, str)

    def test_hash_password_is_bcrypt(self) -> None:
        """Test hash_password produces bcrypt hash."""
        from app.infrastructure.auth.jwt_handler import hash_password

        result = hash_password("testpassword123")
        # Bcrypt hashes start with $2b$
        assert result.startswith("$2b$")

    def test_hash_password_produces_unique_hashes(self) -> None:
        """Test same password produces different hashes."""
        from app.infrastructure.auth.jwt_handler import hash_password

        password = "samepassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        # Different salts should produce different hashes
        assert hash1 != hash2


class TestPasswordVerification:
    """Tests for password verification."""

    def test_verify_password_import(self) -> None:
        """Test verify_password can be imported."""
        from app.infrastructure.auth.jwt_handler import verify_password

        assert verify_password is not None

    def test_verify_password_correct(self) -> None:
        """Test verify_password with correct password."""
        from app.infrastructure.auth.jwt_handler import hash_password, verify_password

        password = "correctpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Test verify_password with incorrect password."""
        from app.infrastructure.auth.jwt_handler import hash_password, verify_password

        password = "correctpassword123"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_invalid_hash(self) -> None:
        """Test verify_password with invalid hash."""
        from app.infrastructure.auth.jwt_handler import verify_password

        result = verify_password("password", "invalid_hash")
        assert result is False


class TestAccessToken:
    """Tests for access token functions."""

    def test_create_access_token_import(self) -> None:
        """Test create_access_token can be imported."""
        from app.infrastructure.auth.jwt_handler import create_access_token

        assert create_access_token is not None

    def test_create_access_token_returns_string(self) -> None:
        """Test create_access_token returns a JWT string."""
        from app.infrastructure.auth.jwt_handler import create_access_token

        user_id = uuid4()
        token = create_access_token(user_id)
        assert isinstance(token, str)
        # JWT has 3 parts separated by dots
        assert len(token.split(".")) == 3

    def test_create_access_token_with_tenant(self) -> None:
        """Test create_access_token with tenant_id."""
        from app.infrastructure.auth.jwt_handler import create_access_token

        user_id = uuid4()
        tenant_id = uuid4()
        token = create_access_token(user_id, tenant_id)
        assert isinstance(token, str)

    def test_create_access_token_with_extra_claims(self) -> None:
        """Test create_access_token with extra claims."""
        from app.infrastructure.auth.jwt_handler import create_access_token

        user_id = uuid4()
        token = create_access_token(user_id, extra_claims={"role": "admin"})
        assert isinstance(token, str)


class TestRefreshToken:
    """Tests for refresh token functions."""

    def test_create_refresh_token_import(self) -> None:
        """Test create_refresh_token can be imported."""
        from app.infrastructure.auth.jwt_handler import create_refresh_token

        assert create_refresh_token is not None

    def test_create_refresh_token_returns_string(self) -> None:
        """Test create_refresh_token returns a JWT string."""
        from app.infrastructure.auth.jwt_handler import create_refresh_token

        user_id = uuid4()
        token = create_refresh_token(user_id)
        assert isinstance(token, str)
        assert len(token.split(".")) == 3


class TestDecodeToken:
    """Tests for token decoding."""

    def test_decode_token_import(self) -> None:
        """Test decode_token can be imported."""
        from app.infrastructure.auth.jwt_handler import decode_token

        assert decode_token is not None

    def test_decode_token_valid(self) -> None:
        """Test decode_token with valid token."""
        from app.infrastructure.auth.jwt_handler import (
            create_access_token,
            decode_token,
        )

        user_id = uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_decode_token_invalid(self) -> None:
        """Test decode_token with invalid token."""
        from app.domain.exceptions.base import AuthenticationError
        from app.infrastructure.auth.jwt_handler import decode_token

        with pytest.raises(AuthenticationError):
            decode_token("invalid.token.here")


class TestGetTokenUserId:
    """Tests for get_token_user_id."""

    def test_get_token_user_id_import(self) -> None:
        """Test get_token_user_id can be imported."""
        from app.infrastructure.auth.jwt_handler import get_token_user_id

        assert get_token_user_id is not None

    def test_get_token_user_id_returns_uuid(self) -> None:
        """Test get_token_user_id returns UUID."""
        from uuid import UUID

        from app.infrastructure.auth.jwt_handler import (
            create_access_token,
            get_token_user_id,
        )

        user_id = uuid4()
        token = create_access_token(user_id)
        result = get_token_user_id(token)

        assert isinstance(result, UUID)
        assert result == user_id


class TestValidateAccessToken:
    """Tests for validate_access_token."""

    def test_validate_access_token_import(self) -> None:
        """Test validate_access_token can be imported."""
        from app.infrastructure.auth.jwt_handler import validate_access_token

        assert validate_access_token is not None

    def test_validate_access_token_valid(self) -> None:
        """Test validate_access_token with valid access token."""
        from app.infrastructure.auth.jwt_handler import (
            create_access_token,
            validate_access_token,
        )

        user_id = uuid4()
        token = create_access_token(user_id)
        payload = validate_access_token(token)

        assert payload["type"] == "access"


class TestBcryptConstants:
    """Tests for bcrypt configuration."""

    def test_bcrypt_rounds_exists(self) -> None:
        """Test BCRYPT_ROUNDS constant exists."""
        from app.infrastructure.auth.jwt_handler import BCRYPT_ROUNDS

        assert BCRYPT_ROUNDS is not None
        assert BCRYPT_ROUNDS >= 10  # Should be secure
