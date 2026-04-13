# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Common schemas shared across endpoints."""

from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# =============================================================================
# Constrained type aliases — use these instead of raw `str` in schemas.
#
# From Audit 24 retrospective: ~40 fixes were missing max_length on Pydantic
# fields. These reusable aliases ensure constraints by default, making it
# harder to forget validation on new schemas.
#
# Usage:
#   class MySchema(BaseModel):
#       name: NameStr          # max 200 chars
#       description: TextStr   # max 2000 chars
#       code: ShortStr         # max 50 chars
#       email: EmailStr        # from pydantic (already constrained)
# =============================================================================

ShortStr = Annotated[str, Field(min_length=1, max_length=50)]
"""Short identifier strings (codes, slugs, enum-like values). Max 50 chars."""

NameStr = Annotated[str, Field(min_length=1, max_length=200)]
"""Names (user names, role names, resource names). Max 200 chars."""

TextStr = Annotated[str, Field(max_length=2000)]
"""Longer text (descriptions, notes, comments). Max 2000 chars."""

LargeTextStr = Annotated[str, Field(max_length=50000)]
"""Very long text/blob fields (e.g. base64 payloads). Max 50000 chars."""

UrlStr = Annotated[str, Field(max_length=2048)]
"""URL strings (callback URLs, logo URLs, webhook URLs). Max 2048 chars."""

TokenStr = Annotated[str, Field(min_length=1, max_length=2048)]
"""Token/secret strings (JWT, API keys, CSRF tokens). Max 2048 chars."""

ScopeStr = Annotated[str, Field(max_length=100)]
"""Permission scope strings (e.g. 'users:read'). Max 100 chars."""

LongNameStr = Annotated[str, Field(min_length=1, max_length=255)]
"""Long names (tenant names, API key names, domains). Max 255 chars."""

RoleNameStr = Annotated[str, Field(min_length=1, max_length=100)]
"""Role names. Max 100 chars."""

DescriptionStr = Annotated[str, Field(max_length=500)]
"""Descriptions (role descriptions, notes). Max 500 chars."""

PasswordStr = Annotated[str, Field(min_length=8, max_length=128)]
"""Password strings. Min 8, max 128 chars."""


class ErrorDetail(BaseModel):
    """Error detail in response."""

    code: ShortStr = Field(..., description="Error code")
    message: DescriptionStr = Field(..., description="Human-readable error message")
    field: NameStr | None = Field(None, description="Field that caused the error")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail
    request_id: ScopeStr | None = Field(None, description="Request ID for debugging")


class ValidationErrorResponse(BaseModel):
    """Validation error response with multiple errors."""

    errors: list[ErrorDetail]
    request_id: ScopeStr | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Create paginated response with calculated pages."""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


class HealthResponse(BaseModel):
    """Basic health check response for /health and /health/live."""

    status: ShortStr = Field(..., description="Service status")
    version: ShortStr | None = Field(
        None, description="Application version (hidden in production)"
    )
    environment: ShortStr | None = Field(
        None, description="Deployment environment (hidden in production)"
    )


class ReadinessResponse(HealthResponse):
    """Readiness check response for /health/ready — includes component health."""

    database: ShortStr = Field(..., description="Database connection status")
    redis: ShortStr = Field(..., description="Redis connection status")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: DescriptionStr
    success: bool = True
    data: dict[str, Any] | None = None
