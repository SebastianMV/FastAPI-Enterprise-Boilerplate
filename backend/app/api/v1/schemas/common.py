# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Common schemas shared across endpoints."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error detail in response."""
    
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    field: str | None = Field(None, description="Field that caused the error")


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: ErrorDetail
    request_id: str | None = Field(None, description="Request ID for debugging")


class ValidationErrorResponse(BaseModel):
    """Validation error response with multiple errors."""
    
    errors: list[ErrorDetail]
    request_id: str | None = None


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
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    
    # Optional component health
    database: str | None = Field(None, description="Database connection status")
    redis: str | None = Field(None, description="Redis connection status")


class MessageResponse(BaseModel):
    """Simple message response."""
    
    message: str
    success: bool = True
    data: dict[str, Any] | None = None
