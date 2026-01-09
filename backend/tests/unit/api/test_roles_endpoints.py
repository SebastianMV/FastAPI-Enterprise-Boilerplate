# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Roles API endpoints.

Tests for role and permission CRUD operations.
"""

from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestListRolesEndpoint:
    """Tests for /roles (list) endpoint."""

    @pytest.mark.asyncio
    async def test_list_roles_no_tenant(self) -> None:
        """Test listing roles without tenant context."""
        from app.api.v1.endpoints.roles import list_roles

        mock_session = AsyncMock()
        mock_repo = AsyncMock()

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
        assert exc_info.value.detail["code"] == "NO_TENANT"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_list_roles_success(self) -> None:
        """Test listing roles successfully."""
        from app.api.v1.endpoints.roles import list_roles

        mock_session = AsyncMock()
        tenant_id = uuid4()

        mock_role = MagicMock()
        mock_role.id = uuid4()
        mock_role.tenant_id = tenant_id
        mock_role.name = "Admin"
        mock_role.description = "Admin role"
        mock_role.permissions = []
        mock_role.is_system = False
        mock_role.created_at = datetime.now(UTC)
        mock_role.updated_at = datetime.now(UTC)

        mock_repo = AsyncMock()
        mock_repo.list.return_value = [mock_role]

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

    @pytest.mark.asyncio
    async def test_list_roles_empty(self) -> None:
        """Test listing roles when none exist."""
        from app.api.v1.endpoints.roles import list_roles

        mock_session = AsyncMock()
        tenant_id = uuid4()
        mock_repo = AsyncMock()
        mock_repo.list.return_value = []

        result = await list_roles(
            current_user_id=uuid4(),
            tenant_id=tenant_id,
            session=mock_session,
            skip=0,
            limit=100,
            repo=mock_repo,
        )

        assert result.total == 0
        assert result.items == []


class TestGetRoleEndpoint:
    """Tests for /roles/{role_id} (get) endpoint."""

    @pytest.mark.asyncio
    async def test_get_role_success(self) -> None:
        """Test getting role successfully."""
        from app.api.v1.endpoints.roles import get_role

        role_id = uuid4()
        mock_session = AsyncMock()

        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.tenant_id = uuid4()
        mock_role.name = "Admin"
        mock_role.description = "Admin role"
        mock_role.permissions = []
        mock_role.is_system = False
        mock_role.created_at = datetime.now(UTC)
        mock_role.updated_at = datetime.now(UTC)

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_role

        result = await get_role(
            role_id=role_id,
            current_user_id=uuid4(),
            session=mock_session,
            repo=mock_repo,
        )

        assert result.id == role_id
        assert result.name == "Admin"

    @pytest.mark.asyncio
    async def test_get_role_not_found(self) -> None:
        """Test getting role that doesn't exist."""
        from app.api.v1.endpoints.roles import get_role

        role_id = uuid4()
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_role(
                role_id=role_id,
                current_user_id=uuid4(),
                session=mock_session,
                repo=mock_repo,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == "ROLE_NOT_FOUND"  # type: ignore[index]


class TestCreateRoleEndpoint:
    """Tests for /roles (create) endpoint."""

    @pytest.mark.asyncio
    async def test_create_role_no_tenant(self) -> None:
        """Test creating role without tenant context."""
        from app.api.v1.endpoints.roles import create_role
        from app.api.v1.schemas.roles import RoleCreate

        mock_session = AsyncMock()
        request = RoleCreate(
            name="Test Role",
            description="A test role",
            permissions=["users:read"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_role(
                request=request,
                superuser_id=uuid4(),
                tenant_id=None,
                session=mock_session,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "NO_TENANT"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_create_role_invalid_permission(self) -> None:
        """Test creating role with invalid permission format."""
        from app.api.v1.endpoints.roles import create_role
        from app.api.v1.schemas.roles import RoleCreate

        mock_session = AsyncMock()
        request = RoleCreate(
            name="Test Role",
            description="A test role",
            permissions=["invalid-format"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_role(
                request=request,
                superuser_id=uuid4(),
                tenant_id=uuid4(),
                session=mock_session,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_PERMISSION"  # type: ignore[index]


class TestRoleSchemas:
    """Tests for role schemas."""

    def test_role_create_valid(self) -> None:
        """Test valid RoleCreate schema."""
        from app.api.v1.schemas.roles import RoleCreate

        role = RoleCreate(
            name="Admin",
            description="Administrator role",
            permissions=["users:read", "users:write"],
        )

        assert role.name == "Admin"
        assert len(role.permissions) == 2

    def test_role_create_minimal(self) -> None:
        """Test RoleCreate with minimal data."""
        from app.api.v1.schemas.roles import RoleCreate

        role = RoleCreate(
            name="Viewer",
        )

        assert role.name == "Viewer"
        assert role.description == ""  # Default is empty string
        assert role.permissions == []

    def test_role_update_valid(self) -> None:
        """Test valid RoleUpdate schema."""
        from app.api.v1.schemas.roles import RoleUpdate

        update = RoleUpdate(
            name="Updated Role",
            description="Updated description",
        )

        assert update.name == "Updated Role"

    def test_role_response(self) -> None:
        """Test RoleResponse schema."""
        from app.api.v1.schemas.roles import RoleResponse

        response = RoleResponse(
            id=uuid4(),
            name="Admin",
            description="Admin role",
            permissions=[],
            is_system=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert response.name == "Admin"
        assert response.is_system is False

    def test_role_list_response(self) -> None:
        """Test RoleListResponse schema."""
        from app.api.v1.schemas.roles import RoleListResponse, RoleResponse

        response = RoleListResponse(
            items=[
                RoleResponse(
                    id=uuid4(),
                    name="Admin",
                    description="Admin role",
                    permissions=[],
                    is_system=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
            total=1,
        )

        assert len(response.items) == 1
        assert response.total == 1

    def test_assign_role_request(self) -> None:
        """Test AssignRoleRequest schema."""
        from app.api.v1.schemas.roles import AssignRoleRequest

        request = AssignRoleRequest(
            user_id=uuid4(),
            role_id=uuid4(),
        )

        assert request.user_id is not None
        assert request.role_id is not None

    def test_revoke_role_request(self) -> None:
        """Test RevokeRoleRequest schema."""
        from app.api.v1.schemas.roles import RevokeRoleRequest

        request = RevokeRoleRequest(
            user_id=uuid4(),
            role_id=uuid4(),
        )

        assert request.user_id is not None

    def test_user_permissions_response(self) -> None:
        """Test UserPermissionsResponse schema."""
        from app.api.v1.schemas.roles import UserPermissionsResponse, RoleResponse

        response = UserPermissionsResponse(
            user_id=uuid4(),
            permissions=["users:read", "users:write"],
            roles=[
                RoleResponse(
                    id=uuid4(),
                    name="Admin",
                    description="Admin role",
                    permissions=["users:read"],
                    is_system=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
        )

        assert len(response.permissions) == 2
        assert len(response.roles) == 1


class TestGetRoleRepository:
    """Tests for get_role_repository dependency."""

    def test_get_role_repository_returns_cached_repo(self) -> None:
        """Test that get_role_repository returns a CachedRoleRepository."""
        from app.api.v1.endpoints.roles import get_role_repository

        mock_session = MagicMock()

        with patch(
            "app.api.v1.endpoints.roles.SQLAlchemyRoleRepository"
        ) as mock_base_repo:
            with patch(
                "app.api.v1.endpoints.roles.get_cached_role_repository"
            ) as mock_get_cached:
                mock_cached_repo = MagicMock()
                mock_get_cached.return_value = mock_cached_repo

                result = get_role_repository(session=mock_session)

                mock_base_repo.assert_called_once_with(mock_session)
                assert result == mock_cached_repo
