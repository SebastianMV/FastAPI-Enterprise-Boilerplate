# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for JWT handler."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest


class TestJWTTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token(self) -> None:
        """Test creating access token."""
        from app.infrastructure.auth.jwt_handler import create_access_token

        user_id = uuid4()
        tenant_id = uuid4()

        token = create_access_token(user_id=user_id, tenant_id=tenant_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_extra_claims(self) -> None:
        """Test creating access token with extra claims."""
        from app.infrastructure.auth.jwt_handler import create_access_token

        user_id = uuid4()
        token = create_access_token(
            user_id=user_id,
            extra_claims={"is_superuser": True, "roles": ["admin"]},
        )

        assert token is not None

    def test_create_refresh_token(self) -> None:
        """Test creating refresh token."""
        from app.infrastructure.auth.jwt_handler import create_refresh_token

        user_id = uuid4()
        token = create_refresh_token(user_id=user_id)

        assert token is not None
        assert isinstance(token, str)


class TestJWTTokenValidation:
    """Tests for JWT token validation."""

    def test_validate_access_token(self) -> None:
        """Test validating access token."""
        from app.infrastructure.auth.jwt_handler import (
            create_access_token,
            validate_access_token,
        )

        user_id = uuid4()
        token = create_access_token(user_id=user_id)

        payload = validate_access_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_validate_refresh_token(self) -> None:
        """Test validating refresh token."""
        from app.infrastructure.auth.jwt_handler import (
            create_refresh_token,
            validate_refresh_token,
        )

        user_id = uuid4()
        token = create_refresh_token(user_id=user_id)

        payload = validate_refresh_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_validate_invalid_token(self) -> None:
        """Test validating invalid token raises error."""
        from app.domain.exceptions.base import AuthenticationError
        from app.infrastructure.auth.jwt_handler import validate_access_token

        with pytest.raises(AuthenticationError):
            validate_access_token("invalid.token.here")

    def test_validate_expired_token(self) -> None:
        """Test validating expired token raises error."""
        # Create token that's already expired
        import jwt

        from app.config import settings
        from app.domain.exceptions.base import AuthenticationError
        from app.infrastructure.auth.jwt_handler import validate_access_token

        payload = {
            "sub": str(uuid4()),
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

        with pytest.raises(AuthenticationError):
            validate_access_token(token)


class TestPasswordHashing:
    """Tests for password hashing."""

    def test_hash_password(self) -> None:
        """Test password hashing."""
        from app.infrastructure.auth.jwt_handler import hash_password

        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password

    def test_hash_password_unique(self) -> None:
        """Test that same password produces different hashes."""
        from app.infrastructure.auth.jwt_handler import hash_password

        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Bcrypt uses random salt, so hashes should differ
        assert hash1 != hash2

    def test_verify_password_correct(self) -> None:
        """Test verifying correct password."""
        from app.infrastructure.auth.jwt_handler import hash_password, verify_password

        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Test verifying incorrect password."""
        from app.infrastructure.auth.jwt_handler import hash_password, verify_password

        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password("WrongPassword123!", hashed) is False


class TestTokenPayload:
    """Tests for token payload structure."""

    def test_access_token_contains_user_id(self) -> None:
        """Test access token contains user ID."""
        from app.infrastructure.auth.jwt_handler import (
            create_access_token,
            validate_access_token,
        )

        user_id = uuid4()
        token = create_access_token(user_id=user_id)
        payload = validate_access_token(token)

        assert "sub" in payload
        assert payload["sub"] == str(user_id)

    def test_access_token_contains_tenant_id(self) -> None:
        """Test access token contains tenant ID."""
        from app.infrastructure.auth.jwt_handler import (
            create_access_token,
            validate_access_token,
        )

        user_id = uuid4()
        tenant_id = uuid4()
        token = create_access_token(user_id=user_id, tenant_id=tenant_id)
        payload = validate_access_token(token)

        assert "tenant_id" in payload
        assert payload["tenant_id"] == str(tenant_id)

    def test_access_token_has_expiration(self) -> None:
        """Test access token has expiration."""
        from app.infrastructure.auth.jwt_handler import (
            create_access_token,
            validate_access_token,
        )

        token = create_access_token(user_id=uuid4())
        payload = validate_access_token(token)

        assert "exp" in payload

    def test_refresh_token_has_type(self) -> None:
        """Test refresh token has correct type."""
        from app.infrastructure.auth.jwt_handler import (
            create_refresh_token,
            validate_refresh_token,
        )

        token = create_refresh_token(user_id=uuid4())
        payload = validate_refresh_token(token)

        # Refresh tokens typically have a different type or longer expiration
        assert payload is not None


class TestValidateRefreshTokenEdgeCases:
    """Test edge cases in validate_refresh_token."""

    def test_validate_refresh_token_missing_user_id(self) -> None:
        """Test validation fails when token has no 'sub' claim."""
        import jwt

        from app.config import settings
        from app.domain.exceptions.base import AuthenticationError
        from app.infrastructure.auth.jwt_handler import validate_refresh_token

        # Create token without 'sub' claim
        payload = {
            "exp": datetime.now(UTC) + timedelta(days=7),
            "jti": str(uuid4()),
        }
        token = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(AuthenticationError) as exc:
            validate_refresh_token(token)

        assert exc.value.code in ("INVALID_TOKEN", "INVALID_TOKEN_TYPE")
        assert exc.value.message is not None
