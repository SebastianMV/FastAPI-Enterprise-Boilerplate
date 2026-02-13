# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Password value object with security validation."""

import re
from dataclasses import dataclass
from typing import ClassVar

from app.domain.exceptions.base import ValidationError as DomainValidationError


@dataclass(frozen=True)
class Password:
    """
    Password value object with security requirements.

    Validates password strength on creation:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Example:
        >>> password = Password("SecureP@ss123")
        >>> password.value
        'SecureP@ss123'
    """

    value: str

    MIN_LENGTH: ClassVar[int] = 8
    MAX_LENGTH: ClassVar[int] = 128

    def __post_init__(self) -> None:
        """Validate password strength after initialization."""
        errors = self._validate()
        if errors:
            raise DomainValidationError(
                message="Password does not meet security requirements",
                field="password",
            )

    def _validate(self) -> list[str]:
        """
        Validate password against security requirements.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if len(self.value) < self.MIN_LENGTH:
            errors.append(f"Must be at least {self.MIN_LENGTH} characters")

        if len(self.value) > self.MAX_LENGTH:
            errors.append(f"Must be at most {self.MAX_LENGTH} characters")

        if not re.search(r"[A-Z]", self.value):
            errors.append("Must contain at least one uppercase letter")

        if not re.search(r"[a-z]", self.value):
            errors.append("Must contain at least one lowercase letter")

        if not re.search(r"\d", self.value):
            errors.append("Must contain at least one digit")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", self.value):
            errors.append("Must contain at least one special character")

        return errors

    @classmethod
    def get_requirements(cls) -> dict[str, str]:
        """Get password requirements for UI display."""
        return {
            "min_length": f"At least {cls.MIN_LENGTH} characters",
            "uppercase": "At least one uppercase letter",
            "lowercase": "At least one lowercase letter",
            "digit": "At least one number",
            "special": "At least one special character (!@#$%^&*...)",
        }

    def __str__(self) -> str:
        """Never expose password in string representation."""
        return "********"

    def __repr__(self) -> str:
        """Never expose password in repr."""
        return "Password(********)"
