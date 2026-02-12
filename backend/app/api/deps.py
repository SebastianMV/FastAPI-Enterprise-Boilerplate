# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""FastAPI dependency injection utilities."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions.base import AuthenticationError
from app.infrastructure.auth.jwt_handler import validate_access_token
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


async def _is_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI has been blacklisted (e.g., after logout).

    In production/staging: fail-closed (reject token if Redis unavailable).
    In development: fail-open (allow token if Redis unavailable).
    """
    try:
        from app.infrastructure.cache import get_cache

        cache = get_cache()
        result = await cache.get(f"blacklist:token:{jti}")
        return result is not None
    except Exception as exc:
        from app.config import settings as _settings

        if _settings.ENVIRONMENT in ("production", "staging"):
            # Fail-closed: reject tokens when Redis is unavailable
            logger.error(
                "Redis unavailable for token blacklist check — fail-closed: %s", exc
            )
            return True
        # Development: fail-open for convenience
        logger.warning(
            "Redis unavailable for token blacklist check — fail-open (dev): %s", exc
        )
        return False


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
    request: Request,
) -> str | None:
    """Extract token from Bearer header or HttpOnly cookie (fallback)."""
    if credentials:
        return credentials.credentials
    # Fallback: check HttpOnly cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    return None


async def get_current_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
    request: Request,
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
    token = _extract_token(credentials, request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authorization required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = validate_access_token(token)

        # Check if token has been blacklisted (logout)
        jti = payload.get("jti")
        if jti and await _is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "TOKEN_REVOKED", "message": "Token has been revoked"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return UUID(payload["sub"])

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_tenant_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
    request: Request,
) -> UUID | None:
    """
    Extract tenant ID from JWT token.

    Returns None if no tenant context (e.g., superuser without tenant).
    """
    token = _extract_token(credentials, request)
    if not token:
        return None

    try:
        payload = validate_access_token(token)
        tenant_id = payload.get("tenant_id")
        return UUID(tenant_id) if tenant_id else None

    except AuthenticationError:
        return None


async def require_superuser(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> UUID:
    """
    Require superuser role.

    Verifies is_superuser and is_active from the database (not just JWT claims)
    to ensure revoked superusers are rejected immediately.

    Usage:
        @router.delete("/users/{id}")
        async def delete_user(user_id: UUID = Depends(require_superuser)):
            ...

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If not superuser or account disabled
    """
    token = _extract_token(credentials, request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authorization required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = validate_access_token(token)

        # Check if token has been blacklisted (logout)
        jti = payload.get("jti")
        if jti and await _is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "TOKEN_REVOKED", "message": "Token has been revoked"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = UUID(payload["sub"])

        # Verify is_superuser and is_active from DB (not just JWT claims)
        from app.infrastructure.database.models.user import UserModel

        user = await session.get(UserModel, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "USER_NOT_FOUND", "message": "User not found"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ACCOUNT_DISABLED",
                    "message": "Account is disabled",
                },
            )

        if not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": "Superuser access required",
                },
            )

        return user_id

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.code, "message": e.message},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def require_permission(resource: str, action: str) -> Any:
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
        request: Request,
        session: AsyncSession = Depends(get_db_session),
    ) -> UUID:
        token = _extract_token(credentials, request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "MISSING_TOKEN", "message": "Authorization required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = validate_access_token(token)
            user_id = UUID(payload["sub"])

            # Check if token has been blacklisted (logout)
            jti = payload.get("jti")
            if jti and await _is_token_blacklisted(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "code": "TOKEN_REVOKED",
                        "message": "Token has been revoked",
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # B5: Cache user lookup on request to avoid repeated DB queries
            # when multiple dependencies (require_permission, get_current_user)
            # are used in the same request.
            _cache_attr = "_cached_user_model"
            user_result = getattr(request.state, _cache_attr, None)
            if user_result is None or user_result.id != user_id:
                from app.infrastructure.database.models.user import UserModel

                user_result = await session.get(UserModel, user_id)
                if user_result is not None:
                    request.state._cached_user_model = user_result
            if not user_result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "USER_NOT_FOUND", "message": "User not found"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user_result.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "ACCOUNT_DISABLED",
                        "message": "Account is disabled",
                    },
                )

            # Superusers have all permissions — verified from DB, not just JWT
            if user_result.is_superuser:
                return user_id

            role_ids = user_result.roles or []
            if not role_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "FORBIDDEN",
                        "message": "Insufficient permissions",
                    },
                )

            # Fetch roles via cached repository (Redis-backed)
            from app.infrastructure.database.repositories.cached_role_repository import (
                get_cached_role_repository,
            )
            from app.infrastructure.database.repositories.role_repository import (
                SQLAlchemyRoleRepository,
            )

            base_repo = SQLAlchemyRoleRepository(session)
            cached_repo = get_cached_role_repository(base_repo)

            required_permission = f"{resource}:{action}"
            wildcard_resource = f"*:{action}"
            wildcard_action = f"{resource}:*"
            full_wildcard = "*:*"

            for rid in role_ids:
                role = await cached_repo.get_by_id(rid)
                if not role:
                    continue
                permissions = [str(p) for p in role.permissions]
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
                    "message": "Insufficient permissions",
                },
            )

        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": e.code, "message": e.message},
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    return permission_checker


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> "User":
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
    from app.domain.entities.user import User
    from app.domain.value_objects.email import Email
    from app.infrastructure.database.models.user import UserModel

    result = await session.get(UserModel, user_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # B-06: Reject disabled users during active token window
    if not result.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_DISABLED", "message": "Account is disabled"},
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
        failed_login_attempts=result.failed_login_attempts,
        locked_until=result.locked_until,
        email_verified=result.email_verified,
        email_verification_token=result.email_verification_token,
        email_verification_sent_at=result.email_verification_sent_at,
        avatar_url=result.avatar_url,
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
