# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Role schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ===========================================
# Request Schemas
# ===========================================


class PermissionSchema(BaseModel):
    """Permission representation."""

    resource: str = Field(..., max_length=50, description="Resource name (e.g., 'users')")
    action: str = Field(..., max_length=50, description="Action name (e.g., 'read', 'create')")


class RoleCreate(BaseModel):
    """Create role request."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Role name",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Role description",
    )
    permissions: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="List of permissions (resource:action format)",
    )


class RoleUpdate(BaseModel):
    """Update role request."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        default=None,
        max_length=500,
    )
    permissions: list[str] | None = Field(default=None, max_length=100)


class AssignRoleRequest(BaseModel):
    """Assign role to user request."""

    user_id: UUID
    role_id: UUID


class RevokeRoleRequest(BaseModel):
    """Revoke role from user request."""

    user_id: UUID
    role_id: UUID


# ===========================================
# Response Schemas
# ===========================================


class RoleResponse(BaseModel):
    """Role response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    permissions: list[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime


class RoleListResponse(BaseModel):
    """Paginated role list response."""

    items: list[RoleResponse]
    total: int


class UserPermissionsResponse(BaseModel):
    """User's effective permissions."""

    user_id: UUID
    permissions: list[str]
    roles: list[RoleResponse]
