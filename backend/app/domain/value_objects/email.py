# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Email value object with validation."""

import re
from dataclasses import dataclass
from typing import ClassVar

from app.domain.exceptions.base import ValidationError as DomainValidationError


@dataclass(frozen=True)
class Email:
    """
    Email value object.

    Immutable value object that validates email format on creation.

    Example:
        >>> email = Email("user@example.com")
        >>> email.value
        'user@example.com'
        >>> email.domain
        'example.com'
    """

    value: str

    # RFC 5322 simplified email regex — ClassVar prevents constructor override
    _PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    def __post_init__(self) -> None:
        """Validate email format after initialization."""
        if not self.value:
            raise DomainValidationError(
                message="Email cannot be empty",
                field="email",
            )

        normalized = self.value.lower().strip()

        if not self._PATTERN.match(normalized):
            raise DomainValidationError(
                message="Invalid email format",
                field="email",
            )

        # Use object.__setattr__ since dataclass is frozen
        object.__setattr__(self, "value", normalized)

    @property
    def domain(self) -> str:
        """Extract domain from email address."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Extract local part (before @) from email address."""
        return self.value.split("@")[0]

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Compare emails case-insensitively."""
        if isinstance(other, Email):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        """Hash by normalized email value."""
        return hash(self.value)
