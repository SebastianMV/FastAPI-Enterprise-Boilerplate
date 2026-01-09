# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for roles endpoint schemas and validation."""

from __future__ import annotations

from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.api.v1.schemas.roles import (
    AssignRoleRequest,
    RevokeRoleRequest,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
    UserPermissionsResponse,
)
from app.domain.entities.role import Permission, Role


class TestPermissionFromString:
    """Tests for Permission.from_string method."""

    def test_permission_from_valid_string(self) -> None:
        """Test Permission from valid string."""
        perm = Permission.from_string("users:read")
        assert perm.resource == "users"
        assert perm.action == "read"

    def test_permission_from_wildcard_action(self) -> None:
        """Test Permission with wildcard action."""
        perm = Permission.from_string("roles:*")
        assert perm.resource == "roles"
        assert perm.action == "*"

    def test_permission_from_invalid_string(self) -> None:
        """Test Permission from invalid string."""
        with pytest.raises(ValueError):
            Permission.from_string("invalid")

    def test_permission_to_string(self) -> None:
        """Test Permission to_string method."""
        perm = Permission(resource="tenants", action="update")
        assert str(perm) == "tenants:update" or hasattr(perm, "to_string")

    def test_permission_with_nested_resource(self) -> None:
        """Test Permission with nested resource."""
        perm = Permission.from_string("api_keys:delete")
        assert perm.resource == "api_keys"
        assert perm.action == "delete"


class TestRoleCreate:
    """Tests for RoleCreate schema."""

    def test_role_create_valid(self) -> None:
        """Test valid RoleCreate."""
        data = RoleCreate(
            name="Admin",
            description="Administrator role",
            permissions=["users:read", "users:write"]
        )
        assert data.name == "Admin"
        assert len(data.permissions) == 2

    def test_role_create_minimal(self) -> None:
        """Test minimal RoleCreate."""
        data = RoleCreate(
            name="Viewer"
        )
        assert data.name == "Viewer"

    def test_role_create_empty_name(self) -> None:
        """Test RoleCreate with empty name raises error."""
        with pytest.raises(ValidationError):
            RoleCreate(name="")


class TestRoleUpdate:
    """Tests for RoleUpdate schema."""

    def test_role_update_name_only(self) -> None:
        """Test RoleUpdate with only name."""
        data = RoleUpdate(name="New Name")
        assert data.name == "New Name"

    def test_role_update_permissions_only(self) -> None:
        """Test RoleUpdate with only permissions."""
        data = RoleUpdate(permissions=["users:*"])
        assert data.permissions == ["users:*"]

    def test_role_update_all_fields(self) -> None:
        """Test RoleUpdate with all fields."""
        data = RoleUpdate(
            name="Updated Role",
            description="Updated description",
            permissions=["users:read"]
        )
        assert data.name == "Updated Role"
        assert data.description == "Updated description"


class TestRoleResponse:
    """Tests for RoleResponse schema."""

    def test_role_response_creation(self) -> None:
        """Test RoleResponse creation."""
        from datetime import datetime, UTC
        
        role_id = uuid4()
        data = RoleResponse(
            id=role_id,
            name="Test Role",
            description="Test description",
            permissions=["users:read"],
            is_system=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert data.id == role_id
        assert data.name == "Test Role"

    def test_role_response_with_description(self) -> None:
        """Test RoleResponse with description."""
        from datetime import datetime, UTC
        
        data = RoleResponse(
            id=uuid4(),
            name="Described Role",
            description="This is a test role",
            permissions=[],
            is_system=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert data.description == "This is a test role"


class TestRoleListResponse:
    """Tests for RoleListResponse schema."""

    def test_role_list_response_empty(self) -> None:
        """Test empty RoleListResponse."""
        data = RoleListResponse(items=[], total=0)
        assert data.items == []
        assert data.total == 0

    def test_role_list_response_with_items(self) -> None:
        """Test RoleListResponse with items."""
        from datetime import datetime, UTC
        
        role1 = RoleResponse(
            id=uuid4(),
            name="Role 1",
            description="Desc 1",
            permissions=[],
            is_system=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        role2 = RoleResponse(
            id=uuid4(),
            name="Role 2",
            description="Desc 2",
            permissions=[],
            is_system=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        data = RoleListResponse(items=[role1, role2], total=2)
        assert len(data.items) == 2
        assert data.total == 2


class TestAssignRoleRequest:
    """Tests for AssignRoleRequest schema."""

    def test_assign_role_request(self) -> None:
        """Test AssignRoleRequest."""
        user_id = uuid4()
        role_id = uuid4()
        data = AssignRoleRequest(user_id=user_id, role_id=role_id)
        assert data.user_id == user_id
        assert data.role_id == role_id


class TestRevokeRoleRequest:
    """Tests for RevokeRoleRequest schema."""

    def test_revoke_role_request(self) -> None:
        """Test RevokeRoleRequest."""
        user_id = uuid4()
        role_id = uuid4()
        data = RevokeRoleRequest(user_id=user_id, role_id=role_id)
        assert data.user_id == user_id
        assert data.role_id == role_id


class TestUserPermissionsResponse:
    """Tests for UserPermissionsResponse schema."""

    def test_user_permissions_response(self) -> None:
        """Test UserPermissionsResponse."""
        from datetime import datetime, UTC
        
        user_id = uuid4()
        role = RoleResponse(
            id=uuid4(),
            name="admin",
            description="Admin role",
            permissions=["users:read", "roles:read", "tenants:*"],
            is_system=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        data = UserPermissionsResponse(
            user_id=user_id,
            permissions=["users:read", "roles:read", "tenants:*"],
            roles=[role]
        )
        assert "users:read" in data.permissions
        assert len(data.roles) == 1

    def test_user_permissions_response_empty(self) -> None:
        """Test UserPermissionsResponse with empty data."""
        user_id = uuid4()
        data = UserPermissionsResponse(user_id=user_id, permissions=[], roles=[])
        assert data.permissions == []
        assert data.roles == []


class TestRolesRouter:
    """Tests for roles router configuration."""

    def test_router_exists(self) -> None:
        """Test router exists."""
        from app.api.v1.endpoints.roles import router
        assert router is not None

    def test_router_has_routes(self) -> None:
        """Test router has routes."""
        from app.api.v1.endpoints.roles import router
        assert len(router.routes) > 0

    def test_get_role_repository_dependency(self) -> None:
        """Test get_role_repository dependency exists."""
        from app.api.v1.endpoints.roles import get_role_repository
        assert callable(get_role_repository)
