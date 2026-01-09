# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for role endpoint schemas."""

import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from app.api.v1.schemas.roles import (
    PermissionSchema,
    RoleCreate,
    RoleUpdate,
    AssignRoleRequest,
    RevokeRoleRequest,
    RoleResponse,
    RoleListResponse,
    UserPermissionsResponse,
)


class TestPermissionSchema:
    """Tests for PermissionSchema."""

    def test_permission_schema_valid(self):
        """Test valid permission schema."""
        perm = PermissionSchema(resource="users", action="read")
        assert perm.resource == "users"
        assert perm.action == "read"

    def test_permission_schema_requires_resource(self):
        """Test permission requires resource."""
        with pytest.raises(ValidationError):
            PermissionSchema(action="read")  # type: ignore[call-arg]

    def test_permission_schema_requires_action(self):
        """Test permission requires action."""
        with pytest.raises(ValidationError):
            PermissionSchema(resource="users")  # type: ignore[call-arg]


class TestRoleCreate:
    """Tests for RoleCreate schema."""

    def test_role_create_valid(self):
        """Test valid role creation."""
        role = RoleCreate(
            name="Admin",
            description="Administrator role",
            permissions=["users:read", "users:write"]
        )
        assert role.name == "Admin"
        assert role.description == "Administrator role"
        assert len(role.permissions) == 2

    def test_role_create_minimal(self):
        """Test role creation with minimal fields."""
        role = RoleCreate(name="Basic")
        assert role.name == "Basic"
        assert role.description == ""
        assert role.permissions == []

    def test_role_create_name_required(self):
        """Test role name is required."""
        with pytest.raises(ValidationError):
            RoleCreate(description="No name")  # type: ignore[call-arg]

    def test_role_create_name_min_length(self):
        """Test role name minimum length."""
        with pytest.raises(ValidationError):
            RoleCreate(name="")

    def test_role_create_name_max_length(self):
        """Test role name maximum length."""
        with pytest.raises(ValidationError):
            RoleCreate(name="a" * 101)

    def test_role_create_description_max_length(self):
        """Test role description maximum length."""
        with pytest.raises(ValidationError):
            RoleCreate(name="Valid", description="a" * 501)


class TestRoleUpdate:
    """Tests for RoleUpdate schema."""

    def test_role_update_all_fields(self):
        """Test role update with all fields."""
        update = RoleUpdate(
            name="Updated Name",
            description="Updated description",
            permissions=["new:permission"]
        )
        assert update.name == "Updated Name"
        assert update.description == "Updated description"
        assert update.permissions == ["new:permission"]

    def test_role_update_partial(self):
        """Test role update with partial fields."""
        update = RoleUpdate(name="New Name Only")
        assert update.name == "New Name Only"
        assert update.description is None
        assert update.permissions is None

    def test_role_update_empty(self):
        """Test role update with no fields."""
        update = RoleUpdate()
        assert update.name is None
        assert update.description is None
        assert update.permissions is None

    def test_role_update_name_min_length(self):
        """Test name minimum length."""
        with pytest.raises(ValidationError):
            RoleUpdate(name="")

    def test_role_update_name_max_length(self):
        """Test name maximum length."""
        with pytest.raises(ValidationError):
            RoleUpdate(name="x" * 101)


class TestAssignRoleRequest:
    """Tests for AssignRoleRequest schema."""

    def test_assign_role_valid(self):
        """Test valid assign role request."""
        user_id = uuid4()
        role_id = uuid4()
        request = AssignRoleRequest(user_id=user_id, role_id=role_id)
        assert request.user_id == user_id
        assert request.role_id == role_id

    def test_assign_role_requires_user_id(self):
        """Test assign role requires user_id."""
        with pytest.raises(ValidationError):
            AssignRoleRequest(role_id=uuid4())  # type: ignore[call-arg]

    def test_assign_role_requires_role_id(self):
        """Test assign role requires role_id."""
        with pytest.raises(ValidationError):
            AssignRoleRequest(user_id=uuid4())  # type: ignore[call-arg]


class TestRevokeRoleRequest:
    """Tests for RevokeRoleRequest schema."""

    def test_revoke_role_valid(self):
        """Test valid revoke role request."""
        user_id = uuid4()
        role_id = uuid4()
        request = RevokeRoleRequest(user_id=user_id, role_id=role_id)
        assert request.user_id == user_id
        assert request.role_id == role_id

    def test_revoke_role_requires_both_ids(self):
        """Test revoke role requires both IDs."""
        with pytest.raises(ValidationError):
            RevokeRoleRequest(user_id=uuid4())  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            RevokeRoleRequest(role_id=uuid4())  # type: ignore[call-arg]


class TestRoleResponse:
    """Tests for RoleResponse schema."""

    def test_role_response_valid(self):
        """Test valid role response."""
        now = datetime.utcnow()
        response = RoleResponse(
            id=uuid4(),
            name="Admin",
            description="Admin role",
            permissions=["users:read", "users:write"],
            is_system=False,
            created_at=now,
            updated_at=now
        )
        assert response.name == "Admin"
        assert len(response.permissions) == 2
        assert response.is_system is False

    def test_role_response_system_role(self):
        """Test system role response."""
        now = datetime.utcnow()
        response = RoleResponse(
            id=uuid4(),
            name="superuser",
            description="System superuser role",
            permissions=["*"],
            is_system=True,
            created_at=now,
            updated_at=now
        )
        assert response.is_system is True


class TestRoleListResponse:
    """Tests for RoleListResponse schema."""

    def test_role_list_response(self):
        """Test role list response."""
        now = datetime.utcnow()
        response = RoleListResponse(
            items=[
                RoleResponse(
                    id=uuid4(),
                    name="Role 1",
                    description="",
                    permissions=[],
                    is_system=False,
                    created_at=now,
                    updated_at=now
                )
            ],
            total=1
        )
        assert len(response.items) == 1
        assert response.total == 1

    def test_role_list_response_empty(self):
        """Test empty role list response."""
        response = RoleListResponse(items=[], total=0)
        assert len(response.items) == 0
        assert response.total == 0


class TestUserPermissionsResponse:
    """Tests for UserPermissionsResponse schema."""

    def test_user_permissions_response(self):
        """Test user permissions response."""
        user_id = uuid4()
        now = datetime.utcnow()
        role = RoleResponse(
            id=uuid4(),
            name="admin",
            description="Admin role",
            permissions=["*"],
            is_system=False,
            created_at=now,
            updated_at=now
        )
        response = UserPermissionsResponse(
            user_id=user_id,
            permissions=["users:read", "posts:write"],
            roles=[role]
        )
        assert response.user_id == user_id
        assert len(response.roles) == 1
        assert response.roles[0].name == "admin"
