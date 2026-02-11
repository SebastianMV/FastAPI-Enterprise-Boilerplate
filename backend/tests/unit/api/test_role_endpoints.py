# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for role endpoints module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.roles import (
    AssignRoleRequest,
    PermissionSchema,
    RevokeRoleRequest,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
)


class TestRoleCreateSchema:
    """Tests for RoleCreate schema."""

    def test_role_create_minimal(self) -> None:
        """Test role create with minimal fields."""
        data = RoleCreate(name="Admin")
        assert data.name == "Admin"
        assert data.description == ""
        assert data.permissions == []

    def test_role_create_full(self) -> None:
        """Test role create with all fields."""
        data = RoleCreate(
            name="Editor",
            description="Can edit content",
            permissions=["posts:read", "posts:write", "users:read"],
        )
        assert data.name == "Editor"
        assert data.description == "Can edit content"
        assert len(data.permissions) == 3

    def test_role_create_name_too_short_fails(self) -> None:
        """Test role create with empty name fails."""
        with pytest.raises(ValidationError):
            RoleCreate(name="")

    def test_role_create_name_too_long_fails(self) -> None:
        """Test role create with name too long fails."""
        with pytest.raises(ValidationError):
            RoleCreate(name="x" * 101)


class TestRoleUpdateSchema:
    """Tests for RoleUpdate schema."""

    def test_role_update_partial(self) -> None:
        """Test partial role update."""
        data = RoleUpdate(name="Updated")
        assert data.name == "Updated"
        assert data.description is None
        assert data.permissions is None

    def test_role_update_full(self) -> None:
        """Test full role update."""
        data = RoleUpdate(
            name="New Name",
            description="New description",
            permissions=["users:read"],
        )
        assert data.name == "New Name"
        assert data.description == "New description"
        assert data.permissions == ["users:read"]

    def test_role_update_empty(self) -> None:
        """Test empty update."""
        data = RoleUpdate()
        assert data.name is None
        assert data.description is None
        assert data.permissions is None


class TestRoleResponseSchema:
    """Tests for RoleResponse schema."""

    def test_role_response_creation(self) -> None:
        """Test role response creation."""
        role_id = uuid4()
        response = RoleResponse(
            id=role_id,
            name="Admin",
            description="Administrator role",
            permissions=["users:read", "users:write"],
            is_system=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert response.id == role_id
        assert response.name == "Admin"
        assert len(response.permissions) == 2


class TestRoleListResponseSchema:
    """Tests for RoleListResponse schema."""

    def test_role_list_response(self) -> None:
        """Test role list response."""
        items = [
            RoleResponse(
                id=uuid4(),
                name=f"Role {i}",
                description=f"Description {i}",
                permissions=[],
                is_system=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            for i in range(3)
        ]
        response = RoleListResponse(items=items, total=10)
        assert len(response.items) == 3
        assert response.total == 10

    def test_role_list_response_empty(self) -> None:
        """Test empty role list."""
        response = RoleListResponse(items=[], total=0)
        assert len(response.items) == 0
        assert response.total == 0


class TestAssignRoleRequest:
    """Tests for AssignRoleRequest schema."""

    def test_assign_role_request(self) -> None:
        """Test assign role request."""
        user_id = uuid4()
        role_id = uuid4()
        data = AssignRoleRequest(user_id=user_id, role_id=role_id)
        assert data.user_id == user_id
        assert data.role_id == role_id


class TestRevokeRoleRequest:
    """Tests for RevokeRoleRequest schema."""

    def test_revoke_role_request(self) -> None:
        """Test revoke role request."""
        user_id = uuid4()
        role_id = uuid4()
        data = RevokeRoleRequest(user_id=user_id, role_id=role_id)
        assert data.user_id == user_id
        assert data.role_id == role_id


class TestPermissionSchema:
    """Tests for PermissionSchema."""

    def test_permission_schema(self) -> None:
        """Test permission schema."""
        perm = PermissionSchema(resource="users", action="read")
        assert perm.resource == "users"
        assert perm.action == "read"


def create_mock_role(role_id=None, tenant_id=None):
    """Create mock role with all required attributes."""
    if role_id is None:
        role_id = uuid4()
    if tenant_id is None:
        tenant_id = uuid4()
    mock_role = MagicMock()
    mock_role.id = role_id
    mock_role.tenant_id = tenant_id
    mock_role.name = "Test Role"
    mock_role.description = "Test description"
    mock_role.permissions = []
    mock_role.is_system = False
    mock_role.created_at = datetime.now(UTC)
    mock_role.updated_at = datetime.now(UTC)
    mock_role.created_by = uuid4()
    return mock_role


class TestListRolesEndpoint:
    """Tests for list roles endpoint."""

    @pytest.mark.asyncio
    async def test_list_roles_success(self) -> None:
        """Test listing roles successfully."""
        from app.api.v1.endpoints.roles import list_roles

        tenant_id = uuid4()
        mock_role = create_mock_role(tenant_id=tenant_id)

        mock_repo = AsyncMock()
        mock_repo.list.return_value = [mock_role]

        mock_session = AsyncMock()

        result = await list_roles(
            current_user_id=uuid4(),
            tenant_id=tenant_id,
            session=mock_session,
            skip=0,
            limit=100,
            repo=mock_repo,
        )

        assert result.total == 1
        assert len(result.items) == 1
        mock_repo.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_roles_no_tenant(self) -> None:
        """Test listing roles without tenant context."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.roles import list_roles

        mock_repo = AsyncMock()
        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await list_roles(
                current_user_id=uuid4(),
                tenant_id=None,
                session=mock_session,
                skip=0,
                limit=100,
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 400


class TestGetRoleEndpoint:
    """Tests for get role endpoint."""

    @pytest.mark.asyncio
    async def test_get_role_success(self) -> None:
        """Test getting role by ID."""
        from app.api.v1.endpoints.roles import get_role

        role_id = uuid4()
        mock_role = create_mock_role(role_id)

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_role

        mock_session = AsyncMock()

        result = await get_role(
            role_id=role_id,
            current_user_id=uuid4(),
            session=mock_session,
            repo=mock_repo,
        )

        assert result.id == role_id
        mock_repo.get_by_id.assert_called_once_with(role_id)

    @pytest.mark.asyncio
    async def test_get_role_not_found(self) -> None:
        """Test getting non-existent role."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.roles import get_role

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_role(
                role_id=uuid4(),
                current_user_id=uuid4(),
                session=mock_session,
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 404


class TestCreateRoleEndpoint:
    """Tests for create role endpoint."""

    @pytest.mark.asyncio
    async def test_create_role_no_tenant(self) -> None:
        """Test creating role without tenant context."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.roles import create_role

        request = RoleCreate(name="New Role")
        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await create_role(
                request=request,
                superuser_id=uuid4(),
                tenant_id=None,
                session=mock_session,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_create_role_invalid_permission(self) -> None:
        """Test creating role with invalid permission format."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.roles import create_role

        request = RoleCreate(
            name="New Role",
            permissions=["invalid_format"],
        )
        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await create_role(
                request=request,
                superuser_id=uuid4(),
                tenant_id=uuid4(),
                session=mock_session,
            )

        assert exc_info.value.status_code == 400


class TestRoleEdgeCases:
    """Edge case tests for role schemas."""

    def test_role_create_with_many_permissions(self) -> None:
        """Test creating role with many permissions."""
        permissions = [f"resource{i}:action{i}" for i in range(20)]
        data = RoleCreate(name="Complex Role", permissions=permissions)
        assert len(data.permissions) == 20

    def test_role_response_with_permissions(self) -> None:
        """Test role response with various permissions."""
        response = RoleResponse(
            id=uuid4(),
            name="Full Access",
            description="Has all permissions",
            permissions=[
                "users:read",
                "users:write",
                "posts:read",
                "posts:write",
                "admin:*",
            ],
            is_system=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert len(response.permissions) == 5
        assert response.is_system is True

    def test_role_update_clear_permissions(self) -> None:
        """Test updating role to clear permissions."""
        data = RoleUpdate(permissions=[])
        assert data.permissions == []

    def test_role_create_description_max_length(self) -> None:
        """Test role create with max description length."""
        data = RoleCreate(name="Role", description="x" * 500)
        assert len(data.description) == 500

    def test_role_create_description_too_long_fails(self) -> None:
        """Test role create with description too long."""
        with pytest.raises(ValidationError):
            RoleCreate(name="Role", description="x" * 501)
