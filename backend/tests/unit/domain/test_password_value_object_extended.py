# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for Password value object - executing real code."""

from __future__ import annotations

import pytest

from app.domain.exceptions.base import ValidationError as DomainValidationError


class TestPasswordValueObject:
    """Tests for Password value object that execute real code."""

    def test_password_creation_valid(self) -> None:
        """Test creating password with valid value."""
        from app.domain.value_objects.password import Password

        password = Password("SecureP@ss123")
        assert password.value == "SecureP@ss123"

    def test_password_too_short(self) -> None:
        """Test password validation rejects too short."""
        from app.domain.value_objects.password import Password

        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("Short1!")

    def test_password_no_uppercase(self) -> None:
        """Test password validation rejects no uppercase."""
        from app.domain.value_objects.password import Password

        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("lowercase1@")

    def test_password_no_lowercase(self) -> None:
        """Test password validation rejects no lowercase."""
        from app.domain.value_objects.password import Password

        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("UPPERCASE1@")

    def test_password_no_digit(self) -> None:
        """Test password validation rejects no digit."""
        from app.domain.value_objects.password import Password

        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("NoDigits@@@")

    def test_password_no_special(self) -> None:
        """Test password validation rejects no special character."""
        from app.domain.value_objects.password import Password

        with pytest.raises(
            (ValueError, DomainValidationError), match="security requirements"
        ):
            Password("NoSpecial123")

    def test_password_get_requirements(self) -> None:
        """Test password requirements method."""
        from app.domain.value_objects.password import Password

        requirements = Password.get_requirements()
        assert "min_length" in requirements
        assert "uppercase" in requirements
        assert "lowercase" in requirements
        assert "digit" in requirements
        assert "special" in requirements

    def test_password_str_hides_value(self) -> None:
        """Test password string representation hides value."""
        from app.domain.value_objects.password import Password

        password = Password("SecureP@ss123")
        str_repr = str(password)
        # Should not expose the actual password
        assert (
            "SecureP@ss123" not in str_repr
            or "***" in str_repr
            or str_repr == "Password(***)"
        )

    def test_password_min_length_constant(self) -> None:
        """Test password min length constant."""
        from app.domain.value_objects.password import Password

        assert Password.MIN_LENGTH == 8

    def test_password_max_length_constant(self) -> None:
        """Test password max length constant."""
        from app.domain.value_objects.password import Password

        assert Password.MAX_LENGTH == 128

    def test_password_valid_with_all_special_chars(self) -> None:
        """Test password with various special characters."""
        from app.domain.value_objects.password import Password

        # Test with different special characters
        passwords = [
            "SecureP!ss123",
            "SecureP@ss123",
            "SecureP#ss123",
            "SecureP$ss123",
            "SecureP%ss123",
        ]
        for pwd in passwords:
            password = Password(pwd)
            assert password.value == pwd

    def test_password_exactly_min_length(self) -> None:
        """Test password with exactly minimum length."""
        from app.domain.value_objects.password import Password

        password = Password("Aa1!aaaa")  # Exactly 8 characters
        assert len(password.value) == 8

    def test_password_multiple_errors(self) -> None:
        """Test password with multiple validation errors."""
        from app.domain.value_objects.password import Password

        with pytest.raises((ValueError, DomainValidationError)) as exc_info:
            Password("short")

        error_msg = str(exc_info.value)
        # Should contain generic error message
        assert "security requirements" in error_msg.lower()
