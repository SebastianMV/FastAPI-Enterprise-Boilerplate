# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for ACL service with real execution."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.services.acl_service import ACLService
from app.domain.entities.role import Permission, Role
from app.domain.exceptions.base import AuthorizationError


class TestACLServiceCheckPermission:
    """Tests for ACLService.check_permission method."""

    @pytest.mark.asyncio
    async def test_check_permission_superuser_always_true(self) -> None:
        """Test that superuser always has permission."""
        mock_repo = AsyncMock()
        service = ACLService(role_repository=mock_repo)

        user_id = uuid4()
        result = await service.check_permission(
            user_id=user_id, resource="users", action="delete", is_superuser=True
        )

        assert result is True
        # Repository should not be called for superuser
        mock_repo.get_user_roles.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_permission_no_roles_returns_false(self) -> None:
        """Test that user with no roles returns False."""
        mock_repo = AsyncMock()
        mock_repo.get_user_roles.return_value = []
        service = ACLService(role_repository=mock_repo)

        user_id = uuid4()
        result = await service.check_permission(
            user_id=user_id, resource="users", action="delete"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_with_matching_role(self) -> None:
        """Test that user with matching permission returns True."""
        mock_repo = AsyncMock()
        tenant_id = uuid4()
        role = Role(
            tenant_id=tenant_id,
            name="Admin",
            permissions=[Permission(resource="users", action="delete")],
        )
        mock_repo.get_user_roles.return_value = [role]
        service = ACLService(role_repository=mock_repo)

        user_id = uuid4()
        result = await service.check_permission(
            user_id=user_id, resource="users", action="delete"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_no_matching_permission(self) -> None:
        """Test that user without matching permission returns False."""
        mock_repo = AsyncMock()
        tenant_id = uuid4()
        role = Role(
            tenant_id=tenant_id,
            name="Reader",
            permissions=[Permission(resource="users", action="read")],
        )
        mock_repo.get_user_roles.return_value = [role]
        service = ACLService(role_repository=mock_repo)

        user_id = uuid4()
        result = await service.check_permission(
            user_id=user_id,
            resource="users",
            action="delete",  # Different action
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_wildcard_resource(self) -> None:
        """Test that wildcard resource permission matches all."""
        mock_repo = AsyncMock()
        tenant_id = uuid4()
        role = Role(
            tenant_id=tenant_id,
            name="SuperAdmin",
            permissions=[Permission(resource="*", action="*")],
        )
        mock_repo.get_user_roles.return_value = [role]
        service = ACLService(role_repository=mock_repo)

        user_id = uuid4()
        result = await service.check_permission(
            user_id=user_id, resource="any_resource", action="any_action"
        )

        assert result is True


class TestACLServiceRequirePermission:
    """Tests for ACLService.require_permission method."""

    @pytest.mark.asyncio
    async def test_require_permission_superuser_passes(self) -> None:
        """Test that superuser passes require_permission."""
        mock_repo = AsyncMock()
        service = ACLService(role_repository=mock_repo)

        user_id = uuid4()
        # Should not raise
        await service.require_permission(
            user_id=user_id, resource="users", action="delete", is_superuser=True
        )

    @pytest.mark.asyncio
    async def test_require_permission_raises_without_permission(self) -> None:
        """Test that require_permission raises AuthorizationError."""
        mock_repo = AsyncMock()
        mock_repo.get_user_roles.return_value = []
        service = ACLService(role_repository=mock_repo)

        user_id = uuid4()
        with pytest.raises(AuthorizationError) as exc_info:
            await service.require_permission(
                user_id=user_id, resource="users", action="delete"
            )

        assert "Permission denied" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_require_permission_passes_with_permission(self) -> None:
        """Test that require_permission passes with valid permission."""
        mock_repo = AsyncMock()
        tenant_id = uuid4()
        role = Role(
            tenant_id=tenant_id,
            name="Admin",
            permissions=[Permission(resource="users", action="delete")],
        )
        mock_repo.get_user_roles.return_value = [role]
        service = ACLService(role_repository=mock_repo)

        user_id = uuid4()
        # Should not raise
        await service.require_permission(
            user_id=user_id, resource="users", action="delete"
        )


class TestACLServiceMultipleRoles:
    """Tests for ACL service with multiple roles."""

    @pytest.mark.asyncio
    async def test_permission_found_in_second_role(self) -> None:
        """Test that permission is found when in second role."""
        mock_repo = AsyncMock()
        tenant_id = uuid4()
        role1 = Role(
            tenant_id=tenant_id,
            name="Reader",
            permissions=[Permission(resource="users", action="read")],
        )
        role2 = Role(
            tenant_id=tenant_id,
            name="Writer",
            permissions=[Permission(resource="users", action="write")],
        )
        mock_repo.get_user_roles.return_value = [role1, role2]
        service = ACLService(role_repository=mock_repo)

        user_id = uuid4()
        result = await service.check_permission(
            user_id=user_id, resource="users", action="write"
        )

        assert result is True
