# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""FastAPI dependency injection utilities."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.domain.exceptions.base import AuthenticationError, AuthorizationError
from app.infrastructure.auth.jwt_handler import validate_access_token
from app.infrastructure.database.connection import get_db_session

# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> UUID:
    """
    Extract and validate user ID from JWT token.
    
    Usage:
        @router.get("/me")
        async def get_me(user_id: UUID = Depends(get_current_user_id)):
            ...
    
    Raises:
        HTTPException 401: If token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authorization required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = validate_access_token(credentials.credentials)
        return UUID(payload["sub"])
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_tenant_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> UUID | None:
    """
    Extract tenant ID from JWT token.
    
    Returns None if no tenant context (e.g., superuser without tenant).
    """
    if not credentials:
        return None
    
    try:
        payload = validate_access_token(credentials.credentials)
        tenant_id = payload.get("tenant_id")
        return UUID(tenant_id) if tenant_id else None
    
    except AuthenticationError:
        return None


async def require_superuser(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> UUID:
    """
    Require superuser role.
    
    Usage:
        @router.delete("/users/{id}")
        async def delete_user(user_id: UUID = Depends(require_superuser)):
            ...
    
    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If not superuser
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authorization required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = validate_access_token(credentials.credentials)
        
        if not payload.get("is_superuser", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": "Superuser access required",
                },
            )
        
        return UUID(payload["sub"])
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(resource: str, action: str):
    """
    Permission decorator factory for ACL-based authorization.
    
    Checks if the current user has the required permission through their roles.
    Superusers automatically have all permissions.
    
    Usage:
        @router.get("/users")
        async def list_users(
            user_id: UUID = Depends(require_permission("users", "read"))
        ):
            ...
    
    Args:
        resource: The resource being accessed (e.g., "users", "roles", "settings")
        action: The action being performed (e.g., "read", "create", "update", "delete")
    
    Returns:
        Dependency that returns user_id if authorized
    
    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If user lacks required permission
    """
    async def permission_checker(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(security),
        ],
        session: AsyncSession = Depends(get_db_session),
    ) -> UUID:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "MISSING_TOKEN", "message": "Authorization required"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            payload = validate_access_token(credentials.credentials)
            user_id = UUID(payload["sub"])
            
            # Superusers have all permissions
            if payload.get("is_superuser", False):
                return user_id
            
            # Get user from database to check roles
            from app.infrastructure.database.models.user import UserModel
            from app.infrastructure.database.models.role import RoleModel
            from sqlalchemy import select
            
            user_result = await session.get(UserModel, user_id)
            if not user_result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "USER_NOT_FOUND", "message": "User not found"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user_result.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "ACCOUNT_DISABLED", "message": "Account is disabled"},
                )
            
            # Get user's roles with permissions
            role_ids = user_result.roles or []
            if not role_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "FORBIDDEN",
                        "message": f"Permission denied: {resource}:{action}",
                    },
                )
            
            # Fetch roles from database
            stmt = select(RoleModel).where(
                RoleModel.id.in_(role_ids),
                RoleModel.is_deleted == False,
            )
            result = await session.execute(stmt)
            roles = result.scalars().all()
            
            # Check if any role has the required permission
            required_permission = f"{resource}:{action}"
            wildcard_resource = f"*:{action}"
            wildcard_action = f"{resource}:*"
            full_wildcard = "*:*"
            
            for role in roles:
                permissions = role.permissions or []
                if (
                    required_permission in permissions
                    or wildcard_resource in permissions
                    or wildcard_action in permissions
                    or full_wildcard in permissions
                ):
                    return user_id
            
            # No permission found
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Permission denied: {resource}:{action}",
                },
            )
        
        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": e.code, "message": e.message},
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return permission_checker


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get the current authenticated user.
    
    This dependency fetches the full User entity from the database
    using the user_id extracted from the JWT token.
    
    Usage:
        @router.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            ...
    
    Raises:
        HTTPException 401: If user not found
    """
    from app.infrastructure.database.models.user import UserModel
    from app.domain.entities.user import User
    from app.domain.value_objects.email import Email
    
    result = await session.get(UserModel, user_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Convert model to domain entity
    return User(
        id=result.id,
        tenant_id=result.tenant_id,
        email=Email(result.email),
        password_hash=result.password_hash,
        first_name=result.first_name or "",
        last_name=result.last_name or "",
        is_active=result.is_active,
        is_superuser=result.is_superuser,
        roles=result.roles or [],
        last_login=result.last_login,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


# Type aliases for cleaner dependency injection
from app.domain.entities.user import User

CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
CurrentTenantId = Annotated[UUID | None, Depends(get_current_tenant_id)]
CurrentUser = Annotated[User, Depends(get_current_user)]
SuperuserId = Annotated[UUID, Depends(require_superuser)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
