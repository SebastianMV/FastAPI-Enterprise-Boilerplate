# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Domain exceptions package."""

from app.domain.exceptions.base import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolationError,
    ConflictError,
    DomainException,
    EntityNotFoundError,
    RateLimitExceededError,
    ServiceUnavailableError,
    ValidationError,
)

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "BusinessRuleViolationError",
    "ConflictError",
    "DomainException",
    "EntityNotFoundError",
    "RateLimitExceededError",
    "ServiceUnavailableError",
    "ValidationError",
]
