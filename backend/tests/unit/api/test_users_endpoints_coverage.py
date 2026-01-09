# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for users endpoints to improve coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.api.v1.endpoints.users import (
    list_users,
    get_user,
    create_user,
    update_user,
    delete_user,
    update_self,
)
from app.api.v1.schemas.users import UserCreate, UserUpdate, UserUpdateSelf
from app.domain.entities.user import User
from app.domain.value_objects.email import Email
from app.domain.exceptions.base import ConflictError, EntityNotFoundError


class TestListUsersEndpoint:
    """Tests for list_users endpoint."""

    @pytest.mark.asyncio
    async def test_list_users_empty(self) -> None:
        """Test list users returns empty list."""
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = []
            mock_repo.count.return_value = 0
            mock_repo_cls.return_value = mock_repo
            
            result = await list_users(
                current_user_id=uuid4(),
                session=mock_session,
                page=1,
                page_size=20,
                is_active=None,
            )
            
            assert result.total == 0
            assert result.items == []
            assert result.page == 1

    @pytest.mark.asyncio
    async def test_list_users_pagination(self) -> None:
        """Test list users with pagination."""
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = []
            mock_repo.count.return_value = 50
            mock_repo_cls.return_value = mock_repo
            
            result = await list_users(
                current_user_id=uuid4(),
                session=mock_session,
                page=3,
                page_size=10,
                is_active=True,
            )
            
            assert result.total == 50
            assert result.pages == 5
            mock_repo.list.assert_called_once_with(skip=20, limit=10, is_active=True)

    @pytest.mark.asyncio
    async def test_list_users_filter_active(self) -> None:
        """Test list users filtered by active status."""
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = []
            mock_repo.count.return_value = 10
            mock_repo_cls.return_value = mock_repo
            
            result = await list_users(
                current_user_id=uuid4(),
                session=mock_session,
                page=1,
                page_size=20,
                is_active=False,
            )
            
            mock_repo.list.assert_called_once()
            mock_repo.count.assert_called_once_with(is_active=False)


class TestGetUserEndpoint:
    """Tests for get_user endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_not_found(self) -> None:
        """Test get user when user doesn't exist."""
        user_id = uuid4()
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await get_user(
                    user_id=user_id,
                    current_user_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404
            assert "USER_NOT_FOUND" in str(exc.value.detail)


class TestCreateUserEndpoint:
    """Tests for create_user endpoint."""

    @pytest.mark.asyncio
    async def test_create_user_email_exists(self) -> None:
        """Test create user with existing email."""
        request = UserCreate(
            email="existing@example.com",
            password="StrongPass1!",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
        )
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.exists_by_email.return_value = True
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_user(
                    request=request,
                    superuser_id=uuid4(),
                    tenant_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409
            assert "EMAIL_EXISTS" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_create_user_conflict_error(self) -> None:
        """Test create user with conflict during creation."""
        request = UserCreate(
            email="new@example.com",
            password="StrongPass1!",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
        )
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.exists_by_email.return_value = False
            mock_repo.create.side_effect = ConflictError("Conflict error")
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await create_user(
                    request=request,
                    superuser_id=uuid4(),
                    tenant_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409


class TestUpdateUserEndpoint:
    """Tests for update_user endpoint."""

    @pytest.mark.asyncio
    async def test_update_user_not_found(self) -> None:
        """Test update user when user doesn't exist."""
        user_id = uuid4()
        request = UserUpdate(first_name="NewName")
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_user(
                    user_id=user_id,
                    request=request,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_email_exists(self) -> None:
        """Test update user with existing email."""
        user_id = uuid4()
        request = UserUpdate(email="existing@example.com")
        mock_session = MagicMock()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.exists_by_email.return_value = True
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_user(
                    user_id=user_id,
                    request=request,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 409
            assert "EMAIL_EXISTS" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_entity_not_found(self) -> None:
        """Test update user when entity not found during update."""
        user_id = uuid4()
        request = UserUpdate(first_name="NewName")
        mock_session = MagicMock()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.first_name = "OldName"
        mock_user.mark_updated = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.side_effect = EntityNotFoundError("User not found")
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_user(
                    user_id=user_id,
                    request=request,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404


class TestDeleteUserEndpoint:
    """Tests for delete_user endpoint."""

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self) -> None:
        """Test delete user when user doesn't exist."""
        user_id = uuid4()
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.delete.side_effect = EntityNotFoundError("User not found")
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await delete_user(
                    user_id=user_id,
                    superuser_id=uuid4(),
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user_success(self) -> None:
        """Test delete user successfully."""
        user_id = uuid4()
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.delete.return_value = None
            mock_repo_cls.return_value = mock_repo
            
            result = await delete_user(
                user_id=user_id,
                superuser_id=uuid4(),
                session=mock_session,
            )
            
            assert result.success is True
            assert "deleted" in result.message.lower()


class TestUpdateSelfEndpoint:
    """Tests for update_self endpoint."""

    @pytest.mark.asyncio
    async def test_update_self_not_found(self) -> None:
        """Test update self when user doesn't exist."""
        user_id = uuid4()
        request = UserUpdateSelf(first_name="NewName")
        mock_session = MagicMock()
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_cls.return_value = mock_repo
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await update_self(
                    request=request,
                    current_user_id=user_id,
                    session=mock_session,
                )
            
            assert exc.value.status_code == 404


class TestUpdateUserFieldVariations:
    """Tests for various update field combinations."""

    @pytest.mark.asyncio
    async def test_update_user_all_fields(self) -> None:
        """Test update user with all optional fields."""
        user_id = uuid4()
        request = UserUpdate(
            first_name="NewFirst",
            last_name="NewLast",
            is_active=False,
            roles=[uuid4()],
        )
        mock_session = MagicMock()
        
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.first_name = "OldFirst"
        mock_user.last_name = "OldLast"
        mock_user.is_active = True
        mock_user.roles = []
        mock_user.mark_updated = MagicMock()
        mock_user.model_dump = MagicMock(return_value={})
        
        updated_user = MagicMock()
        updated_user.id = user_id
        updated_user.tenant_id = uuid4()
        updated_user.email = "test@example.com"
        updated_user.first_name = "NewFirst"
        updated_user.last_name = "NewLast"
        updated_user.avatar_url = None
        updated_user.is_active = False
        updated_user.is_superuser = False
        updated_user.roles = []
        updated_user.created_at = datetime.now(timezone.utc)
        updated_user.updated_at = datetime.now(timezone.utc)
        updated_user.last_login = None
        updated_user.model_dump = MagicMock(return_value={
            "id": user_id,
            "tenant_id": updated_user.tenant_id,
            "email": "test@example.com",
            "first_name": "NewFirst",
            "last_name": "NewLast",
            "avatar_url": None,
            "is_active": False,
            "is_superuser": False,
            "roles": [],
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at,
        })
        
        with patch("app.api.v1.endpoints.users.SQLAlchemyUserRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = updated_user
            mock_repo_cls.return_value = mock_repo
            
            result = await update_user(
                user_id=user_id,
                request=request,
                superuser_id=uuid4(),
                session=mock_session,
            )
            
            assert result is not None
            # Verify all fields were updated
            assert mock_user.first_name == "NewFirst"
            assert mock_user.last_name == "NewLast"
            assert mock_user.is_active is False
