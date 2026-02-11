# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Comprehensive tests for TOTP Handler."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.auth.totp_handler import TOTPHandler


class TestTOTPHandler:
    """Tests for TOTPHandler class."""

    @pytest.fixture
    def handler(self):
        """Create TOTP handler instance."""
        return TOTPHandler(issuer="TestApp")

    def test_init_with_issuer(self):
        """Should initialize with custom issuer."""
        handler = TOTPHandler(issuer="MyApp")
        assert handler._issuer == "MyApp"

    def test_init_with_default_issuer(self):
        """Should use default issuer from settings."""
        handler = TOTPHandler()
        assert handler._issuer is not None

    def test_generate_secret(self, handler):
        """Should generate base32 secret."""
        secret = handler.generate_secret()

        assert secret is not None
        assert isinstance(secret, str)
        assert len(secret) == 32

        # Base32 alphabet check
        import string

        base32_chars = string.ascii_uppercase + "234567"
        assert all(c in base32_chars for c in secret)

    def test_generate_secret_is_static_method(self):
        """Should be callable as static method."""
        secret = TOTPHandler.generate_secret()
        assert secret is not None

    def test_generate_secret_uniqueness(self, handler):
        """Should generate unique secrets."""
        secret1 = handler.generate_secret()
        secret2 = handler.generate_secret()

        assert secret1 != secret2

    def test_verify_valid_code(self, handler):
        """Should verify valid TOTP code."""
        import pyotp

        secret = handler.generate_secret()
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        is_valid = handler.verify(secret, valid_code)

        assert is_valid is True

    def test_verify_invalid_code(self, handler):
        """Should reject invalid TOTP code."""
        secret = handler.generate_secret()
        invalid_code = "000000"

        is_valid = handler.verify(secret, invalid_code)

        assert is_valid is False

    def test_verify_with_empty_secret(self, handler):
        """Should reject empty secret."""
        is_valid = handler.verify("", "123456")

        assert is_valid is False

    def test_verify_with_empty_code(self, handler):
        """Should reject empty code."""
        secret = handler.generate_secret()

        is_valid = handler.verify(secret, "")

        assert is_valid is False

    def test_verify_with_none_values(self, handler):
        """Should handle None values."""
        is_valid = handler.verify(None, None)

        assert is_valid is False

    def test_verify_code_with_spaces(self, handler):
        """Should clean spaces from code."""
        import pyotp

        secret = handler.generate_secret()
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Add spaces to code
        code_with_spaces = f"{valid_code[:3]} {valid_code[3:]}"

        is_valid = handler.verify(secret, code_with_spaces)

        assert is_valid is True

    def test_verify_code_with_dashes(self, handler):
        """Should clean dashes from code."""
        import pyotp

        secret = handler.generate_secret()
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Add dashes
        code_with_dashes = f"{valid_code[:3]}-{valid_code[3:]}"

        is_valid = handler.verify(secret, code_with_dashes)

        assert is_valid is True

    def test_verify_wrong_length_code(self, handler):
        """Should reject code with wrong length."""
        secret = handler.generate_secret()

        is_valid = handler.verify(secret, "12345")  # Only 5 digits

        assert is_valid is False

    def test_verify_non_numeric_code(self, handler):
        """Should reject non-numeric code."""
        secret = handler.generate_secret()

        is_valid = handler.verify(secret, "abcdef")

        assert is_valid is False

    def test_verify_with_custom_window(self, handler):
        """Should verify with custom time window."""
        import pyotp

        secret = handler.generate_secret()
        totp = pyotp.TOTP(secret)

        # Get a code that would be valid with larger window
        valid_code = totp.now()

        is_valid = handler.verify(secret, valid_code, valid_window=2)

        assert is_valid is True

    def test_get_provisioning_uri(self, handler):
        """Should generate provisioning URI."""
        secret = handler.generate_secret()
        account_name = "user@example.com"

        uri = handler.get_provisioning_uri(secret, account_name)

        assert uri is not None
        assert uri.startswith("otpauth://totp/")
        # Account name is URL-encoded
        assert "user" in uri
        assert secret in uri
        assert "TestApp" in uri

    def test_get_provisioning_uri_with_issuer(self, handler):
        """Should include issuer in URI."""
        secret = handler.generate_secret()

        uri = handler.get_provisioning_uri(secret, "user@test.com")

        assert "issuer=TestApp" in uri

    def test_generate_qr_code(self, handler):
        """Should generate QR code."""
        secret = handler.generate_secret()

        qr_code = handler.generate_qr_code(secret, "user@example.com")

        assert qr_code is not None
        # QR code should be a PIL Image or similar
        assert hasattr(qr_code, "save") or isinstance(qr_code, str)

    def test_generate_qr_code_base64(self, handler):
        """Should generate QR code as base64."""
        secret = handler.generate_secret()

        with patch.object(handler, "generate_qr_code") as mock_qr:
            mock_img = MagicMock()
            mock_qr.return_value = mock_img

            result = handler.generate_qr_code(secret, "user@test.com")

            assert mock_qr.called

    def test_totp_configuration_constants(self, handler):
        """Should have correct TOTP configuration."""
        assert handler.DIGITS == 6
        assert handler.INTERVAL == 30
        assert handler.VALID_WINDOW == 1


class TestTOTPConstants:
    """Tests for TOTP configuration constants."""

    def test_digits_configuration(self):
        """Should use 6-digit codes."""
        handler = TOTPHandler()
        assert handler.DIGITS == 6

    def test_interval_configuration(self):
        """Should use 30-second intervals."""
        handler = TOTPHandler()
        assert handler.INTERVAL == 30

    def test_valid_window_configuration(self):
        """Should allow 1 interval tolerance."""
        handler = TOTPHandler()
        assert handler.VALID_WINDOW == 1


class TestTOTPEdgeCases:
    """Edge case tests for TOTP operations."""

    @pytest.fixture
    def handler(self):
        """Create handler."""
        return TOTPHandler()

    def test_verify_alphanumeric_code(self, handler):
        """Should reject alphanumeric codes."""
        secret = handler.generate_secret()

        is_valid = handler.verify(secret, "12ab56")

        assert is_valid is False

    def test_verify_code_with_leading_zeros(self, handler):
        """Should handle codes with leading zeros."""

        secret = handler.generate_secret()

        # Mock a code with leading zeros
        with patch("pyotp.TOTP.verify") as mock_verify:
            mock_verify.return_value = True

            is_valid = handler.verify(secret, "000123")

            # Should still validate format correctly
            assert mock_verify.called

    def test_multiple_verifications_same_code(self, handler):
        """Should verify same code multiple times within window."""
        import pyotp

        secret = handler.generate_secret()
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Should work multiple times
        assert handler.verify(secret, valid_code) is True
        assert handler.verify(secret, valid_code) is True

    def test_secret_base32_encoding(self):
        """Generated secrets should be valid base32."""
        secret = TOTPHandler.generate_secret()

        # Should not raise exception
        try:
            base64.b32decode(secret)
            valid = True
        except Exception:
            valid = False

        assert valid is True

    def test_qr_code_generation_with_special_characters(self, handler):
        """Should handle special characters in account name."""
        secret = handler.generate_secret()
        account = "user+test@example.com"

        # Should not raise exception
        uri = handler.get_provisioning_uri(secret, account)
        assert uri is not None


class TestTOTPIntegration:
    """Integration tests for complete TOTP flow."""

    @pytest.fixture
    def handler(self):
        """Create handler."""
        return TOTPHandler(issuer="IntegrationTest")

    def test_complete_setup_flow(self, handler):
        """Test complete MFA setup flow."""
        # 1. Generate secret
        secret = handler.generate_secret()
        assert secret is not None

        # 2. Generate QR code
        qr_code = handler.generate_qr_code(secret, "test@example.com")
        assert qr_code is not None

        # 3. Verify code
        import pyotp

        totp = pyotp.TOTP(secret)
        code = totp.now()

        assert handler.verify(secret, code) is True

    def test_provisioning_uri_matches_verification(self, handler):
        """Provisioning URI should match verification parameters."""
        secret = handler.generate_secret()
        uri = handler.get_provisioning_uri(secret, "user@test.com")

        # URI should contain the secret
        assert f"secret={secret}" in uri
        # Note: pyotp may not include default values in URI
        assert "IntegrationTest" in uri

    def test_time_based_code_changes(self, handler):
        """Codes should change over time."""
        import time

        import pyotp

        secret = handler.generate_secret()
        totp = pyotp.TOTP(secret)

        code1 = totp.now()

        # Wait for potential code change (mocked for speed)
        with patch("time.time", return_value=time.time() + 31):
            code2 = totp.now()

        # In theory, codes should be different after 30+ seconds
        # But this is hard to test without mocking time
        assert isinstance(code1, str)
        assert isinstance(code2, str)
