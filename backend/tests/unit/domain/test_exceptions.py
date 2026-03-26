# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Unit tests for domain exceptions."""

from app.domain.exceptions.base import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainException,
    EntityNotFoundError,
    RateLimitExceededError,
    ValidationError,
)


class TestDomainException:
    """Tests for base DomainException."""

    def test_exception_creation(self):
        """Test creating domain exception."""
        exc = DomainException(message="Test error")

        assert str(exc) == "Test error"
        assert exc.code == "DOMAIN_ERROR"
        assert exc.details == {}

    def test_exception_with_details(self):
        """Test exception with details."""
        exc = DomainException(
            message="Test error",
            code="CUSTOM_CODE",
            details={"key": "value"},
        )

        assert exc.code == "CUSTOM_CODE"
        assert exc.details == {"key": "value"}


class TestEntityNotFoundError:
    """Tests for EntityNotFoundError."""

    def test_auto_message(self):
        """Test automatic message generation."""
        exc = EntityNotFoundError(
            message="",
            entity_type="User",
            entity_id="123",
        )

        assert "User" in str(exc)
        assert "not found" in str(exc)
        assert exc.code == "ENTITY_NOT_FOUND"


class TestValidationError:
    """Tests for ValidationError."""

    def test_validation_error(self):
        """Test validation error."""
        exc = ValidationError(
            message="Invalid email format",
            field="email",
        )

        assert exc.field == "email"
        assert exc.code == "VALIDATION_ERROR"


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_authentication_error(self):
        """Test authentication error."""
        exc = AuthenticationError(message="Invalid credentials")

        assert exc.code == "AUTHENTICATION_FAILED"


class TestAuthorizationError:
    """Tests for AuthorizationError."""

    def test_authorization_error_auto_message(self):
        """Test automatic message generation."""
        exc = AuthorizationError(
            message="",
            resource="users",
            action="delete",
        )

        assert str(exc) == "Insufficient permissions"
        assert exc.resource == "users"
        assert exc.action == "delete"
        assert exc.code == "AUTHORIZATION_DENIED"

    def test_authorization_error_custom_message(self):
        """Test custom message."""
        exc = AuthorizationError(
            message="Custom access denied message",
            resource="users",
            action="delete",
        )

        assert str(exc) == "Custom access denied message"


class TestConflictError:
    """Tests for ConflictError."""

    def test_conflict_error(self):
        """Test conflict error."""
        exc = ConflictError(
            message="Email already exists",
            conflicting_field="email",
        )

        assert exc.conflicting_field == "email"
        assert exc.code == "CONFLICT"


class TestRateLimitExceededError:
    """Tests for RateLimitExceededError."""

    def test_auto_message(self):
        """Test automatic message generation."""
        exc = RateLimitExceededError(
            message="",
            retry_after_seconds=120,
        )

        assert "Rate limit exceeded" in str(exc)
        assert exc.code == "RATE_LIMIT_EXCEEDED"
        assert exc.retry_after_seconds == 120
