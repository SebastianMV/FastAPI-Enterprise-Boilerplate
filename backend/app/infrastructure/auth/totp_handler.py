# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
TOTP (Time-based One-Time Password) handler for MFA.

Implements RFC 6238 TOTP algorithm using pyotp library.
Supports QR code generation for authenticator app setup.
"""

import base64
from io import BytesIO
from typing import Any

import pyotp
import qrcode  # type: ignore[import-untyped]
from qrcode.constants import ERROR_CORRECT_L  # type: ignore[import-untyped]

from app.config import settings


class TOTPHandler:
    """
    Handler for TOTP-based two-factor authentication.

    This class provides methods for:
    - Generating TOTP secrets
    - Verifying TOTP codes
    - Generating QR codes for authenticator app setup
    - Creating provisioning URIs

    Usage:
        handler = TOTPHandler()

        # Setup MFA for user
        secret = handler.generate_secret()
        qr_code = handler.generate_qr_code(secret, "user@example.com")

        # Verify code from user
        is_valid = handler.verify(secret, "123456")
    """

    # TOTP configuration
    DIGITS = 6
    INTERVAL = 30  # seconds
    VALID_WINDOW = 1  # Allow 1 interval before/after current

    def __init__(self, issuer: str | None = None) -> None:
        """
        Initialize the TOTP handler.

        Args:
            issuer: The issuer name shown in authenticator apps.
                   Defaults to APP_NAME from settings.
        """
        self._issuer = issuer or settings.APP_NAME

    @staticmethod
    def generate_secret() -> str:
        """
        Generate a new random TOTP secret.

        Returns:
            Base32-encoded secret string (32 characters)
        """
        return pyotp.random_base32()

    def verify(
        self,
        secret: str,
        code: str,
        *,
        valid_window: int | None = None,
    ) -> bool:
        """
        Verify a TOTP code against the secret.

        Args:
            secret: The user's TOTP secret
            code: The 6-digit code to verify
            valid_window: Number of intervals to check before/after current.
                         Defaults to VALID_WINDOW (1).

        Returns:
            True if the code is valid, False otherwise
        """
        if not secret or not code:
            return False

        # Clean up code (remove spaces/dashes)
        code = code.replace(" ", "").replace("-", "")

        if len(code) != self.DIGITS or not code.isdigit():
            return False

        window = valid_window if valid_window is not None else self.VALID_WINDOW

        totp = pyotp.TOTP(secret, digits=self.DIGITS, interval=self.INTERVAL)
        return totp.verify(code, valid_window=window)

    def get_current_code(self, secret: str) -> str:
        """
        Get the current TOTP code for a secret.

        This is mainly useful for testing purposes.

        Args:
            secret: The TOTP secret

        Returns:
            Current 6-digit TOTP code
        """
        totp = pyotp.TOTP(secret, digits=self.DIGITS, interval=self.INTERVAL)
        return totp.now()

    def get_provisioning_uri(self, secret: str, account_name: str) -> str:
        """
        Generate the provisioning URI for authenticator apps.

        This URI follows the otpauth:// format and can be encoded
        into a QR code for easy scanning.

        Args:
            secret: The TOTP secret
            account_name: User identifier (usually email)

        Returns:
            otpauth:// URI string
        """
        totp = pyotp.TOTP(secret, digits=self.DIGITS, interval=self.INTERVAL)
        return totp.provisioning_uri(name=account_name, issuer_name=self._issuer)

    def generate_qr_code(
        self,
        secret: str,
        account_name: str,
        *,
        size: int = 200,
        as_base64: bool = True,
    ) -> str | bytes:
        """
        Generate a QR code image for authenticator app setup.

        Args:
            secret: The TOTP secret
            account_name: User identifier (usually email)
            size: Image size in pixels (default 200x200)
            as_base64: If True, return base64-encoded string.
                      If False, return raw PNG bytes.

        Returns:
            Base64-encoded PNG string (with data URI prefix) or raw bytes
        """
        uri = self.get_provisioning_uri(secret, account_name)

        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img: Any = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size))

        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()

        if as_base64:
            b64 = base64.b64encode(png_bytes).decode("utf-8")
            return f"data:image/png;base64,{b64}"

        return png_bytes

    def generate_setup_data(
        self,
        account_name: str,
    ) -> tuple[str, str, str | bytes]:
        """
        Generate all data needed for MFA setup.

        Convenience method that generates a new secret along with
        the provisioning URI and QR code.

        Args:
            account_name: User identifier (usually email)

        Returns:
            Tuple of (secret, provisioning_uri, qr_code_base64)
        """
        secret = self.generate_secret()
        uri = self.get_provisioning_uri(secret, account_name)
        qr_code = self.generate_qr_code(secret, account_name)

        return secret, uri, qr_code


# Singleton instance
_totp_handler: TOTPHandler | None = None


def get_totp_handler() -> TOTPHandler:
    """Get the singleton TOTP handler instance."""
    global _totp_handler
    if _totp_handler is None:
        _totp_handler = TOTPHandler()
    return _totp_handler
