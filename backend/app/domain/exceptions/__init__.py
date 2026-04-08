# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

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
