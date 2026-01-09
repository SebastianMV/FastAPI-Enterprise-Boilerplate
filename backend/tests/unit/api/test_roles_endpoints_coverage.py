# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for roles endpoints to improve coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

from app.api.v1.endpoints.roles import (
    list_roles,
    get_role,
    create_role,
    update_role,
    delete_role,
    get_user_permissions,
    assign_role,
    revoke_role,
)
from app.api.v1.schemas.roles import RoleCreate, RoleUpdate, AssignRoleRequest, RevokeRoleRequest
from app.domain.entities.role import Role, Permission
from app.domain.entities.user import User
from app.domain.exceptions.base import ConflictError, EntityNotFoundError


class TestListRolesEndpoint:
    """Tests for list_roles endpoint."""

    @pytest.mark.asyncio
    async def test_list_roles_no_tenant(self) -> None:
        """Test list roles with no tenant context."""
        mock_repo = AsyncMock()
        mock_session = MagicMock()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await list_roles(
                current_user_id=uuid4(),
                tenant_id=None,  # No tenant
                session=mock_session,
                skip=0,
                limit=100,
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 400
        assert "NO_TENANT" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_list_roles_success(self) -> None:
        """Test list roles successfully."""
        tenant_id = uuid4()
        user_id = uuid4()
        
        mock_role = MagicMock()
        mock_role.id = uuid4()
        mock_role.tenant_id = tenant_id
        mock_role.name = "Admin"
        mock_role.description = "Admin role"
        mock_role.permissions = []  # Empty permissions to avoid validation issues
        mock_role.is_system = False
        mock_role.created_at = datetime.now(timezone.utc)
        mock_role.updated_at = datetime.now(timezone.utc)  # Add updated_at
        mock_role.model_dump = MagicMock(return_value={
            "id": mock_role.id,
            "tenant_id": tenant_id,
            "name": "Admin",
            "description": "Admin role",
            "permissions": [],
            "is_system": False,
            "created_at": mock_role.created_at,
            "updated_at": mock_role.updated_at,
        })
        
        mock_repo = AsyncMock()
        mock_repo.list.return_value = [mock_role]
        mock_session = MagicMock()
        
        result = await list_roles(
            current_user_id=user_id,
            tenant_id=tenant_id,
            session=mock_session,
            skip=0,
            limit=100,
            repo=mock_repo,
        )
        
        assert result.total == 1
        mock_repo.list.assert_called_once_with(tenant_id=tenant_id, skip=0, limit=100)

    @pytest.mark.asyncio
    async def test_list_roles_empty(self) -> None:
        """Test list roles returns empty list."""
        tenant_id = uuid4()
        
        mock_repo = AsyncMock()
        mock_repo.list.return_value = []
        mock_session = MagicMock()
        
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
    """Tests for get_role endpoint."""

    @pytest.mark.asyncio
    async def test_get_role_not_found(self) -> None:
        """Test get role when role doesn't exist."""
        role_id = uuid4()
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_session = MagicMock()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await get_role(
                role_id=role_id,
                current_user_id=uuid4(),
                session=mock_session,
                repo=mock_repo,
            )
        
        assert exc.value.status_code == 404
        assert "ROLE_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_get_role_success(self) -> None:
        """Test get role successfully."""
        role_id = uuid4()
        tenant_id = uuid4()
        
        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.tenant_id = tenant_id
        mock_role.name = "Admin"
        mock_role.description = "Admin role"
        mock_role.permissions = []
        mock_role.is_system = False
        mock_role.created_at = datetime.now(timezone.utc)
        mock_role.updated_at = datetime.now(timezone.utc)  # Add updated_at
        mock_role.model_dump = MagicMock(return_value={
            "id": role_id,
            "tenant_id": tenant_id,
            "name": "Admin",
            "description": "Admin role",
            "permissions": [],
            "is_system": False,
            "created_at": mock_role.created_at,
            "updated_at": mock_role.updated_at,
        })
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_role
        mock_session = MagicMock()
        
        result = await get_role(
            role_id=role_id,
            current_user_id=uuid4(),
            session=mock_session,
            repo=mock_repo,
        )
        
        assert result is not None
        mock_repo.get_by_id.assert_called_once_with(role_id)


class TestCreateRoleEndpoint:
    """Tests for create_role endpoint."""

    @pytest.mark.asyncio
    async def test_create_role_no_tenant(self) -> None:
        """Test create role with no tenant context."""
        request = RoleCreate(
            name="TestRole",
            description="Test description",
            permissions=["users:read:own"],
        )
        mock_session = MagicMock()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await create_role(
                request=request,
                superuser_id=uuid4(),
                tenant_id=None,
                session=mock_session,
            )
        
        assert exc.value.status_code == 400
        assert "NO_TENANT" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_create_role_invalid_permission(self) -> None:
        """Test create role with invalid permission format."""
        request = RoleCreate(
            name="TestRole",
            description="Test description",
            permissions=["invalid_permission_format"],
        )
        mock_session = MagicMock()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await create_role(
                request=request,
                superuser_id=uuid4(),
                tenant_id=uuid4(),
                session=mock_session,
            )
        
        assert exc.value.status_code == 400
        assert "INVALID_PERMISSION" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_create_role_conflict(self) -> None:
        """Test create role when role already exists."""
        request = RoleCreate(
            name="Admin",
            description="Admin role",
            permissions=["users:read"],  # Use valid format: resource:action
        )
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.create.side_effect = ConflictError("Role with this name already exists")
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_role(
                    request=request,
                    superuser_id=uuid4(),
                    tenant_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409


class TestUpdateRoleEndpoint:
    """Tests for update_role endpoint."""

    @pytest.mark.asyncio
    async def test_update_role_not_found(self) -> None:
        """Test update role when role doesn't exist."""
        role_id = uuid4()
        request = RoleUpdate(name="NewName")
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_role(
                    role_id=role_id,
                    request=request,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_role_invalid_permission(self) -> None:
        """Test update role with invalid permission format."""
        role_id = uuid4()
        tenant_id = uuid4()
        request = RoleUpdate(permissions=["invalid_format"])
        mock_session = MagicMock()
        
        mock_role = MagicMock(spec=Role)
        mock_role.id = role_id
        mock_role.tenant_id = tenant_id
        mock_role.name = "Admin"
        mock_role.description = "Admin role"
        mock_role.permissions = []
        mock_role.is_system = False
        mock_role.mark_updated = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_role
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_role(
                    role_id=role_id,
                    request=request,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 400
            assert "INVALID_PERMISSION" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_role_entity_not_found(self) -> None:
        """Test update role when entity not found during update."""
        role_id = uuid4()
        tenant_id = uuid4()
        request = RoleUpdate(name="NewName")
        mock_session = MagicMock()
        
        mock_role = MagicMock(spec=Role)
        mock_role.id = role_id
        mock_role.tenant_id = tenant_id
        mock_role.name = "Admin"
        mock_role.description = "Admin role"
        mock_role.permissions = []
        mock_role.is_system = False
        mock_role.mark_updated = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_role
            mock_repo.update.side_effect = EntityNotFoundError("Role not found")
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_role(
                    role_id=role_id,
                    request=request,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404


class TestDeleteRoleEndpoint:
    """Tests for delete_role endpoint."""

    @pytest.mark.asyncio
    async def test_delete_role_not_found(self) -> None:
        """Test delete role when role doesn't exist."""
        role_id = uuid4()
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.delete.side_effect = EntityNotFoundError("Role not found")
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await delete_role(
                    role_id=role_id,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_role_conflict(self) -> None:
        """Test delete system role."""
        role_id = uuid4()
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.delete.side_effect = ConflictError("Cannot delete system role")
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await delete_role(
                    role_id=role_id,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_role_success(self) -> None:
        """Test delete role successfully."""
        role_id = uuid4()
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.delete.return_value = None
            mock_repo_cls.return_value = mock_repo
            
            result = await delete_role(
                role_id=role_id,
                superuser_id=uuid4(),
                session=mock_session,
            )
            
            assert result.success is True
            assert "deleted" in result.message.lower()


class TestGetUserPermissionsEndpoint:
    """Tests for get_user_permissions endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_permissions_user_not_found(self) -> None:
        """Test get permissions for non-existent user."""
        user_id = uuid4()
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_role_cls:
            with patch("app.api.v1.endpoints.roles.SQLAlchemyUserRepository") as mock_user_cls:
                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = None
                mock_user_cls.return_value = mock_user_repo
                
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    await get_user_permissions(
                        user_id=user_id,
                        current_user_id=uuid4(),
                        session=mock_session,
                    )
                
                assert exc.value.status_code == 404
                assert "USER_NOT_FOUND" in str(exc.value.detail)


class TestAssignRoleEndpoint:
    """Tests for assign_role endpoint."""

    @pytest.mark.asyncio
    async def test_assign_role_user_not_found(self) -> None:
        """Test assign role to non-existent user."""
        request = AssignRoleRequest(user_id=uuid4(), role_id=uuid4())
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyUserRepository") as mock_user_cls:
            with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_role_cls:
                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = None
                mock_user_cls.return_value = mock_user_repo
                
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    await assign_role(
                        request=request,
                        superuser_id=uuid4(),
                        session=mock_session,
                    )
                
                assert exc.value.status_code == 404
                assert "USER_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_assign_role_role_not_found(self) -> None:
        """Test assign non-existent role to user."""
        user_id = uuid4()
        request = AssignRoleRequest(user_id=user_id, role_id=uuid4())
        mock_session = MagicMock()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyUserRepository") as mock_user_cls:
            with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_role_cls:
                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = mock_user
                mock_user_cls.return_value = mock_user_repo
                
                mock_role_repo = AsyncMock()
                mock_role_repo.get_by_id.return_value = None
                mock_role_cls.return_value = mock_role_repo
                
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc:
                    await assign_role(
                        request=request,
                        superuser_id=uuid4(),
                        session=mock_session,
                    )
                
                assert exc.value.status_code == 404
                assert "ROLE_NOT_FOUND" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_assign_role_success(self) -> None:
        """Test assign role successfully."""
        user_id = uuid4()
        role_id = uuid4()
        request = AssignRoleRequest(user_id=user_id, role_id=role_id)
        mock_session = MagicMock()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.add_role = MagicMock()
        mock_user.mark_updated = MagicMock()
        
        mock_role = MagicMock()
        mock_role.id = role_id
        mock_role.name = "Admin"
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyUserRepository") as mock_user_cls:
            with patch("app.api.v1.endpoints.roles.SQLAlchemyRoleRepository") as mock_role_cls:
                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = mock_user
                mock_user_repo.update.return_value = mock_user
                mock_user_cls.return_value = mock_user_repo
                
                mock_role_repo = AsyncMock()
                mock_role_repo.get_by_id.return_value = mock_role
                mock_role_cls.return_value = mock_role_repo
                
                result = await assign_role(
                    request=request,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
                
                assert result.success is True
                mock_user.add_role.assert_called_once_with(role_id)


class TestRevokeRoleEndpoint:
    """Tests for revoke_role endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_role_user_not_found(self) -> None:
        """Test revoke role from non-existent user."""
        request = RevokeRoleRequest(user_id=uuid4(), role_id=uuid4())
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyUserRepository") as mock_user_cls:
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_id.return_value = None
            mock_user_cls.return_value = mock_user_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await revoke_role(
                    request=request,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_role_success(self) -> None:
        """Test revoke role successfully."""
        user_id = uuid4()
        role_id = uuid4()
        request = RevokeRoleRequest(user_id=user_id, role_id=role_id)
        mock_session = MagicMock()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.remove_role = MagicMock()
        mock_user.mark_updated = MagicMock()
        
        with patch("app.api.v1.endpoints.roles.SQLAlchemyUserRepository") as mock_user_cls:
            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_id.return_value = mock_user
            mock_user_repo.update.return_value = mock_user
            mock_user_cls.return_value = mock_user_repo
            
            result = await revoke_role(
                request=request,
                superuser_id=uuid4(),
                session=mock_session,
            )
            
            assert result.success is True
            mock_user.remove_role.assert_called_once_with(role_id)
