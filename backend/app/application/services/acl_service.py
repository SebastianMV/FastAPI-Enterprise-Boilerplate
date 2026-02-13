# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
ACL (Access Control List) Service.

Handles permission checking for users based on their roles.
"""

from uuid import UUID

from app.domain.entities.role import Permission, Role
from app.domain.exceptions.base import AuthorizationError
from app.domain.ports.role_repository import RoleRepositoryPort
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class ACLService:
    """
    Access Control List service.

    Checks user permissions based on assigned roles.
    """

    def __init__(self, role_repository: RoleRepositoryPort) -> None:
        """
        Initialize ACL service.

        Args:
            role_repository: Repository for role data access
        """
        self._role_repository = role_repository

    async def check_permission(
        self,
        user_id: UUID,
        resource: str,
        action: str,
        *,
        is_superuser: bool = False,
    ) -> bool:
        """
        Check if user has permission.

        Args:
            user_id: User's unique identifier
            resource: Resource name (e.g., "users", "roles")
            action: Action name (e.g., "read", "create", "delete")
            is_superuser: If True, bypasses permission check

        Returns:
            True if user has permission, False otherwise
        """
        # Superusers have all permissions
        if is_superuser:
            return True

        # Get user's roles
        roles = await self._role_repository.get_user_roles(user_id)

        # Check if any role has the permission
        return any(role.has_permission(resource, action) for role in roles)

    async def require_permission(
        self,
        user_id: UUID,
        resource: str,
        action: str,
        *,
        is_superuser: bool = False,
    ) -> None:
        """
        Require user to have permission (raises if not).

        Args:
            user_id: User's unique identifier
            resource: Resource name
            action: Action name
            is_superuser: If True, bypasses permission check

        Raises:
            AuthorizationError: If user lacks permission
        """
        has_permission = await self.check_permission(
            user_id=user_id,
            resource=resource,
            action=action,
            is_superuser=is_superuser,
        )

        if not has_permission:
            logger.warning(
                "permission_denied",
                user_id=str(user_id),
                resource=resource,
                action=action,
            )
            raise AuthorizationError(
                message="Insufficient permissions",
                resource=resource,
                action=action,
            )

    async def get_user_permissions(
        self,
        user_id: UUID,
        *,
        is_superuser: bool = False,
    ) -> list[str]:
        """
        Get all permissions for a user.

        Args:
            user_id: User's unique identifier
            is_superuser: If True, returns wildcard permission

        Returns:
            List of permission strings (resource:action)
        """
        if is_superuser:
            return ["*:*"]

        roles = await self._role_repository.get_user_roles(user_id)

        # Collect unique permissions from all roles
        permissions: set[str] = set()
        for role in roles:
            permissions.update(role.permission_strings)

        return sorted(permissions)

    async def can_access_resources(
        self,
        user_id: UUID,
        permissions: list[tuple[str, str]],
        *,
        require_all: bool = False,
        is_superuser: bool = False,
    ) -> bool:
        """
        Check if user has access to multiple resources.

        Args:
            user_id: User's unique identifier
            permissions: List of (resource, action) tuples
            require_all: If True, requires all permissions
            is_superuser: If True, bypasses permission check

        Returns:
            True if access is granted based on require_all logic
        """
        if is_superuser:
            return True

        roles = await self._role_repository.get_user_roles(user_id)

        if require_all:
            # Must have all permissions
            for resource, action in permissions:
                has_perm = any(r.has_permission(resource, action) for r in roles)
                if not has_perm:
                    return False
            return True
        # Must have at least one permission
        for resource, action in permissions:
            if any(r.has_permission(resource, action) for r in roles):
                return True
        return False


# ===========================================
# Default Permissions & Roles
# ===========================================

# Standard CRUD actions
ACTIONS = ["read", "create", "update", "delete", "manage"]

# Standard resources
RESOURCES = ["users", "roles", "settings", "tenants"]

# Default system roles with permissions
DEFAULT_ROLES = {
    "admin": {
        "description": "Full system administrator",
        "permissions": ["*:*"],
    },
    "manager": {
        "description": "Can manage most resources",
        "permissions": [
            "users:read",
            "users:create",
            "users:update",
            "roles:read",
            "settings:read",
            "settings:update",
        ],
    },
    "viewer": {
        "description": "Read-only access",
        "permissions": [
            "users:read",
            "roles:read",
            "settings:read",
        ],
    },
}


def create_default_roles(tenant_id: UUID) -> list[Role]:
    """
    Create default system roles for a new tenant.

    Args:
        tenant_id: Tenant UUID

    Returns:
        List of Role entities
    """
    from uuid import uuid4

    roles = []

    for role_name, config in DEFAULT_ROLES.items():
        permissions = [Permission.from_string(p) for p in config["permissions"]]

        role = Role(
            id=uuid4(),
            tenant_id=tenant_id,
            name=role_name,
            description=config["description"],
            permissions=permissions,
            is_system=True,
        )
        roles.append(role)

    return roles
