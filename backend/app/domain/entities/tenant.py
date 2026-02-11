# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tenant entity for multi-tenant support."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.entities.base import AuditableEntity


@dataclass
class TenantSettings:
    """Tenant-specific settings."""

    # Feature flags
    enable_2fa: bool = False
    enable_api_keys: bool = True
    enable_webhooks: bool = False

    # Limits
    max_users: int = 100
    max_api_keys_per_user: int = 5
    max_storage_mb: int = 1024

    # Branding
    primary_color: str = "#3B82F6"
    logo_url: str | None = None

    # Security
    password_min_length: int = 8
    session_timeout_minutes: int = 60
    require_email_verification: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "enable_2fa": self.enable_2fa,
            "enable_api_keys": self.enable_api_keys,
            "enable_webhooks": self.enable_webhooks,
            "max_users": self.max_users,
            "max_api_keys_per_user": self.max_api_keys_per_user,
            "max_storage_mb": self.max_storage_mb,
            "primary_color": self.primary_color,
            "logo_url": self.logo_url,
            "password_min_length": self.password_min_length,
            "session_timeout_minutes": self.session_timeout_minutes,
            "require_email_verification": self.require_email_verification,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TenantSettings":
        """Create from dictionary with validated ranges."""
        return cls(
            enable_2fa=data.get("enable_2fa", False),
            enable_api_keys=data.get("enable_api_keys", True),
            enable_webhooks=data.get("enable_webhooks", False),
            max_users=max(int(data.get("max_users", 100)), 1),
            max_api_keys_per_user=max(int(data.get("max_api_keys_per_user", 5)), 1),
            max_storage_mb=max(int(data.get("max_storage_mb", 1024)), 1),
            primary_color=data.get("primary_color", "#3B82F6"),
            logo_url=data.get("logo_url"),
            password_min_length=max(int(data.get("password_min_length", 8)), 1),
            session_timeout_minutes=max(int(data.get("session_timeout_minutes", 60)), 1),
            require_email_verification=data.get("require_email_verification", True),
        )


@dataclass
class Tenant(AuditableEntity):
    """
    Tenant entity representing an organization/company.

    Each tenant has isolated data via Row Level Security (RLS).
    All tenant-scoped entities reference this via tenant_id.
    """

    # Basic info
    name: str = ""
    slug: str = ""  # URL-friendly identifier

    # Contact
    email: str | None = None
    phone: str | None = None

    # Status
    is_active: bool = True
    is_verified: bool = False

    # Subscription/Plan
    plan: str = "free"  # free, starter, professional, enterprise
    plan_expires_at: datetime | None = None

    # Settings (stored as JSON)
    settings: TenantSettings = field(default_factory=TenantSettings)

    # Metadata
    domain: str | None = None  # Custom domain if any
    timezone: str = "UTC"
    locale: str = "en"

    # Soft delete fields (Tenant doesn't inherit from SoftDeletableEntity
    # because it's the root of the tenant hierarchy)
    is_deleted: bool = False
    deleted_at: datetime | None = None
    deleted_by: UUID | None = None

    def activate(self) -> None:
        """Activate the tenant."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate the tenant (soft disable)."""
        self.is_active = False

    def verify(self) -> None:
        """Mark tenant as verified."""
        self.is_verified = True

    def update_plan(self, plan: str, expires_at: datetime | None = None) -> None:
        """Update subscription plan."""
        valid_plans = {"free", "starter", "professional", "enterprise"}
        if plan not in valid_plans:
            raise ValueError("Invalid plan. Must be one of: free, starter, professional, enterprise")

        self.plan = plan
        self.plan_expires_at = expires_at

    def is_plan_expired(self) -> bool:
        """Check if the plan has expired."""
        if self.plan_expires_at is None:
            return False
        from datetime import UTC

        return datetime.now(UTC) > self.plan_expires_at

    def can_add_users(self, current_user_count: int) -> bool:
        """Check if tenant can add more users based on plan limits."""
        return current_user_count < self.settings.max_users

    def update_settings(self, **kwargs) -> None:
        """Update tenant settings."""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
