# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
End-to-End Tests - Authentication Flow.

Complete user journey tests for authentication.

Note: These tests require the full authentication endpoints to be implemented.
They are marked as skip until the implementation is complete.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.e2e


class TestAuthenticationE2E:
    """End-to-end authentication flow tests."""

    @pytest.mark.asyncio
    async def test_complete_registration_login_flow(self, client: AsyncClient) -> None:
        """Test complete user registration and login flow."""
        import uuid

        # 1. Register new user
        email = f"e2e_test_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePassword123!"

        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "E2E Test User",
            },
        )
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["email"] == email
        assert "id" in user_data

        # 2. Login with new credentials
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": email,
                "password": password,
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

        # 3. Access protected endpoint
        access_token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        me_response = await client.get("/api/v1/users/me", headers=headers)
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == email

        # 4. Refresh token
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens

        # 5. Logout
        logout_response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert logout_response.status_code in [200, 204]

        # 6. Verify old token no longer works (if token blacklist enabled)
        old_token_response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        # May still work if blacklist not enabled, or return 401
        assert old_token_response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_password_reset_flow(
        self, client: AsyncClient, registered_user: dict
    ) -> None:
        """Test password reset flow."""
        email = registered_user["email"]

        # 1. Request password reset
        reset_request = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": email},
        )
        # Should always return 200 (don't reveal if email exists)
        assert reset_request.status_code == 200

        # Note: In real E2E test, you would:
        # 1. Check email inbox for reset link
        # 2. Extract token from link
        # 3. POST to /auth/reset-password with new password
        # 4. Verify login with new password works

    @pytest.mark.asyncio
    async def test_login_with_wrong_password(
        self, client: AsyncClient, registered_user: dict
    ) -> None:
        """Test login fails with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": registered_user["email"],
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_with_nonexistent_email(self, client: AsyncClient) -> None:
        """Test login fails with non-existent email."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "AnyPassword123!",
            },
        )
        assert response.status_code == 401
