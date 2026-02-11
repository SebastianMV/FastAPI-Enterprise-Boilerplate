# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Multi-Factor Authentication (MFA) domain entity.

Represents TOTP-based two-factor authentication configuration for users.
"""

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class MFAConfig:
    """
    MFA configuration for a user.

    Stores the TOTP secret and backup codes for two-factor authentication.
    The secret should be encrypted at rest in the database.

    Attributes:
        id: Unique identifier
        user_id: Associated user ID
        secret: TOTP secret key (base32 encoded)
        is_enabled: Whether MFA is currently active
        backup_codes: List of one-time use backup codes
        created_at: When MFA was first configured
        enabled_at: When MFA was enabled
        last_used_at: Last successful MFA verification
    """

    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    secret: str = ""
    is_enabled: bool = False
    backup_codes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    enabled_at: datetime | None = None
    last_used_at: datetime | None = None

    @staticmethod
    def generate_backup_codes(count: int = 10) -> list[str]:
        """
        Generate a list of backup codes.

        Each backup code is a random 8-character alphanumeric string.
        These can be used as one-time passwords if the user loses
        access to their authenticator app.

        Args:
            count: Number of backup codes to generate

        Returns:
            List of backup code strings
        """
        codes = []
        for _ in range(count):
            # Generate 8 random characters (letters and digits)
            code = secrets.token_hex(4).upper()  # 8 hex characters
            codes.append(code)
        return codes

    def use_backup_code(self, code: str) -> bool:
        """
        Attempt to use a backup code.

        If the code is valid, it will be removed from the list
        (backup codes are single-use).

        Args:
            code: The backup code to verify

        Returns:
            True if the code was valid and used, False otherwise
        """
        import hmac

        code_upper = code.upper().replace("-", "").replace(" ", "")
        # Constant-time comparison to prevent timing side-channel attacks
        matched = None
        for stored in self.backup_codes:
            if hmac.compare_digest(code_upper, stored):
                matched = stored
                break
        if matched:
            self.backup_codes.remove(matched)
            self.last_used_at = datetime.now(UTC)
            return True
        return False

    def regenerate_backup_codes(self) -> list[str]:
        """
        Generate new backup codes, replacing the old ones.

        Returns:
            The newly generated backup codes
        """
        self.backup_codes = self.generate_backup_codes()
        return self.backup_codes

    def enable(self) -> None:
        """Enable MFA for the user."""
        self.is_enabled = True
        self.enabled_at = datetime.now(UTC)

    def disable(self) -> None:
        """Disable MFA for the user."""
        self.is_enabled = False
        self.enabled_at = None

    def record_use(self) -> None:
        """Record that MFA was successfully used."""
        self.last_used_at = datetime.now(UTC)

    @property
    def remaining_backup_codes(self) -> int:
        """Get the number of remaining backup codes."""
        return len(self.backup_codes)
