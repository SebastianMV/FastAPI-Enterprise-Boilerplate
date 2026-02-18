# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Role schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import DescriptionStr, RoleNameStr, ScopeStr, ShortStr

# ===========================================
# Request Schemas
# ===========================================


class PermissionSchema(BaseModel):
    """Permission representation."""

    resource: ShortStr = Field(..., description="Resource name (e.g., 'users')")
    action: ShortStr = Field(..., description="Action name (e.g., 'read', 'create')")


class RoleCreate(BaseModel):
    """Create role request."""

    name: RoleNameStr = Field(
        ...,
        description="Role name",
    )
    description: DescriptionStr = Field(
        default="",
        description="Role description",
    )
    permissions: list[ScopeStr] = Field(
        default_factory=list,
        max_length=100,
        description="List of permissions (resource:action format)",
    )


class RoleUpdate(BaseModel):
    """Update role request."""

    name: RoleNameStr | None = Field(
        default=None,
    )
    description: DescriptionStr | None = Field(
        default=None,
    )
    permissions: list[ScopeStr] | None = Field(default=None, max_length=100)


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
    name: RoleNameStr = Field()
    description: DescriptionStr = Field()
    permissions: list[ScopeStr]
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
    permissions: list[ScopeStr]
    roles: list[RoleResponse]
