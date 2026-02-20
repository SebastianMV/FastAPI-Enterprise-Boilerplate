# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
End-to-End Tests - User Management Flow.

Complete user journey tests for user CRUD operations.

Note: These tests require the full user management endpoints to be implemented.
They are marked as skip until the implementation is complete.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.e2e
from uuid import uuid4


class TestUserManagementE2E:
    """End-to-end user management tests."""

    @pytest.mark.asyncio
    async def test_admin_user_crud_flow(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Test complete admin user management flow."""
        # 1. Create new user
        new_user_email = f"created_{uuid4().hex[:8]}@example.com"

        create_response = await client.post(
            "/api/v1/users",
            json={
                "email": new_user_email,
                "password": "NewUserPassword123!",
                "full_name": "Created User",
                "is_active": True,
            },
            headers=admin_headers,
        )
        assert create_response.status_code == 201
        created_user = create_response.json()
        user_id = created_user["id"]

        # 2. Read user
        read_response = await client.get(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
        )
        assert read_response.status_code == 200
        assert read_response.json()["email"] == new_user_email

        # 3. Update user
        update_response = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"full_name": "Updated Name"},
            headers=admin_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["full_name"] == "Updated Name"

        # 4. List users (verify new user appears)
        list_response = await client.get(
            "/api/v1/users",
            headers=admin_headers,
        )
        assert list_response.status_code == 200
        users = list_response.json()
        user_ids = [u["id"] for u in users.get("items", users)]
        assert user_id in user_ids

        # 5. Deactivate user
        deactivate_response = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["is_active"] is False

        # 6. Delete user
        delete_response = await client.delete(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
        )
        assert delete_response.status_code == 204

        # 7. Verify user is deleted
        verify_response = await client.get(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
        )
        assert verify_response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_profile_update_flow(
        self, client: AsyncClient, user_headers: dict
    ) -> None:
        """Test user updating their own profile."""
        # 1. Get current profile
        me_response = await client.get("/api/v1/users/me", headers=user_headers)
        assert me_response.status_code == 200
        original_data = me_response.json()

        # 2. Update profile
        new_name = f"Updated_{uuid4().hex[:8]}"
        update_response = await client.patch(
            "/api/v1/users/me",
            json={"full_name": new_name},
            headers=user_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["full_name"] == new_name

        # 3. Verify update persisted
        verify_response = await client.get("/api/v1/users/me", headers=user_headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["full_name"] == new_name

    @pytest.mark.asyncio
    async def test_user_change_password_flow(self, client: AsyncClient) -> None:
        """Test user changing their password."""
        import uuid

        # 1. Register user
        email = f"pwd_change_{uuid.uuid4().hex[:8]}@example.com"
        original_password = "OriginalPassword123!"
        new_password = "NewSecurePassword456!"

        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": original_password,
                "full_name": "Password Change Test",
            },
        )

        # 2. Login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": original_password},
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Change password
        change_response = await client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": original_password,
                "new_password": new_password,
            },
            headers=headers,
        )
        assert change_response.status_code in [200, 204]

        # 4. Verify old password no longer works
        old_login = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": original_password},
        )
        assert old_login.status_code == 401

        # 5. Verify new password works
        new_login = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": new_password},
        )
        assert new_login.status_code == 200
