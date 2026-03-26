# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Tests for roles endpoints API."""

from __future__ import annotations

from uuid import uuid4


class TestRolesEndpointsStructure:
    """Tests for roles endpoints structure."""

    def test_router_import(self) -> None:
        """Test router can be imported."""
        from app.api.v1.endpoints.roles import router

        assert router is not None

    def test_router_is_api_router(self) -> None:
        """Test router is an APIRouter."""
        from fastapi import APIRouter

        from app.api.v1.endpoints.roles import router

        assert isinstance(router, APIRouter)

    def test_get_role_repository_import(self) -> None:
        """Test get_role_repository can be imported."""
        from app.api.v1.endpoints.roles import get_role_repository

        assert get_role_repository is not None
        assert callable(get_role_repository)


class TestRolesSchemas:
    """Tests for roles API schemas."""

    def test_role_create_schema(self) -> None:
        """Test RoleCreate schema."""
        from app.api.v1.schemas.roles import RoleCreate

        data = RoleCreate(
            name="Admin",
            description="Administrator role",
            permissions=["users:read", "users:write"],
        )
        assert data.name == "Admin"
        assert len(data.permissions) == 2

    def test_role_update_schema(self) -> None:
        """Test RoleUpdate schema."""
        from app.api.v1.schemas.roles import RoleUpdate

        data = RoleUpdate(name="Updated Admin")
        assert data.name == "Updated Admin"

    def test_role_response_schema(self) -> None:
        """Test RoleResponse schema."""
        from app.api.v1.schemas.roles import RoleResponse

        assert RoleResponse is not None

    def test_assign_role_request_schema(self) -> None:
        """Test AssignRoleRequest schema."""
        from app.api.v1.schemas.roles import AssignRoleRequest

        user_id = uuid4()
        role_id = uuid4()
        data = AssignRoleRequest(user_id=user_id, role_id=role_id)
        assert data.user_id == user_id
        assert data.role_id == role_id

    def test_revoke_role_request_schema(self) -> None:
        """Test RevokeRoleRequest schema."""
        from app.api.v1.schemas.roles import RevokeRoleRequest

        user_id = uuid4()
        role_id = uuid4()
        data = RevokeRoleRequest(user_id=user_id, role_id=role_id)
        assert data.user_id == user_id

    def test_role_list_response_schema(self) -> None:
        """Test RoleListResponse schema."""
        from app.api.v1.schemas.roles import RoleListResponse

        data = RoleListResponse(items=[], total=0, page=1, page_size=100, pages=0)
        assert data.total == 0
        assert len(data.items) == 0

    def test_user_permissions_response_schema(self) -> None:
        """Test UserPermissionsResponse schema."""
        from app.api.v1.schemas.roles import UserPermissionsResponse

        assert UserPermissionsResponse is not None


class TestRolesRouterRoutes:
    """Tests for roles router route registration."""

    def test_list_roles_route_exists(self) -> None:
        """Test list roles route is registered."""
        from app.api.v1.endpoints.roles import router

        routes = [getattr(r, "path", None) for r in router.routes]
        assert "" in routes or "/" in routes

    def test_get_role_route_exists(self) -> None:
        """Test get role route is registered."""
        from app.api.v1.endpoints.roles import router

        routes = [getattr(r, "path", None) for r in router.routes]
        assert "/{role_id}" in routes

    def test_router_has_multiple_routes(self) -> None:
        """Test router has multiple routes."""
        from app.api.v1.endpoints.roles import router

        assert len(router.routes) >= 2


class TestPermissionEntity:
    """Tests for Permission entity."""

    def test_permission_from_string(self) -> None:
        """Test Permission.from_string."""
        from app.domain.entities.role import Permission

        perm = Permission.from_string("users:read")
        assert perm.resource == "users"
        assert perm.action == "read"

    def test_permission_from_string_wildcard(self) -> None:
        """Test Permission.from_string with wildcard."""
        from app.domain.entities.role import Permission

        perm = Permission.from_string("*:*")
        assert perm.resource == "*"
        assert perm.action == "*"

    def test_permission_to_string(self) -> None:
        """Test Permission to_string."""
        from app.domain.entities.role import Permission

        perm = Permission(resource="users", action="write")
        assert str(perm) == "users:write"

    def test_permission_equality(self) -> None:
        """Test Permission equality."""
        from app.domain.entities.role import Permission

        perm1 = Permission(resource="users", action="read")
        perm2 = Permission(resource="users", action="read")
        perm3 = Permission(resource="users", action="write")
        assert perm1 == perm2
        assert perm1 != perm3

    def test_permission_hash(self) -> None:
        """Test Permission hash."""
        from app.domain.entities.role import Permission

        perm1 = Permission(resource="users", action="read")
        perm2 = Permission(resource="users", action="read")
        assert hash(perm1) == hash(perm2)


class TestRoleEntity:
    """Tests for Role entity."""

    def test_role_creation(self) -> None:
        """Test Role entity creation."""
        from app.domain.entities.role import Permission, Role

        tenant_id = uuid4()
        role = Role(
            tenant_id=tenant_id,
            name="Admin",
            description="Administrator",
            permissions=[Permission(resource="users", action="read")],
            is_system=False,
        )
        assert role.name == "Admin"
        assert role.tenant_id == tenant_id

    def test_role_has_permission(self) -> None:
        """Test Role.has_permission method."""
        from app.domain.entities.role import Permission, Role

        tenant_id = uuid4()
        role = Role(
            tenant_id=tenant_id,
            name="Reader",
            permissions=[Permission(resource="users", action="read")],
        )
        assert role.has_permission("users", "read") is True
        assert role.has_permission("users", "write") is False
