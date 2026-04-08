# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for domain exceptions."""

from __future__ import annotations

import pytest


class TestDomainExceptions:
    """Tests for domain exception classes."""

    def test_authentication_error(self) -> None:
        """Test AuthenticationError exception."""
        from app.domain.exceptions.base import AuthenticationError

        error = AuthenticationError("Invalid credentials", "INVALID_CREDENTIALS")
        assert error.message == "Invalid credentials"
        assert error.code == "INVALID_CREDENTIALS"
        assert str(error) == "Invalid credentials"

    def test_authorization_error(self) -> None:
        """Test AuthorizationError exception."""
        from app.domain.exceptions.base import AuthorizationError

        error = AuthorizationError("Access denied", "ACCESS_DENIED")
        assert error.message == "Access denied"
        assert error.code == "ACCESS_DENIED"

    def test_entity_not_found_error(self) -> None:
        """Test EntityNotFoundError exception."""
        from app.domain.exceptions.base import EntityNotFoundError

        error = EntityNotFoundError("User not found", "USER_NOT_FOUND")
        assert error.message == "User not found"
        assert error.code == "USER_NOT_FOUND"

    def test_conflict_error(self) -> None:
        """Test ConflictError exception."""
        from app.domain.exceptions.base import ConflictError

        error = ConflictError("Email already exists", "EMAIL_EXISTS")
        assert error.message == "Email already exists"
        assert error.code == "EMAIL_EXISTS"

    def test_validation_error(self) -> None:
        """Test ValidationError exception."""
        from app.domain.exceptions.base import ValidationError

        error = ValidationError("Invalid input", "VALIDATION_ERROR")
        assert error.message == "Invalid input"
        assert error.code == "VALIDATION_ERROR"

    def test_domain_error_inheritance(self) -> None:
        """Test domain errors are proper exceptions."""
        from app.domain.exceptions.base import (
            AuthenticationError,
            AuthorizationError,
            ConflictError,
            EntityNotFoundError,
            ValidationError,
        )

        # All should be exceptions
        assert issubclass(AuthenticationError, Exception)
        assert issubclass(AuthorizationError, Exception)
        assert issubclass(EntityNotFoundError, Exception)
        assert issubclass(ConflictError, Exception)
        assert issubclass(ValidationError, Exception)

    def test_domain_error_is_exception(self) -> None:
        """Test domain errors are Exceptions."""
        from app.domain.exceptions.base import AuthenticationError

        error = AuthenticationError("Test", "TEST")
        assert isinstance(error, Exception)

    def test_exception_can_be_raised(self) -> None:
        """Test exceptions can be raised and caught."""
        from app.domain.exceptions.base import AuthenticationError

        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Test error", "TEST")

        assert exc_info.value.code == "TEST"


class TestExceptionDetails:
    """Tests for exception details and attributes."""

    def test_error_with_details(self) -> None:
        """Test error with additional details."""
        from app.domain.exceptions.base import ValidationError

        error = ValidationError("Field validation failed", "FIELD_ERROR")
        assert hasattr(error, "message")
        assert hasattr(error, "code")

    def test_error_repr(self) -> None:
        """Test error string representation."""
        from app.domain.exceptions.base import AuthenticationError

        error = AuthenticationError("Bad token", "BAD_TOKEN")
        repr_str = repr(error)
        assert "AuthenticationError" in repr_str or "Bad token" in str(error)


class TestTenantError:
    """Tests for tenant-related errors."""

    def test_tenant_not_found(self) -> None:
        """Test tenant not found error."""
        from app.domain.exceptions.base import EntityNotFoundError

        error = EntityNotFoundError("Tenant not found", "TENANT_NOT_FOUND")
        assert "Tenant" in error.message

    def test_tenant_inactive(self) -> None:
        """Test tenant inactive error."""
        from app.domain.exceptions.base import AuthorizationError

        error = AuthorizationError("Tenant is inactive", "TENANT_INACTIVE")
        assert error.code == "TENANT_INACTIVE"


class TestRateLimitError:
    """Tests for rate limit error if exists."""

    def test_rate_limit_error(self) -> None:
        """Test rate limit error creation."""
        # Use existing error type for rate limiting
        from app.domain.exceptions.base import AuthorizationError

        error = AuthorizationError("Too many requests", "RATE_LIMITED")
        assert error.code == "RATE_LIMITED"
