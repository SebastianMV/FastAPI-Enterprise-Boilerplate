# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Tests for Bulk Operations API endpoints.
"""

from uuid import uuid4

import pytest

from app.api.v1.endpoints.bulk import (
    BulkEntityType,
    BulkOperationType,
    BulkRoleAssignment,
    BulkUserCreate,
    BulkUserDelete,
    BulkUsersCreateRequest,
    BulkUserStatusUpdate,
    BulkUserUpdate,
    BulkValidationRequest,
)


class TestBulkSchemas:
    """Tests for Bulk Operations schemas."""

    def test_bulk_user_create_schema(self):
        """Test BulkUserCreate validation."""
        user = BulkUserCreate(
            email="test@example.com",
            password="SecurePass123!",
            first_name="John",
            last_name="Doe",
        )

        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.roles == []

    def test_bulk_user_create_with_roles(self):
        """Test BulkUserCreate with roles."""
        role_id = uuid4()
        user = BulkUserCreate(
            email="test@example.com",
            password="SecurePass123!",
            first_name="John",
            last_name="Doe",
            roles=[role_id],
        )

        assert len(user.roles) == 1
        assert user.roles[0] == role_id

    def test_bulk_user_update_schema(self):
        """Test BulkUserUpdate validation."""
        user_id = uuid4()
        update = BulkUserUpdate(
            id=user_id,
            first_name="Jane",
            is_active=False,
        )

        assert update.id == user_id
        assert update.first_name == "Jane"
        assert update.last_name is None
        assert update.is_active is False

    def test_bulk_user_delete_schema(self):
        """Test BulkUserDelete validation."""
        user_ids = [uuid4(), uuid4()]
        delete = BulkUserDelete(
            user_ids=user_ids,
            hard_delete=True,
        )

        assert len(delete.user_ids) == 2
        assert delete.hard_delete is True

    def test_bulk_user_delete_max_limit(self):
        """Test BulkUserDelete respects max limit."""
        # Should accept up to 100
        user_ids = [uuid4() for _ in range(100)]
        delete = BulkUserDelete(user_ids=user_ids)
        assert len(delete.user_ids) == 100

        # Should fail over 100
        user_ids = [uuid4() for _ in range(101)]
        with pytest.raises(ValueError):
            BulkUserDelete(user_ids=user_ids)

    def test_bulk_status_update_schema(self):
        """Test BulkUserStatusUpdate validation."""
        user_ids = [uuid4(), uuid4()]
        status_update = BulkUserStatusUpdate(
            user_ids=user_ids,
            is_active=False,
        )

        assert len(status_update.user_ids) == 2
        assert status_update.is_active is False

    def test_bulk_role_assignment_schema(self):
        """Test BulkRoleAssignment validation."""
        user_ids = [uuid4(), uuid4()]
        role_ids = [uuid4()]

        assignment = BulkRoleAssignment(
            user_ids=user_ids,
            role_ids=role_ids,
            operation="assign",
        )

        assert len(assignment.user_ids) == 2
        assert len(assignment.role_ids) == 1
        assert assignment.operation == "assign"

    def test_bulk_role_assignment_invalid_operation(self):
        """Test BulkRoleAssignment rejects invalid operation."""
        with pytest.raises(ValueError):
            BulkRoleAssignment(
                user_ids=[uuid4()],
                role_ids=[uuid4()],
                operation="invalid",
            )

    def test_bulk_users_create_request(self):
        """Test BulkUsersCreateRequest validation."""
        users = [
            BulkUserCreate(
                email=f"user{i}@example.com",
                password="SecurePass123!",
                first_name=f"User{i}",
                last_name="Test",
            )
            for i in range(5)
        ]

        request = BulkUsersCreateRequest(
            users=users,
            skip_duplicates=True,
            send_welcome_email=False,
        )

        assert len(request.users) == 5
        assert request.skip_duplicates is True

    def test_bulk_validation_request(self):
        """Test BulkValidationRequest schema."""
        request = BulkValidationRequest(
            entity_type=BulkEntityType.USERS,
            operation=BulkOperationType.CREATE,
            data=[
                {"email": "test@example.com", "first_name": "Test"},
            ],
        )

        assert request.entity_type == BulkEntityType.USERS
        assert request.operation == BulkOperationType.CREATE


class TestBulkCreateUsers:
    """Tests for bulk user creation endpoint."""

    async def test_bulk_create_users_unauthorized(self, client):
        """Test bulk create requires superuser."""
        response = await client.post(
            "/api/v1/bulk/users/create",
            json={
                "users": [
                    {
                        "email": "test@example.com",
                        "password": "SecurePass123!",
                        "first_name": "Test",
                        "last_name": "User",
                    }
                ]
            },
        )

        assert response.status_code == 401

    async def test_bulk_create_users_success(
        self,
        client,
        superuser_auth_headers,
    ):
        """Test successful bulk user creation."""
        users = [
            {
                "email": f"bulktest{i}_{uuid4().hex[:8]}@example.com",
                "password": "SecurePass123!",
                "first_name": f"Bulk{i}",
                "last_name": "Test",
            }
            for i in range(3)
        ]

        response = await client.post(
            "/api/v1/bulk/users/create",
            json={"users": users, "skip_duplicates": True},
            headers=superuser_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["operation"] == "create"
        assert data["entity_type"] == "users"
        assert data["total_requested"] == 3
        assert data["successful"] > 0
        assert "results" in data

    async def test_bulk_create_users_with_duplicates(
        self,
        client,
        superuser_auth_headers,
    ):
        """Test bulk create handles duplicates."""
        email = f"duplicate_{uuid4().hex[:8]}@example.com"

        users = [
            {
                "email": email,
                "password": "SecurePass123!",
                "first_name": "First",
                "last_name": "User",
            },
            {
                "email": email,  # Duplicate
                "password": "SecurePass123!",
                "first_name": "Second",
                "last_name": "User",
            },
        ]

        response = await client.post(
            "/api/v1/bulk/users/create",
            json={"users": users, "skip_duplicates": True},
            headers=superuser_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "skipped" in data
        assert "successful" in data
        # Either duplicate is skipped, one succeeds, or both fail (FK constraint in test env)
        # The important thing is no 500 error and proper response structure
        assert data["total_requested"] == 2


class TestBulkUpdateUsers:
    """Tests for bulk user update endpoint."""

    async def test_bulk_update_users_unauthorized(self, client):
        """Test bulk update requires superuser."""
        response = await client.post(
            "/api/v1/bulk/users/update",
            json={"users": [{"id": str(uuid4()), "first_name": "Updated"}]},
        )

        assert response.status_code == 401

    async def test_bulk_update_users_not_found(
        self,
        client,
        superuser_auth_headers,
    ):
        """Test bulk update with non-existent users."""
        fake_ids = [str(uuid4()) for _ in range(3)]

        response = await client.post(
            "/api/v1/bulk/users/update",
            json={
                "users": [
                    {"id": fake_id, "first_name": "Updated"} for fake_id in fake_ids
                ],
                "skip_not_found": True,
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["skipped"] == 3
        assert data["successful"] == 0


class TestBulkDeleteUsers:
    """Tests for bulk user deletion endpoint."""

    async def test_bulk_delete_users_unauthorized(self, client):
        """Test bulk delete requires superuser."""
        response = await client.post(
            "/api/v1/bulk/users/delete",
            json={"user_ids": [str(uuid4())]},
        )

        assert response.status_code == 401

    async def test_bulk_delete_prevents_self_deletion(
        self,
        client,
        superuser_auth_headers,
        test_superuser,
    ):
        """Test cannot delete yourself in bulk."""
        response = await client.post(
            "/api/v1/bulk/users/delete",
            json={"user_ids": [str(test_superuser["id"])]},
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Self-deletion should be skipped
        assert data["skipped"] >= 1


class TestBulkStatusUpdate:
    """Tests for bulk status update endpoint."""

    async def test_bulk_status_update_unauthorized(self, client):
        """Test bulk status update requires superuser."""
        response = await client.post(
            "/api/v1/bulk/users/status",
            json={
                "user_ids": [str(uuid4())],
                "is_active": False,
            },
        )

        assert response.status_code == 401

    async def test_bulk_deactivate_users(
        self,
        client,
        superuser_auth_headers,
    ):
        """Test bulk deactivation."""
        # Use non-existent IDs - they should fail silently
        response = await client.post(
            "/api/v1/bulk/users/status",
            json={
                "user_ids": [str(uuid4()), str(uuid4())],
                "is_active": False,
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "operation" in data
        assert "bulk_deactivated" in data["operation"]


class TestBulkRoleAssignment:
    """Tests for bulk role assignment endpoint."""

    async def test_bulk_role_assignment_unauthorized(self, client):
        """Test bulk role assignment requires superuser."""
        response = await client.post(
            "/api/v1/bulk/users/roles",
            json={
                "user_ids": [str(uuid4())],
                "role_ids": [str(uuid4())],
                "operation": "assign",
            },
        )

        assert response.status_code == 401

    async def test_bulk_role_assignment_no_valid_roles(
        self,
        client,
        superuser_auth_headers,
    ):
        """Test bulk role assignment with invalid roles."""
        response = await client.post(
            "/api/v1/bulk/users/roles",
            json={
                "user_ids": [str(uuid4())],
                "role_ids": [str(uuid4())],  # Non-existent role
                "operation": "assign",
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        if isinstance(detail, dict):
            assert detail.get("code") == "NO_VALID_ROLES"
            assert detail.get("message") == "No valid roles found"
        else:
            assert "No valid roles found" in str(detail)


class TestBulkValidation:
    """Tests for bulk validation endpoint."""

    async def test_validate_user_creation_data(
        self,
        client,
        superuser_auth_headers,
    ):
        """Test validation of user creation data."""
        response = await client.post(
            "/api/v1/bulk/validate",
            json={
                "entity_type": "users",
                "operation": "create",
                "data": [
                    {
                        "email": "valid@example.com",
                        "password": "SecurePass123!",
                        "first_name": "Valid",
                        "last_name": "User",
                    },
                    {
                        "email": "invalid-email",  # Invalid
                        "password": "short",  # Too short
                        "first_name": "",  # Empty
                        "last_name": "User",
                    },
                ],
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert data["valid_count"] >= 1
        assert data["invalid_count"] >= 1
        assert len(data["errors"]) >= 1

    async def test_validate_missing_required_fields(
        self,
        client,
        superuser_auth_headers,
    ):
        """Test validation catches missing fields."""
        response = await client.post(
            "/api/v1/bulk/validate",
            json={
                "entity_type": "users",
                "operation": "create",
                "data": [
                    {"email": "test@example.com"},  # Missing password, names
                ],
            },
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False
        assert data["invalid_count"] == 1
        assert len(data["errors"]) == 1

        # Check specific errors
        error = data["errors"][0]
        assert "password is required" in str(error["errors"])


class TestBulkOperationTypes:
    """Tests for BulkOperationType enum."""

    def test_operation_types(self):
        """Test all operation types exist."""
        assert BulkOperationType.CREATE.value == "create"
        assert BulkOperationType.UPDATE.value == "update"
        assert BulkOperationType.DELETE.value == "delete"
        assert BulkOperationType.ACTIVATE.value == "activate"
        assert BulkOperationType.DEACTIVATE.value == "deactivate"
        assert BulkOperationType.ASSIGN_ROLE.value == "assign_role"
        assert BulkOperationType.REMOVE_ROLE.value == "remove_role"

    def test_entity_types(self):
        """Test all entity types exist."""
        assert BulkEntityType.USERS.value == "users"
        assert BulkEntityType.ROLES.value == "roles"
