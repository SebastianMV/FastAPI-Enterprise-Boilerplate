# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Extended unit tests for User domain entity."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.entities.user import User
from app.domain.value_objects.email import Email


class TestUserLocking:
    """Test user account locking functionality."""

    def test_record_failed_login(self):
        """Test recording failed login attempts."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        assert user.failed_login_attempts == 0

        # Record failures but not enough to lock
        is_locked = user.record_failed_login(
            lockout_threshold=5, lockout_duration_minutes=15
        )
        assert not is_locked
        assert user.failed_login_attempts == 1

        # Lock after threshold
        for _ in range(4):
            user.record_failed_login(lockout_threshold=5, lockout_duration_minutes=15)

        assert user.is_locked()
        assert user.locked_until is not None

    def test_unlock_account(self):
        """Test unlocking a user account."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        # Lock the account
        user.record_failed_login(lockout_threshold=1, lockout_duration_minutes=15)
        assert user.is_locked()

        user.unlock()

        assert not user.is_locked()
        assert user.locked_until is None
        assert user.failed_login_attempts == 0

    def test_reset_failed_attempts(self):
        """Test resetting failed login attempts."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        user.record_failed_login(lockout_threshold=5, lockout_duration_minutes=15)
        assert user.failed_login_attempts > 0

        user.reset_failed_attempts()

        assert user.failed_login_attempts == 0
        assert user.locked_until is None


class TestUserActivation:
    """Test user activation/deactivation."""

    def test_activate_user(self):
        """Test activating a user."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
            is_active=False,
        )

        user.activate()

        assert user.is_active

    def test_deactivate_user(self):
        """Test deactivating a user."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
            is_active=True,
        )

        user.deactivate()

        assert not user.is_active


class TestUserProperties:
    """Test user computed properties."""

    def test_full_name_with_both_names(self):
        """Test full_name property with first and last name."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
            first_name="John",
            last_name="Doe",
        )

        assert user.full_name == "John Doe"

    def test_full_name_first_only(self):
        """Test full_name property with only first name."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
            first_name="John",
            last_name="",
        )

        assert user.full_name == "John"

    def test_full_name_last_only(self):
        """Test full_name property with only last name."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
            first_name="",
            last_name="Doe",
        )

        assert user.full_name == "Doe"

    def test_full_name_empty(self):
        """Test full_name property with no names."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
            first_name="",
            last_name="",
        )

        assert user.full_name == ""


class TestEmailVerification:
    """Test email verification methods."""

    def test_generate_verification_token(self):
        """Test generating verification token."""
        import hashlib

        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        raw_token = user.generate_verification_token()

        assert isinstance(raw_token, str)
        assert len(raw_token) > 0
        # Stored token is SHA-256 hash of raw token
        expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        assert user.email_verification_token == expected_hash
        assert user.email_verification_sent_at is not None

    def test_verify_email_success(self):
        """Test successful email verification."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        token = user.generate_verification_token()
        result = user.verify_email(token, token_expire_hours=24)

        assert result is True
        assert user.email_verified
        assert user.email_verification_token is None

    def test_verify_email_wrong_token(self):
        """Test email verification with wrong token."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        user.generate_verification_token()
        result = user.verify_email("wrong-token", token_expire_hours=24)

        assert result is False
        assert not user.email_verified

    def test_verify_email_expired_token(self):
        """Test email verification with expired token."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        token = user.generate_verification_token()
        # Manually set sent_at to past
        user.email_verification_sent_at = datetime.now(UTC) - timedelta(hours=25)

        result = user.verify_email(token, token_expire_hours=24)

        assert result is False
        assert not user.email_verified


class TestUserRoles:
    """Test role management methods."""

    def test_add_role(self):
        """Test adding role to user."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        role_id = uuid4()
        user.add_role(role_id)

        assert user.has_role(role_id)
        assert role_id in user.roles

    def test_add_duplicate_role(self):
        """Test adding same role twice."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        role_id = uuid4()
        user.add_role(role_id)
        user.add_role(role_id)

        assert len(user.roles) == 1

    def test_remove_role(self):
        """Test removing role from user."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("user@example.com"),
            password_hash="hash",
        )

        role_id = uuid4()
        user.add_role(role_id)
        user.remove_role(role_id)

        assert not user.has_role(role_id)
        assert role_id not in user.roles
