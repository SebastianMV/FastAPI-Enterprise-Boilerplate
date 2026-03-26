# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Unit tests for Password value object."""

import pytest

from app.domain.exceptions.base import ValidationError as DomainValidationError
from app.domain.value_objects.password import Password


class TestPassword:
    """Tests for Password value object."""

    def test_valid_password_creation(self):
        """Test creating valid passwords."""
        valid_passwords = [
            "SecureP@ss123",
            "MyP@ssw0rd!",
            "Complex#Pass1",
            "Test123!@#abc",
        ]

        for pwd in valid_passwords:
            password = Password(pwd)
            assert password.value == pwd

    def test_password_too_short(self):
        """Test that short password raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("Ab1!xyz")

    def test_password_too_long(self):
        """Test that very long password raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("A" * 100 + "a1!" + "x" * 30)

    def test_password_missing_uppercase(self):
        """Test that password without uppercase raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("lowercase1!")

    def test_password_missing_lowercase(self):
        """Test that password without lowercase raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("UPPERCASE1!")

    def test_password_missing_digit(self):
        """Test that password without digit raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("NoDigits!")

    def test_password_missing_special(self):
        """Test that password without special char raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("NoSpecial123")

    def test_password_multiple_errors(self):
        """Test that multiple validation errors are combined."""
        with pytest.raises((ValueError, DomainValidationError)) as exc_info:
            Password("weak")

        error_message = str(exc_info.value)
        assert "security requirements" in error_message

    def test_password_string_never_exposed(self):
        """Test that str() never exposes the password."""
        password = Password("SecureP@ss123")
        assert "SecureP@ss123" not in str(password)
        assert "********" in str(password)

    def test_password_repr_never_exposed(self):
        """Test that repr() never exposes the password."""
        password = Password("SecureP@ss123")
        assert "SecureP@ss123" not in repr(password)
        assert "********" in repr(password)

    def test_password_requirements(self):
        """Test getting password requirements for UI."""
        requirements = Password.get_requirements()

        assert "min_length" in requirements
        assert "uppercase" in requirements
        assert "lowercase" in requirements
        assert "digit" in requirements
        assert "special" in requirements

    def test_password_immutability(self):
        """Test that Password is immutable."""
        password = Password("SecureP@ss123")
        with pytest.raises(AttributeError):
            password.value = "OtherP@ss456"
