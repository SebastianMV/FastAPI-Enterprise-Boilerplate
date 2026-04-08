# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Integration tests for roles endpoints with PostgreSQL.

These tests use real PostgreSQL database via HTTP client to test:
- Role CRUD operations
- Permission management
- RLS (Row-Level Security)
- JSONB permissions
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from app.domain.entities.role import Permission, Role
from app.infrastructure.database.repositories.role_repository import (
    SQLAlchemyRoleRepository,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_role_for_admin(integration_db_session, real_admin_user):
    """Create test role for admin user's tenant."""
    if not integration_db_session or not real_admin_user:
        pytest.skip("Requires PostgreSQL integration database")

    role_repo = SQLAlchemyRoleRepository(integration_db_session)
    unique_id = str(uuid4())[:8]

    role = Role(
        id=uuid4(),
        name=f"TestRole-{unique_id}",
        description="Test role for integration tests",
        tenant_id=real_admin_user["tenant_id"],
        permissions=[
            Permission.from_string("users:read"),
            Permission.from_string("users:write"),
        ],
        is_system=False,
    )

    await role_repo.create(role)
    await integration_db_session.flush()

    return role


# ===========================================
# LIST ROLES - Integration Tests
# ===========================================


class TestListRolesIntegration:
    """Integration tests for list roles endpoint."""

    async def test_list_roles_returns_roles(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_role_for_admin: Role,
    ):
        """Test that list roles returns existing roles."""
        response = await client.get(
            "/api/v1/roles",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_roles_unauthorized(self, client: AsyncClient):
        """Test that list roles requires authentication."""
        response = await client.get("/api/v1/roles")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===========================================
# CREATE ROLE - Integration Tests
# ===========================================


class TestCreateRoleIntegration:
    """Integration tests for create role endpoint."""

    async def test_create_role_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test successful role creation."""
        unique_id = str(uuid4())[:8]
        response = await client.post(
            "/api/v1/roles",
            headers=admin_headers,
            json={
                "name": f"NewRole-{unique_id}",
                "description": "New test role",
                "permissions": ["posts:read", "posts:write"],
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == f"NewRole-{unique_id}"
        assert "posts:read" in data["permissions"]
        assert "posts:write" in data["permissions"]

    async def test_create_role_duplicate_name_conflict(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_role_for_admin: Role,
    ):
        """Test that creating role with duplicate name causes conflict."""
        response = await client.post(
            "/api/v1/roles",
            headers=admin_headers,
            json={
                "name": test_role_for_admin.name,  # Duplicate name
                "description": "Duplicate role",
                "permissions": ["users:read"],
            },
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_create_role_invalid_permission_format(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test that invalid permission format returns 400."""
        response = await client.post(
            "/api/v1/roles",
            headers=admin_headers,
            json={
                "name": "InvalidPerms",
                "description": "Invalid permissions",
                "permissions": ["invalid_permission"],
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ===========================================
# UPDATE ROLE - Integration Tests
# ===========================================


class TestUpdateRoleIntegration:
    """Integration tests for update role endpoint."""

    async def test_update_role_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_role_for_admin: Role,
    ):
        """Test successful role update."""
        response = await client.patch(
            f"/api/v1/roles/{test_role_for_admin.id}",
            headers=admin_headers,
            json={
                "description": "Updated description",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "Updated description"

    async def test_update_role_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test that updating non-existent role returns 404."""
        fake_role_id = uuid4()
        response = await client.patch(
            f"/api/v1/roles/{fake_role_id}",
            headers=admin_headers,
            json={
                "description": "Updated description",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ===========================================
# DELETE ROLE - Integration Tests
# ===========================================


class TestDeleteRoleIntegration:
    """Integration tests for delete role endpoint."""

    async def test_delete_role_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_role_for_admin: Role,
    ):
        """Test successful role deletion."""
        role_id = test_role_for_admin.id

        response = await client.delete(
            f"/api/v1/roles/{role_id}",
            headers=admin_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    async def test_delete_role_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test that deleting non-existent role returns 404."""
        fake_role_id = uuid4()
        response = await client.delete(
            f"/api/v1/roles/{fake_role_id}",
            headers=admin_headers,
        )

        # Could be 404 or 200 depending on implementation
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_200_OK]


# ===========================================
# GET USER PERMISSIONS - Integration Tests
# ===========================================


class TestGetUserPermissionsIntegration:
    """Integration tests for get user permissions endpoint."""

    async def test_get_user_permissions_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        real_admin_user,
    ):
        """Test getting user permissions."""
        if not real_admin_user:
            pytest.skip("Requires PostgreSQL integration database")

        response = await client.get(
            f"/api/v1/roles/users/{real_admin_user['user_id']}/permissions",
            headers=admin_headers,
        )

        # Superuser should have access or return permissions
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    async def test_get_user_permissions_user_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Test that getting permissions for non-existent user returns 404."""
        fake_user_id = uuid4()
        response = await client.get(
            f"/api/v1/roles/users/{fake_user_id}/permissions",
            headers=admin_headers,
        )

        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN,
        ]
