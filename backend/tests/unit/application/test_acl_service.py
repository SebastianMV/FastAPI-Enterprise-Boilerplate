# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Unit tests for ACL Service."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.services.acl_service import (
    DEFAULT_ROLES,
    ACLService,
    create_default_roles,
)
from app.domain.entities.role import Permission, Role
from app.domain.exceptions.base import AuthorizationError


@pytest.fixture
def mock_role_repository():
    """Create mock role repository."""
    return AsyncMock()


@pytest.fixture
def acl_service(mock_role_repository):
    """Create ACL service with mock repository."""
    return ACLService(mock_role_repository)


class TestACLService:
    """Tests for ACL Service."""

    @pytest.mark.asyncio
    async def test_check_permission_superuser(self, acl_service):
        """Test superuser bypasses permission check."""
        result = await acl_service.check_permission(
            user_id=uuid4(),
            resource="anything",
            action="anything",
            is_superuser=True,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_has_permission(
        self, acl_service, mock_role_repository
    ):
        """Test user with permission returns True."""
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=[Permission(resource="users", action="read")],
        )
        mock_role_repository.get_user_roles.return_value = [role]

        result = await acl_service.check_permission(
            user_id=uuid4(),
            resource="users",
            action="read",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_no_permission(
        self, acl_service, mock_role_repository
    ):
        """Test user without permission returns False."""
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=[Permission(resource="users", action="read")],
        )
        mock_role_repository.get_user_roles.return_value = [role]

        result = await acl_service.check_permission(
            user_id=uuid4(),
            resource="users",
            action="delete",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_no_roles(self, acl_service, mock_role_repository):
        """Test user with no roles returns False."""
        mock_role_repository.get_user_roles.return_value = []

        result = await acl_service.check_permission(
            user_id=uuid4(),
            resource="users",
            action="read",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_require_permission_success(self, acl_service, mock_role_repository):
        """Test require_permission passes with valid permission."""
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=[Permission(resource="users", action="read")],
        )
        mock_role_repository.get_user_roles.return_value = [role]

        # Should not raise
        await acl_service.require_permission(
            user_id=uuid4(),
            resource="users",
            action="read",
        )

    @pytest.mark.asyncio
    async def test_require_permission_failure(self, acl_service, mock_role_repository):
        """Test require_permission raises without permission."""
        mock_role_repository.get_user_roles.return_value = []

        with pytest.raises(AuthorizationError) as exc_info:
            await acl_service.require_permission(
                user_id=uuid4(),
                resource="users",
                action="delete",
            )

        assert exc_info.value.resource == "users"
        assert exc_info.value.action == "delete"

    @pytest.mark.asyncio
    async def test_get_user_permissions_superuser(self, acl_service):
        """Test superuser gets wildcard permission."""
        permissions = await acl_service.get_user_permissions(
            user_id=uuid4(),
            is_superuser=True,
        )

        assert permissions == ["*:*"]

    @pytest.mark.asyncio
    async def test_get_user_permissions(self, acl_service, mock_role_repository):
        """Test getting user permissions from roles."""
        role1 = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="role1",
            permissions=[
                Permission(resource="users", action="read"),
                Permission(resource="users", action="create"),
            ],
        )
        role2 = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="role2",
            permissions=[
                Permission(resource="roles", action="read"),
                Permission(resource="users", action="read"),  # Duplicate
            ],
        )
        mock_role_repository.get_user_roles.return_value = [role1, role2]

        permissions = await acl_service.get_user_permissions(user_id=uuid4())

        # Should be unique and sorted
        assert "users:read" in permissions
        assert "users:create" in permissions
        assert "roles:read" in permissions
        assert len(permissions) == 3  # No duplicates

    @pytest.mark.asyncio
    async def test_can_access_resources_any(self, acl_service, mock_role_repository):
        """Test can_access_resources with require_all=False."""
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=[Permission(resource="users", action="read")],
        )
        mock_role_repository.get_user_roles.return_value = [role]

        # Has one of the permissions
        result = await acl_service.can_access_resources(
            user_id=uuid4(),
            permissions=[("users", "read"), ("roles", "read")],
            require_all=False,
        )

        assert result is True

        # Has none of the permissions
        result = await acl_service.can_access_resources(
            user_id=uuid4(),
            permissions=[("settings", "read"), ("logs", "read")],
            require_all=False,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_can_access_resources_all(self, acl_service, mock_role_repository):
        """Test can_access_resources with require_all=True."""
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="test",
            permissions=[
                Permission(resource="users", action="read"),
                Permission(resource="roles", action="read"),
            ],
        )
        mock_role_repository.get_user_roles.return_value = [role]

        # Has all permissions
        result = await acl_service.can_access_resources(
            user_id=uuid4(),
            permissions=[("users", "read"), ("roles", "read")],
            require_all=True,
        )

        assert result is True

        # Missing one permission
        result = await acl_service.can_access_resources(
            user_id=uuid4(),
            permissions=[("users", "read"), ("settings", "read")],
            require_all=True,
        )

        assert result is False


class TestCreateDefaultRoles:
    """Tests for create_default_roles."""

    def test_creates_all_default_roles(self):
        """Test all default roles are created."""
        tenant_id = uuid4()
        roles = create_default_roles(tenant_id)

        assert len(roles) == len(DEFAULT_ROLES)

        role_names = {r.name for r in roles}
        assert "admin" in role_names
        assert "manager" in role_names
        assert "viewer" in role_names

    def test_roles_are_system_roles(self):
        """Test created roles are marked as system."""
        tenant_id = uuid4()
        roles = create_default_roles(tenant_id)

        for role in roles:
            assert role.is_system is True

    def test_roles_have_tenant_id(self):
        """Test created roles have correct tenant_id."""
        tenant_id = uuid4()
        roles = create_default_roles(tenant_id)

        for role in roles:
            assert role.tenant_id == tenant_id

    def test_admin_has_full_permissions(self):
        """Test admin role has wildcard permission."""
        tenant_id = uuid4()
        roles = create_default_roles(tenant_id)

        admin_role = next(r for r in roles if r.name == "admin")

        # Admin should have *:* permission
        assert admin_role.has_permission("anything", "anything") is True
