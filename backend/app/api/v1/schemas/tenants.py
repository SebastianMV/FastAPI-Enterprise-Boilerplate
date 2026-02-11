# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Pydantic schemas for Tenant endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TenantSettingsSchema(BaseModel):
    """Schema for tenant settings."""

    enable_2fa: bool = False
    enable_api_keys: bool = True
    enable_webhooks: bool = False
    max_users: int = Field(default=100, ge=1, le=10000)
    max_api_keys_per_user: int = Field(default=5, ge=1, le=100)
    max_storage_mb: int = Field(default=1024, ge=100, le=1000000)
    primary_color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    logo_url: str | None = Field(default=None, max_length=2048)
    password_min_length: int = Field(default=8, ge=6, le=128)
    session_timeout_minutes: int = Field(default=60, ge=5, le=10080)
    require_email_verification: bool = True


class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""

    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-friendly identifier (lowercase, hyphens allowed)",
    )
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    domain: str | None = Field(default=None, max_length=255)
    timezone: str = Field(default="UTC", max_length=50)
    locale: str = Field(default="en", max_length=10)
    plan: str = Field(
        default="free", pattern=r"^(free|starter|professional|enterprise)$"
    )
    settings: TenantSettingsSchema | None = None


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    domain: str | None = Field(default=None, max_length=255)
    timezone: str | None = Field(default=None, max_length=50)
    locale: str | None = Field(default=None, max_length=10)
    plan: str | None = Field(
        default=None,
        pattern=r"^(free|starter|professional|enterprise)$",
    )
    settings: TenantSettingsSchema | None = None


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    email: str | None = None
    phone: str | None = None
    is_active: bool
    is_verified: bool
    plan: str
    plan_expires_at: datetime | None = None
    settings: TenantSettingsSchema
    domain: str | None = None
    timezone: str
    locale: str
    created_at: datetime
    updated_at: datetime


class TenantListResponse(BaseModel):
    """Schema for paginated tenant list."""

    items: list[TenantResponse]
    total: int
    skip: int
    limit: int


class TenantActivateRequest(BaseModel):
    """Schema for activating/deactivating tenant."""

    is_active: bool


class TenantVerifyRequest(BaseModel):
    """Schema for verifying tenant."""

    is_verified: bool


class TenantPlanUpdate(BaseModel):
    """Schema for updating tenant plan."""

    plan: str = Field(..., pattern=r"^(free|starter|professional|enterprise)$")
    expires_at: datetime | None = None
