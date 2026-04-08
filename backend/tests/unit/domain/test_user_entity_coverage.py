# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Comprehensive tests for User entity to achieve 100% coverage.
Focuses on 8 uncovered lines in app/domain/entities/user.py
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password


class TestUserSetPassword:
    """Tests for User.set_password method (line 55)."""

    def test_set_password_hashes_password(self):
        """Test set_password correctly hashes the password."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("test@example.com"),
            first_name="Test",
            last_name="User",
            password_hash="old_hash",
            is_active=True,
            is_superuser=False,
        )

        mock_hasher = MagicMock(return_value="new_hashed_value")
        password = Password("NewSecureP@ss123")

        user.set_password(password, mock_hasher)

        mock_hasher.assert_called_once_with("NewSecureP@ss123")
        assert user.password_hash == "new_hashed_value"

    def test_set_password_produces_verifiable_hash(self):
        """Test set_password produces hash that can be verified."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("test@example.com"),
            first_name="Test",
            last_name="User",
            password_hash="",
            is_active=True,
            is_superuser=False,
        )

        # Simulate hasher that just prefixes with "hash_"
        def simple_hasher(password: str) -> str:
            return f"hash_{password}"

        def simple_verifier(plain: str, hashed: str) -> bool:
            return hashed == f"hash_{plain}"

        password = Password("MySecure@Pass456")
        user.set_password(password, simple_hasher)

        assert user.verify_password("MySecure@Pass456", simple_verifier) == True
        assert user.verify_password("WrongPassword", simple_verifier) == False


class TestUserEmailVerification:
    """Tests for User.verify_email method (lines 160, 166)."""

    def test_verify_email_already_verified(self):
        """Test verify_email returns True if already verified."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("verified@example.com"),
            first_name="Verified",
            last_name="User",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verified=True,
        )

        result = user.verify_email("any_token")

        assert result == True

    def test_verify_email_wrong_token(self):
        """Test verify_email returns False for wrong token."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("unverified@example.com"),
            first_name="Unverified",
            last_name="User",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verified=False,
            email_verification_token="correct_token_123",
            email_verification_sent_at=datetime.now(UTC),
        )

        result = user.verify_email("wrong_token")

        assert result == False
        assert user.email_verified == False

    def test_verify_email_correct_token_not_expired(self):
        """Test verify_email marks verified for correct token."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("pending@example.com"),
            first_name="Pending",
            last_name="User",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verified=False,
        )

        # Use generate_verification_token to properly set up (stores SHA-256 hash)
        raw_token = user.generate_verification_token()
        # Backdate sent_at to 1 hour ago (still within 24h expiry)
        user.email_verification_sent_at = datetime.now(UTC) - timedelta(hours=1)

        result = user.verify_email(raw_token, token_expire_hours=24)

        assert result == True
        assert user.email_verified == True
        assert user.email_verification_token is None

    def test_verify_email_correct_token_expired(self):
        """Test verify_email returns False for expired token."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("expired@example.com"),
            first_name="Expired",
            last_name="User",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verified=False,
            email_verification_token="expired_token",
            email_verification_sent_at=datetime.now(UTC) - timedelta(hours=48),
        )

        result = user.verify_email("expired_token", token_expire_hours=24)

        assert result == False
        assert user.email_verified == False

    def test_verify_email_correct_token_no_sent_at(self):
        """Test verify_email returns False when sent_at is None."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("nosenttime@example.com"),
            first_name="NoSent",
            last_name="Time",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verified=False,
            email_verification_token="valid_token",
            email_verification_sent_at=None,  # This triggers line 166
        )

        # Even with correct token, should fail if sent_at is None
        result = user.verify_email("valid_token")

        assert result == False
        assert user.email_verified == False


class TestUserVerificationTokenExpiry:
    """Tests for User.is_verification_token_expired method (lines 180-186)."""

    def test_is_verification_token_expired_no_sent_at(self):
        """Test is_verification_token_expired returns True if sent_at is None."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("nosent@example.com"),
            first_name="No",
            last_name="Sent",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verification_sent_at=None,
        )

        result = user.is_verification_token_expired(token_expire_hours=24)

        assert result == True

    def test_is_verification_token_expired_not_expired(self):
        """Test is_verification_token_expired returns False if not expired."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("fresh@example.com"),
            first_name="Fresh",
            last_name="Token",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verification_sent_at=datetime.now(UTC) - timedelta(hours=1),
        )

        result = user.is_verification_token_expired(token_expire_hours=24)

        assert result == False

    def test_is_verification_token_expired_is_expired(self):
        """Test is_verification_token_expired returns True if expired."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("old@example.com"),
            first_name="Old",
            last_name="Token",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verification_sent_at=datetime.now(UTC) - timedelta(hours=48),
        )

        result = user.is_verification_token_expired(token_expire_hours=24)

        assert result == True

    def test_is_verification_token_expired_boundary_case(self):
        """Test is_verification_token_expired at exact boundary."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("boundary@example.com"),
            first_name="Boundary",
            last_name="Case",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verification_sent_at=datetime.now(UTC)
            - timedelta(hours=24, minutes=1),
        )

        result = user.is_verification_token_expired(token_expire_hours=24)

        assert result == True


class TestUserGenerateVerificationToken:
    """Tests for User.generate_verification_token method."""

    def test_generate_verification_token_creates_token(self):
        """Test generate_verification_token creates a token."""
        import hashlib

        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("generate@example.com"),
            first_name="Generate",
            last_name="Token",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
        )

        raw_token = user.generate_verification_token()

        assert raw_token is not None
        assert len(raw_token) > 0
        # Stored token is SHA-256 hash of raw token
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        assert user.email_verification_token == expected_hash
        assert user.email_verification_sent_at is not None

    def test_generate_verification_token_updates_sent_at(self):
        """Test generate_verification_token updates sent_at timestamp."""
        old_time = datetime.now(UTC) - timedelta(days=1)
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("update@example.com"),
            first_name="Update",
            last_name="SentAt",
            password_hash="hash",
            is_active=True,
            is_superuser=False,
            email_verification_sent_at=old_time,
        )

        user.generate_verification_token()

        assert user.email_verification_sent_at > old_time
