# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Roles and ACL endpoints.

Optimized with Redis caching for frequently accessed role data.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentTenantId,
    DbSession,
    SuperuserId,
    require_permission,
)
from app.api.v1.schemas.common import MessageResponse
from app.api.v1.schemas.roles import (
    AssignRoleRequest,
    RevokeRoleRequest,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
    UserPermissionsResponse,
)
from app.application.services.acl_service import ACLService
from app.domain.entities.role import Permission, Role
from app.domain.exceptions.base import ConflictError, EntityNotFoundError
from app.domain.exceptions.base import ValidationError as DomainValidationError
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.cached_role_repository import (
    CachedRoleRepository,
    get_cached_role_repository,
)
from app.infrastructure.database.repositories.role_repository import (
    SQLAlchemyRoleRepository,
)
from app.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _role_to_response(role: Role) -> RoleResponse:
    """Convert Role entity to RoleResponse, handling Permission objects."""
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=[str(p) for p in role.permissions],
        is_system=role.is_system,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


def get_role_repository(
    session: AsyncSession = Depends(get_db_session),
) -> CachedRoleRepository:
    """Dependency to get cached role repository."""
    base_repo = SQLAlchemyRoleRepository(session)
    return get_cached_role_repository(base_repo)


@router.get(
    "",
    response_model=RoleListResponse,
    summary="List roles",
    description="List all roles for the current tenant.",
)
async def list_roles(
    tenant_id: CurrentTenantId,
    session: DbSession,
    current_user_id: UUID = Depends(require_permission("roles", "read")),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    repo: CachedRoleRepository = Depends(get_role_repository),
) -> RoleListResponse:
    """List all roles for the current tenant with caching."""
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_TENANT", "message": "Tenant context required"},
        )

    roles = await repo.list(tenant_id=tenant_id, skip=skip, limit=limit)
    total = await repo.count(tenant_id=tenant_id)

    return RoleListResponse(
        items=[_role_to_response(r) for r in roles],
        total=total,
    )


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Get role by ID",
    description="Get role details by ID.",
)
async def get_role(
    role_id: UUID,
    tenant_id: CurrentTenantId,
    session: DbSession,
    current_user_id: UUID = Depends(require_permission("roles", "read")),
    repo: CachedRoleRepository = Depends(get_role_repository),
) -> RoleResponse:
    """Get role by ID with caching."""
    role = await repo.get_by_id(role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROLE_NOT_FOUND", "message": "Role not found"},
        )

    # Validate tenant ownership — prevent cross-tenant role access.
    # When tenant_id is present, only allow roles that belong to this tenant
    # or system roles (tenant_id=None) which are shared.
    if tenant_id and role.tenant_id and role.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROLE_NOT_FOUND", "message": "Role not found"},
        )

    return _role_to_response(role)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create role",
    description="Create a new role. Requires superuser privileges.",
)
async def create_role(
    request: RoleCreate,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> RoleResponse:
    """Create a new role (admin only)."""
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_TENANT", "message": "Tenant context required"},
        )

    # Validate permissions format
    permissions = []
    for perm_str in request.permissions:
        try:
            permissions.append(Permission.from_string(perm_str))
        except (ValueError, DomainValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_PERMISSION",
                    "message": "Invalid permission format. Expected 'resource:action'.",
                },
            ) from None

    from uuid import uuid4

    role = Role(
        id=uuid4(),
        tenant_id=tenant_id,
        name=request.name,
        description=request.description,
        permissions=permissions,
        is_system=False,
        created_by=superuser_id,
    )

    repo = SQLAlchemyRoleRepository(session)

    try:
        created_role = await repo.create(role)
        return _role_to_response(created_role)

    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.patch(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Update role",
    description="Update role. Requires superuser privileges.",
)
async def update_role(
    role_id: UUID,
    request: RoleUpdate,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> RoleResponse:
    """Update role (admin only)."""
    repo = SQLAlchemyRoleRepository(session)
    role = await repo.get_by_id(role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROLE_NOT_FOUND", "message": "Role not found"},
        )

    # Validate tenant ownership
    if tenant_id and role.tenant_id and role.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROLE_NOT_FOUND", "message": "Role not found"},
        )

    if request.name is not None:
        role.name = request.name

    if request.description is not None:
        role.description = request.description

    if request.permissions is not None:
        permissions = []
        for perm_str in request.permissions:
            try:
                permissions.append(Permission.from_string(perm_str))
            except (ValueError, DomainValidationError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_PERMISSION",
                        "message": "Invalid permission format. Expected 'resource:action'.",
                    },
                ) from None
        role.permissions = permissions

    role.mark_updated(by_user=superuser_id)

    try:
        updated_role = await repo.update(role)
        return _role_to_response(updated_role)

    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.delete(
    "/{role_id}",
    response_model=MessageResponse,
    summary="Delete role",
    description="Delete role. Requires superuser privileges.",
)
async def delete_role(
    role_id: UUID,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> MessageResponse:
    """Delete role (admin only). System roles cannot be deleted."""
    repo = SQLAlchemyRoleRepository(session)

    # Validate tenant ownership before deletion
    role = await repo.get_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROLE_NOT_FOUND", "message": "Role not found"},
        )
    if tenant_id and role.tenant_id and role.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROLE_NOT_FOUND", "message": "Role not found"},
        )

    try:
        await repo.delete(role_id)
        return MessageResponse(
            message="Role deleted successfully",
            success=True,
        )

    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        ) from e

    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message},
        ) from e


@router.get(
    "/users/{user_id}/permissions",
    response_model=UserPermissionsResponse,
    summary="Get user permissions",
    description="Get effective permissions for a user.",
)
async def get_user_permissions(
    user_id: UUID,
    tenant_id: CurrentTenantId,
    session: DbSession,
    current_user_id: UUID = Depends(require_permission("roles", "read")),
) -> UserPermissionsResponse:
    """Get all permissions for a user based on their roles."""
    # Authorization: only self or superuser can view permissions
    if user_id != current_user_id:
        from app.infrastructure.database.models.user import UserModel

        requester = await session.get(UserModel, current_user_id)
        if not requester or not requester.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": "Only superusers can view other users' permissions",
                },
            )

    role_repo = SQLAlchemyRoleRepository(session)
    user_repo = SQLAlchemyUserRepository(session)

    # Get user
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )
    # Tenant isolation: verify user belongs to current tenant
    if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Get user's roles
    roles = await role_repo.get_user_roles(user_id)

    # Get ACL service to compute permissions
    acl_service = ACLService(role_repo)
    permissions = await acl_service.get_user_permissions(
        user_id=user_id,
        is_superuser=user.is_superuser,
    )

    return UserPermissionsResponse(
        user_id=user_id,
        permissions=permissions,
        roles=[_role_to_response(r) for r in roles],
    )


@router.post(
    "/assign",
    response_model=MessageResponse,
    summary="Assign role to user",
    description="Assign a role to a user. Requires superuser privileges.",
)
async def assign_role(
    request: AssignRoleRequest,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> MessageResponse:
    """Assign role to user (admin only)."""
    user_repo = SQLAlchemyUserRepository(session)
    role_repo = SQLAlchemyRoleRepository(session)

    # Verify user exists
    user = await user_repo.get_by_id(request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Verify user belongs to the same tenant
    if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Verify role exists
    role = await role_repo.get_by_id(request.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROLE_NOT_FOUND", "message": "Role not found"},
        )

    # Verify role belongs to the same tenant
    if tenant_id and role.tenant_id and role.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROLE_NOT_FOUND", "message": "Role not found"},
        )

    # Add role to user
    user.add_role(request.role_id)
    user.mark_updated(by_user=superuser_id)
    await user_repo.update(user)

    return MessageResponse(
        message="Role assigned to user",
        success=True,
    )


@router.post(
    "/revoke",
    response_model=MessageResponse,
    summary="Revoke role from user",
    description="Revoke a role from a user. Requires superuser privileges.",
)
async def revoke_role(
    request: RevokeRoleRequest,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
) -> MessageResponse:
    """Revoke role from user (admin only)."""
    user_repo = SQLAlchemyUserRepository(session)

    # Verify user exists
    user = await user_repo.get_by_id(request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Verify user belongs to the same tenant
    if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Remove role from user
    user.remove_role(request.role_id)
    user.mark_updated(by_user=superuser_id)
    await user_repo.update(user)

    return MessageResponse(
        message="Role revoked from user",
        success=True,
    )
