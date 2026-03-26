# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""API Key entity for machine-to-machine authentication."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities.base import AuditableEntity, TenantEntity


@dataclass
class APIKey(TenantEntity, AuditableEntity):
    """
    API Key entity for programmatic access.

    API keys are used for server-to-server communication,
    CLI tools, and automated integrations.
    """

    # Key identification
    name: str = ""  # Human-readable name
    prefix: str = ""  # First 8 chars of key for identification
    key_hash: str = ""  # Hashed key (never store plain key)

    # Owner
    user_id: UUID = field(default_factory=lambda: UUID(int=0))

    # Permissions (same format as role permissions)
    scopes: list[str] = field(default_factory=list)

    # Status
    is_active: bool = True

    # Expiration
    expires_at: datetime | None = None

    # Usage tracking
    last_used_at: datetime | None = None
    last_used_ip: str | None = None
    usage_count: int = 0

    # Soft delete fields (for consistency with DB model)
    is_deleted: bool = False
    deleted_at: datetime | None = None

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, prefix={self.prefix})>"

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid for use."""
        return self.is_active and not self.is_expired

    def record_usage(self, ip_address: str | None = None) -> None:
        """Record API key usage."""
        self.last_used_at = datetime.now(UTC)
        self.last_used_ip = ip_address
        self.usage_count += 1

    def has_scope(self, scope: str) -> bool:
        """
        Check if key has a specific scope.

        Supports wildcards:
        - "*" matches everything
        - "users:*" matches all user actions
        - "users:read" matches exact scope
        """
        if "*" in self.scopes:
            return True

        if scope in self.scopes:
            return True

        # Check wildcard patterns
        parts = scope.split(":")
        if len(parts) == 2:
            resource, action = parts
            wildcard = f"{resource}:*"
            if wildcard in self.scopes:
                return True

        return False

    def has_any_scope(self, scopes: list[str]) -> bool:
        """Check if key has any of the given scopes."""
        return any(self.has_scope(s) for s in scopes)

    def has_all_scopes(self, scopes: list[str]) -> bool:
        """Check if key has all of the given scopes."""
        return all(self.has_scope(s) for s in scopes)

    def revoke(self) -> None:
        """Revoke the API key."""
        self.is_active = False
