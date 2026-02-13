# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Role domain entity."""

from dataclasses import dataclass, field

from app.domain.entities.base import TenantSoftDeletableEntity
from app.domain.exceptions.base import ValidationError as DomainValidationError


@dataclass
class Permission:
    """
    Permission value object.

    Represents a single permission as resource:action pair.

    Examples:
        - users:read
        - users:create
        - users:update
        - users:delete
        - roles:read
        - settings:manage
    """

    resource: str
    action: str

    def __str__(self) -> str:
        """String representation (resource:action)."""
        return f"{self.resource}:{self.action}"

    def __eq__(self, other: object) -> bool:
        """Compare permissions."""
        if isinstance(other, Permission):
            return self.resource == other.resource and self.action == other.action
        if isinstance(other, str):
            parts = other.split(":")
            if len(parts) == 2:
                return self.resource == parts[0] and self.action == parts[1]
        return False

    def __hash__(self) -> int:
        """Hash for set operations."""
        return hash((self.resource, self.action))

    @classmethod
    def from_string(cls, permission_str: str) -> "Permission":
        """
        Create Permission from string.

        Args:
            permission_str: "resource:action" format

        Returns:
            Permission instance

        Raises:
            ValueError: If format is invalid
        """
        parts = permission_str.split(":")
        if len(parts) != 2:
            raise DomainValidationError(
                message="Invalid permission format. Expected 'resource:action'",
                field="permission",
            )
        return cls(resource=parts[0], action=parts[1])


@dataclass
class Role(TenantSoftDeletableEntity):
    """
    Role domain entity.

    Groups permissions for assignment to users.
    """

    name: str = ""
    description: str = ""
    permissions: list[Permission] = field(default_factory=list)
    is_system: bool = False  # System roles cannot be deleted

    def add_permission(self, permission: Permission) -> None:
        """Add permission to role if not already present."""
        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission: Permission) -> None:
        """Remove permission from role."""
        if permission in self.permissions:
            self.permissions.remove(permission)

    def has_permission(self, resource: str, action: str) -> bool:
        """Check if role has specific permission."""
        target = Permission(resource=resource, action=action)

        # Check for wildcard permissions
        wildcard_resource = Permission(resource="*", action=action)
        wildcard_action = Permission(resource=resource, action="*")
        full_wildcard = Permission(resource="*", action="*")

        return (
            target in self.permissions
            or wildcard_resource in self.permissions
            or wildcard_action in self.permissions
            or full_wildcard in self.permissions
        )

    def has_any_permission(self, permissions: list[tuple[str, str]]) -> bool:
        """Check if role has any of the given permissions."""
        for resource, action in permissions:
            if self.has_permission(resource, action):
                return True
        return False

    def has_all_permissions(self, permissions: list[tuple[str, str]]) -> bool:
        """Check if role has all of the given permissions."""
        for resource, action in permissions:
            if not self.has_permission(resource, action):
                return False
        return True

    @property
    def permission_strings(self) -> list[str]:
        """Get permissions as list of strings."""
        return [str(p) for p in self.permissions]
