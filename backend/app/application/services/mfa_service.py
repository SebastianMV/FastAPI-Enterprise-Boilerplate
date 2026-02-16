# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
MFA (Multi-Factor Authentication) Service.

Handles MFA setup, verification, and management.
"""

from uuid import UUID

from app.domain.entities.mfa import BACKUP_CODE_LENGTH, MFAConfig
from app.infrastructure.auth.totp_handler import TOTPHandler, get_totp_handler
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class MFAService:
    """
    Service for managing Multi-Factor Authentication.

    Provides high-level operations for:
    - Setting up MFA for users
    - Verifying TOTP codes
    - Managing backup codes
    - Enabling/disabling MFA

    Usage:
        service = MFAService()

        # Setup MFA
        secret, qr_code, backup_codes = await service.setup_mfa(
            user_id=user.id,
            email=user.email
        )

        # Verify during login
        is_valid = service.verify_code(mfa_config, "123456")
    """

    def __init__(self, totp_handler: TOTPHandler | None = None) -> None:
        """
        Initialize the MFA service.

        Args:
            totp_handler: TOTP handler instance. Defaults to singleton.
        """
        self._totp = totp_handler or get_totp_handler()

    def setup_mfa(
        self, user_id: UUID, email: str
    ) -> tuple[MFAConfig, str | bytes, str]:
        """
        Initialize MFA setup for a user.

        Generates a new TOTP secret, QR code, and backup codes.
        The MFA is not enabled yet - user must verify a code first.

        Args:
            user_id: The user's ID
            email: The user's email (shown in authenticator app)

        Returns:
            Tuple of (MFAConfig, qr_code_base64, provisioning_uri)
        """
        # Generate TOTP setup data
        secret, uri, qr_code = self._totp.generate_setup_data(email)

        # Generate backup codes
        backup_codes = MFAConfig.generate_backup_codes(count=10)

        # Create MFA config (not enabled yet)
        config = MFAConfig(
            user_id=user_id,
            secret=secret,
            is_enabled=False,
            backup_codes=backup_codes,
        )

        return config, qr_code, uri

    def verify_code(
        self,
        config: MFAConfig,
        code: str,
        *,
        allow_backup: bool = True,
    ) -> tuple[bool, bool]:
        """
        Verify a TOTP or backup code.

        Args:
            config: The user's MFA configuration
            code: The code to verify (TOTP or backup)
            allow_backup: Whether to check backup codes

        Returns:
            Tuple of (is_valid, was_backup_code)
        """
        if not config.is_enabled:
            return False, False

        # Clean up code
        code = code.replace(" ", "").replace("-", "")

        # Try TOTP verification first
        if self._totp.verify(config.secret, code):
            config.record_use()
            return True, False

        # Try backup code if allowed
        if allow_backup and len(code) == BACKUP_CODE_LENGTH:
            if config.use_backup_code(code):
                return True, True

        return False, False

    def verify_setup_code(self, config: MFAConfig, code: str) -> bool:
        """
        Verify the initial setup code and enable MFA.

        This should be called after setup_mfa() to verify the user
        has correctly configured their authenticator app.

        Args:
            config: The MFA configuration from setup
            code: The verification code from the authenticator app

        Returns:
            True if verification succeeded and MFA is now enabled
        """
        if config.is_enabled:
            return False  # Already enabled

        if self._totp.verify(config.secret, code):
            config.enable()
            return True

        return False

    def regenerate_backup_codes(self, config: MFAConfig) -> list[str]:
        """
        Generate new backup codes for a user.

        This invalidates all previous backup codes.

        Args:
            config: The user's MFA configuration

        Returns:
            List of new backup codes
        """
        return config.regenerate_backup_codes()

    def disable_mfa(self, config: MFAConfig, code: str) -> bool:
        """
        Disable MFA after verifying a code.

        Requires a valid TOTP code for security.

        Args:
            config: The user's MFA configuration
            code: TOTP code for verification

        Returns:
            True if MFA was disabled, False if code was invalid
        """
        # Verify code first (don't allow backup codes for disabling)
        if self._totp.verify(config.secret, code):
            config.disable()
            return True

        return False

    def get_remaining_backup_codes(self, config: MFAConfig) -> int:
        """
        Get the number of remaining backup codes.

        Args:
            config: The user's MFA configuration

        Returns:
            Number of unused backup codes
        """
        return config.remaining_backup_codes


# Singleton instance
_mfa_service: MFAService | None = None


def get_mfa_service() -> MFAService:
    """Get the singleton MFA service instance."""
    global _mfa_service
    if _mfa_service is None:
        _mfa_service = MFAService()
    return _mfa_service
