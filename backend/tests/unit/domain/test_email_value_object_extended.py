# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for Email value object - executing real code."""

from __future__ import annotations

import pytest


class TestEmailValueObject:
    """Tests for Email value object that execute real code."""

    def test_email_creation_valid(self) -> None:
        """Test creating email with valid value."""
        from app.domain.value_objects.email import Email

        email = Email("user@example.com")
        assert email.value == "user@example.com"

    def test_email_normalized_to_lowercase(self) -> None:
        """Test email is normalized to lowercase."""
        from app.domain.value_objects.email import Email

        email = Email("USER@EXAMPLE.COM")
        assert email.value == "user@example.com"

    def test_email_stripped(self) -> None:
        """Test email is stripped of whitespace."""
        from app.domain.value_objects.email import Email

        email = Email("  user@example.com  ")
        assert email.value == "user@example.com"

    def test_email_domain_property(self) -> None:
        """Test email domain property."""
        from app.domain.value_objects.email import Email

        email = Email("user@example.com")
        assert email.domain == "example.com"

    def test_email_local_part_property(self) -> None:
        """Test email local part property."""
        from app.domain.value_objects.email import Email

        email = Email("user@example.com")
        assert email.local_part == "user"

    def test_email_str(self) -> None:
        """Test email string representation."""
        from app.domain.value_objects.email import Email

        email = Email("user@example.com")
        assert str(email) == "user@example.com"

    def test_email_equality_with_email(self) -> None:
        """Test email equality with another Email."""
        from app.domain.value_objects.email import Email

        email1 = Email("user@example.com")
        email2 = Email("USER@EXAMPLE.COM")
        assert email1 == email2

    def test_email_equality_with_string(self) -> None:
        """Test email equality with string."""
        from app.domain.value_objects.email import Email

        email = Email("user@example.com")
        assert email == "user@example.com"
        assert email == "USER@EXAMPLE.COM"

    def test_email_invalid_empty(self) -> None:
        """Test email validation rejects empty string."""
        from app.domain.value_objects.email import Email

        with pytest.raises(ValueError, match="Email cannot be empty"):
            Email("")

    def test_email_invalid_format_no_at(self) -> None:
        """Test email validation rejects no @ symbol."""
        from app.domain.value_objects.email import Email

        with pytest.raises(ValueError, match="Invalid email format"):
            Email("userexample.com")

    def test_email_invalid_format_no_domain(self) -> None:
        """Test email validation rejects no domain."""
        from app.domain.value_objects.email import Email

        with pytest.raises(ValueError, match="Invalid email format"):
            Email("user@")

    def test_email_invalid_format_no_tld(self) -> None:
        """Test email validation rejects no TLD."""
        from app.domain.value_objects.email import Email

        with pytest.raises(ValueError, match="Invalid email format"):
            Email("user@example")

    def test_email_valid_with_plus(self) -> None:
        """Test email validation accepts plus addressing."""
        from app.domain.value_objects.email import Email

        email = Email("user+tag@example.com")
        assert email.value == "user+tag@example.com"

    def test_email_valid_with_dots(self) -> None:
        """Test email validation accepts dots in local part."""
        from app.domain.value_objects.email import Email

        email = Email("first.last@example.com")
        assert email.value == "first.last@example.com"

    def test_email_valid_subdomain(self) -> None:
        """Test email validation accepts subdomain."""
        from app.domain.value_objects.email import Email

        email = Email("user@mail.example.com")
        assert email.domain == "mail.example.com"

    def test_email_inequality_with_different_email(self) -> None:
        """Test email inequality with different email."""
        from app.domain.value_objects.email import Email

        email1 = Email("user1@example.com")
        email2 = Email("user2@example.com")
        assert email1 != email2

    def test_email_inequality_with_non_email_type(self) -> None:
        """Test email inequality with non-email type."""
        from app.domain.value_objects.email import Email

        email = Email("user@example.com")
        assert email != 123
        assert email != None
