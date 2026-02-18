# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for Email value object."""

import pytest

from app.domain.exceptions.base import ValidationError as DomainValidationError
from app.domain.value_objects.email import Email


class TestEmail:
    """Tests for Email value object."""

    def test_valid_email_creation(self):
        """Test creating valid email addresses."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@subdomain.example.com",
            "123@example.com",
        ]

        for email_str in valid_emails:
            email = Email(email_str)
            assert email.value == email_str.lower()

    def test_email_normalization(self):
        """Test that emails are normalized to lowercase."""
        email = Email("USER@EXAMPLE.COM")
        assert email.value == "user@example.com"

    def test_email_whitespace_trimming(self):
        """Test that whitespace is trimmed."""
        email = Email("  user@example.com  ")
        assert email.value == "user@example.com"

    def test_invalid_email_empty(self):
        """Test that empty email raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="cannot be empty"
        ):
            Email("")

    def test_invalid_email_no_at_sign(self):
        """Test that email without @ raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="Invalid email format"
        ):
            Email("userexample.com")

    def test_invalid_email_no_domain(self):
        """Test that email without domain raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="Invalid email format"
        ):
            Email("user@")

    def test_invalid_email_no_tld(self):
        """Test that email without TLD raises ValueError."""
        with pytest.raises(
            (ValueError, DomainValidationError), match="Invalid email format"
        ):
            Email("user@example")

    def test_email_domain_property(self):
        """Test domain extraction."""
        email = Email("user@example.com")
        assert email.domain == "example.com"

    def test_email_local_part_property(self):
        """Test local part extraction."""
        email = Email("user.name@example.com")
        assert email.local_part == "user.name"

    def test_email_string_representation(self):
        """Test str() returns email value."""
        email = Email("user@example.com")
        assert str(email) == "user@example.com"

    def test_email_equality_with_email(self):
        """Test equality between Email objects."""
        email1 = Email("user@example.com")
        email2 = Email("USER@EXAMPLE.COM")
        assert email1 == email2

    def test_email_equality_with_string(self):
        """Test equality with string by wrapping in Email."""
        email = Email("user@example.com")
        assert email == Email("user@example.com")
        assert email == Email("USER@EXAMPLE.COM")

    def test_email_immutability(self):
        """Test that Email is immutable."""
        email = Email("user@example.com")
        with pytest.raises(AttributeError):
            email.value = "other@example.com"
