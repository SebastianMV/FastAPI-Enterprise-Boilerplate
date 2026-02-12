# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""User domain entity."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.entities.base import TenantSoftDeletableEntity
from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password


@dataclass
class User(TenantSoftDeletableEntity):
    """
    User domain entity.

    Represents a user in the system with authentication
    and authorization capabilities.
    """

    email: Email = field(default_factory=lambda: Email("user@example.com"))
    password_hash: str = ""
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_superuser: bool = False
    last_login: datetime | None = None
    roles: list[UUID] = field(default_factory=list)

    # Account Lockout
    failed_login_attempts: int = 0
    locked_until: datetime | None = None

    # Email Verification
    email_verified: bool = False
    email_verification_token: str | None = None
    email_verification_sent_at: datetime | None = None

    # Avatar
    avatar_url: str | None = None

    @classmethod
    def create(
        cls,
        email: str,
        first_name: str,
        last_name: str,
        tenant_id: UUID | None = None,
    ) -> "User":
        """
        Factory method to create a new User entity.

        Args:
            email: User email address
            first_name: User first name
            last_name: User last name
            tenant_id: Optional tenant ID (auto-generated if not provided)

        Returns:
            New User instance with generated ID and timestamps
        """

        kwargs: dict[str, Any] = {
            "email": Email(email),
            "first_name": first_name,
            "last_name": last_name,
        }
        if tenant_id is not None:
            kwargs["tenant_id"] = tenant_id
        return cls(**kwargs)

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def set_password(self, password: Password, hasher: Callable[[str], str]) -> None:
        """
        Set user password using provided hasher.

        Args:
            password: Validated password value object
            hasher: Function to hash the password
        """
        self.password_hash = hasher(password.value)

    def verify_password(self, plain_password: str, verifier: Callable[[str, str], bool]) -> bool:
        """
        Verify password against stored hash.

        Args:
            plain_password: Plain text password to verify
            verifier: Function to verify password

        Returns:
            True if password matches, False otherwise
        """
        return verifier(plain_password, self.password_hash)

    def record_login(self) -> None:
        """Record successful login timestamp."""
        self.last_login = datetime.now(UTC)

    def activate(self) -> None:
        """Activate user account."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False

    def add_role(self, role_id: UUID) -> None:
        """Add role to user if not already assigned."""
        if role_id not in self.roles:
            self.roles.append(role_id)

    def remove_role(self, role_id: UUID) -> None:
        """Remove role from user."""
        if role_id in self.roles:
            self.roles.remove(role_id)

    def has_role(self, role_id: UUID) -> bool:
        """Check if user has specific role."""
        return role_id in self.roles

    # ===========================================
    # Account Lockout Methods
    # ===========================================

    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.now(UTC) < self.locked_until

    def record_failed_login(
        self, lockout_threshold: int, lockout_duration_minutes: int
    ) -> bool:
        """
        Record a failed login attempt.

        Args:
            lockout_threshold: Number of failures before lockout
            lockout_duration_minutes: How long to lock the account

        Returns:
            True if account is now locked, False otherwise
        """
        from datetime import timedelta

        self.failed_login_attempts += 1

        if self.failed_login_attempts >= lockout_threshold:
            self.locked_until = datetime.now(UTC) + timedelta(
                minutes=lockout_duration_minutes
            )
            return True
        return False

    def reset_failed_attempts(self) -> None:
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def unlock(self) -> None:
        """Manually unlock the account."""
        self.locked_until = None
        self.failed_login_attempts = 0

    # ===========================================
    # Email Verification Methods
    # ===========================================

    def generate_verification_token(self) -> str:
        """Generate a new email verification token.

        Stores SHA-256 hash of the token in the entity (for indexed lookup),
        and returns the raw token to be sent via email.
        """
        import hashlib
        import secrets

        raw_token = secrets.token_urlsafe(32)
        self.email_verification_token = hashlib.sha256(
            raw_token.encode()
        ).hexdigest()
        self.email_verification_sent_at = datetime.now(UTC)
        return raw_token

    def verify_email(self, token: str, token_expire_hours: int = 24) -> bool:
        """
        Verify email with provided token.

        Args:
            token: Verification token to check
            token_expire_hours: How long the token is valid

        Returns:
            True if verification successful, False otherwise
        """
        import hashlib
        import hmac
        from datetime import timedelta

        if self.email_verified:
            return True  # Already verified

        # Hash input token for comparison against stored hash
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if not self.email_verification_token or not hmac.compare_digest(
            self.email_verification_token, token_hash
        ):
            return False

        if self.email_verification_sent_at is None:
            return False

        # Check if token expired
        expiry = self.email_verification_sent_at + timedelta(hours=token_expire_hours)
        if datetime.now(UTC) > expiry:
            return False

        # Mark as verified
        self.email_verified = True
        self.email_verification_token = None
        return True

    def is_verification_token_expired(self, token_expire_hours: int = 24) -> bool:
        """Check if verification token has expired."""
        from datetime import timedelta

        if self.email_verification_sent_at is None:
            return True

        expiry = self.email_verification_sent_at + timedelta(hours=token_expire_hours)
        return datetime.now(UTC) > expiry
