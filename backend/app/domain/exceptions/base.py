# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Base domain exceptions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DomainException(Exception):
    """
    Base exception for domain layer errors.

    All domain exceptions should inherit from this class.
    """

    message: str
    code: str = "DOMAIN_ERROR"
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation of the exception."""
        return self.message


@dataclass
class EntityNotFoundError(DomainException):
    """Raised when an entity is not found."""

    message: str = ""
    entity_type: str = ""
    entity_id: str = ""
    code: str = "ENTITY_NOT_FOUND"

    def __post_init__(self) -> None:
        """Set message based on entity info."""
        if not self.message:
            self.message = f"{self.entity_type} not found"


@dataclass
class ValidationError(DomainException):
    """Raised when validation fails."""

    field: str = ""
    code: str = "VALIDATION_ERROR"


@dataclass
class BusinessRuleViolationError(DomainException):
    """Raised when a business rule is violated."""

    rule: str = ""
    code: str = "BUSINESS_RULE_VIOLATION"


@dataclass
class AuthenticationError(DomainException):
    """Raised when authentication fails."""

    code: str = "AUTHENTICATION_FAILED"


@dataclass
class AuthorizationError(DomainException):
    """Raised when authorization fails."""

    resource: str = ""
    action: str = ""
    code: str = "AUTHORIZATION_DENIED"

    def __post_init__(self) -> None:
        """Set message based on resource and action."""
        if not self.message:
            self.message = "Insufficient permissions"


@dataclass
class ConflictError(DomainException):
    """Raised when there's a conflict (e.g., duplicate entity)."""

    conflicting_field: str = ""
    code: str = "CONFLICT"


@dataclass
class RateLimitExceededError(DomainException):
    """Raised when rate limit is exceeded."""

    retry_after_seconds: int = 60
    code: str = "RATE_LIMIT_EXCEEDED"

    def __post_init__(self) -> None:
        """Set message with retry info."""
        if not self.message:
            self.message = "Rate limit exceeded. Please try again later."


@dataclass
class ServiceUnavailableError(DomainException):
    """Raised when a required infrastructure service is unavailable."""

    service: str = ""
    code: str = "SERVICE_UNAVAILABLE"

    def __post_init__(self) -> None:
        """Set message with service info."""
        if not self.message:
            self.message = "Service temporarily unavailable. Please try again later."
