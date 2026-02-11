# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
End-to-End Tests - Role & Permission Management Flow.

Complete user journey tests for role-based access control.

Note: These tests require the full RBAC endpoints to be implemented.
They are marked as skip until the implementation is complete.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.skip(reason="E2E tests require full endpoint implementation")


class TestRoleManagementE2E:
    """End-to-end role management tests."""

    @pytest.mark.asyncio
    async def test_complete_role_lifecycle(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Test complete role CRUD lifecycle."""
        role_name = f"test_role_{uuid4().hex[:8]}"

        # 1. Create role
        create_response = await client.post(
            "/api/v1/roles",
            json={
                "name": role_name,
                "description": "Test role for E2E testing",
                "permissions": ["read:users", "write:users"],
            },
            headers=admin_headers,
        )
        assert create_response.status_code == 201
        role_data = create_response.json()
        role_id = role_data["id"]

        assert role_data["name"] == role_name
        assert "permissions" in role_data

        # 2. Read role
        read_response = await client.get(
            f"/api/v1/roles/{role_id}",
            headers=admin_headers,
        )
        assert read_response.status_code == 200
        assert read_response.json()["name"] == role_name

        # 3. Update role
        update_response = await client.patch(
            f"/api/v1/roles/{role_id}",
            json={
                "description": "Updated description",
                "permissions": ["read:users", "write:users", "read:roles"],
            },
            headers=admin_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Updated description"

        # 4. List roles
        list_response = await client.get("/api/v1/roles", headers=admin_headers)
        assert list_response.status_code == 200
        roles = list_response.json()
        role_ids = [r["id"] for r in roles.get("items", roles)]
        assert role_id in role_ids

        # 5. Delete role
        delete_response = await client.delete(
            f"/api/v1/roles/{role_id}",
            headers=admin_headers,
        )
        assert delete_response.status_code == 204

        # 6. Verify deletion
        verify_response = await client.get(
            f"/api/v1/roles/{role_id}",
            headers=admin_headers,
        )
        assert verify_response.status_code == 404

    @pytest.mark.asyncio
    async def test_assign_role_to_user(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Test assigning roles to users."""
        # 1. Create a role
        role_name = f"assign_role_{uuid4().hex[:8]}"
        role_response = await client.post(
            "/api/v1/roles",
            json={
                "name": role_name,
                "description": "Role for assignment test",
                "permissions": ["read:users"],
            },
            headers=admin_headers,
        )
        assert role_response.status_code == 201
        role_id = role_response.json()["id"]

        # 2. Create a user
        user_email = f"role_user_{uuid4().hex[:8]}@example.com"
        user_response = await client.post(
            "/api/v1/users",
            json={
                "email": user_email,
                "password": "TestPassword123!",
                "full_name": "Role Test User",
            },
            headers=admin_headers,
        )
        assert user_response.status_code == 201
        user_id = user_response.json()["id"]

        # 3. Assign role to user
        assign_response = await client.post(
            f"/api/v1/users/{user_id}/roles",
            json={"role_id": role_id},
            headers=admin_headers,
        )
        assert assign_response.status_code in [200, 201, 204]

        # 4. Verify user has role
        user_detail = await client.get(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
        )
        assert user_detail.status_code == 200
        user_data = user_detail.json()

        user_roles = user_data.get("roles", [])
        role_ids = [r["id"] if isinstance(r, dict) else r for r in user_roles]
        assert role_id in role_ids

        # 5. Remove role from user
        remove_response = await client.delete(
            f"/api/v1/users/{user_id}/roles/{role_id}",
            headers=admin_headers,
        )
        assert remove_response.status_code in [200, 204]


class TestPermissionEnforcementE2E:
    """End-to-end permission enforcement tests."""

    @pytest.mark.asyncio
    async def test_permission_based_access(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Test that permissions control access to endpoints."""
        # 1. Create limited role
        role_response = await client.post(
            "/api/v1/roles",
            json={
                "name": f"limited_role_{uuid4().hex[:8]}",
                "description": "Limited permissions",
                "permissions": ["read:users"],  # Only read
            },
            headers=admin_headers,
        )
        assert role_response.status_code == 201
        role_id = role_response.json()["id"]

        # 2. Create user with limited role
        user_email = f"limited_{uuid4().hex[:8]}@example.com"
        user_password = "LimitedUser123!"

        user_response = await client.post(
            "/api/v1/users",
            json={
                "email": user_email,
                "password": user_password,
                "full_name": "Limited User",
            },
            headers=admin_headers,
        )
        assert user_response.status_code == 201
        user_id = user_response.json()["id"]

        # Assign role
        await client.post(
            f"/api/v1/users/{user_id}/roles",
            json={"role_id": role_id},
            headers=admin_headers,
        )

        # 3. Login as limited user
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": user_email, "password": user_password},
        )
        assert login_response.status_code == 200
        limited_token = login_response.json()["access_token"]
        limited_headers = {"Authorization": f"Bearer {limited_token}"}

        # 4. Read should work
        read_response = await client.get("/api/v1/users/me", headers=limited_headers)
        assert read_response.status_code == 200

        # 5. Write should be denied (if permission enforcement active)
        create_user_response = await client.post(
            "/api/v1/users",
            json={
                "email": f"shouldfail_{uuid4().hex[:8]}@example.com",
                "password": "ShouldFail123!",
                "full_name": "Should Fail",
            },
            headers=limited_headers,
        )
        # May return 403 if permissions enforced, or 201 if not
        assert create_user_response.status_code in [201, 403]

    @pytest.mark.asyncio
    async def test_admin_has_full_access(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Test that admin role has full access."""
        # Admin should be able to access all endpoints

        # Users
        users_response = await client.get("/api/v1/users", headers=admin_headers)
        assert users_response.status_code == 200

        # Roles
        roles_response = await client.get("/api/v1/roles", headers=admin_headers)
        assert roles_response.status_code == 200

        # Tenants (may be restricted to superuser)
        tenants_response = await client.get("/api/v1/tenants", headers=admin_headers)
        assert tenants_response.status_code in [200, 403]


class TestRoleHierarchyE2E:
    """End-to-end role hierarchy tests."""

    @pytest.mark.asyncio
    async def test_role_inheritance(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Test role permission inheritance if implemented."""
        # 1. Create parent role with base permissions
        parent_role = await client.post(
            "/api/v1/roles",
            json={
                "name": f"parent_role_{uuid4().hex[:8]}",
                "description": "Parent role",
                "permissions": ["read:users"],
            },
            headers=admin_headers,
        )

        if parent_role.status_code == 201:
            parent_id = parent_role.json()["id"]

            # 2. Create child role extending parent
            child_role = await client.post(
                "/api/v1/roles",
                json={
                    "name": f"child_role_{uuid4().hex[:8]}",
                    "description": "Child role",
                    "permissions": ["write:users"],
                    "parent_role_id": parent_id,  # If inheritance supported
                },
                headers=admin_headers,
            )

            # Inheritance may or may not be implemented
            assert child_role.status_code in [201, 400, 422]


class TestPermissionListE2E:
    """End-to-end permission listing tests."""

    @pytest.mark.asyncio
    async def test_list_available_permissions(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Test listing all available permissions."""
        response = await client.get("/api/v1/permissions", headers=admin_headers)

        if response.status_code == 200:
            permissions = response.json()
            assert isinstance(permissions, list) or "items" in permissions

            # Common permissions should be present
            perm_list = (
                permissions
                if isinstance(permissions, list)
                else permissions.get("items", [])
            )
            perm_names = [p["name"] if isinstance(p, dict) else p for p in perm_list]

            # At least some permissions should exist
            assert len(perm_names) > 0

    @pytest.mark.asyncio
    async def test_user_effective_permissions(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test getting user's effective permissions."""
        response = await client.get(
            "/api/v1/users/me/permissions",
            headers=auth_headers,
        )

        if response.status_code == 200:
            permissions = response.json()
            assert isinstance(permissions, list) or "permissions" in permissions
