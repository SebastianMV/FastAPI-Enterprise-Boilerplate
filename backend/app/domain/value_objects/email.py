# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Email value object with validation."""

from dataclasses import dataclass
import re


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
    
    # RFC 5322 simplified email regex
    _PATTERN: re.Pattern = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    
    def __post_init__(self) -> None:
        """Validate email format after initialization."""
        if not self.value:
            raise ValueError("Email cannot be empty")
        
        normalized = self.value.lower().strip()
        
        if not self._PATTERN.match(normalized):
            raise ValueError(f"Invalid email format: {self.value}")
        
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
        if isinstance(other, str):
            return self.value == other.lower().strip()
        return False
