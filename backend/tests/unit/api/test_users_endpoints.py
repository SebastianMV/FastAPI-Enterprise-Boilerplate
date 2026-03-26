# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for Users API endpoints.

Tests for user CRUD operations.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


class TestListUsersEndpoint:
    """Tests for /users (list) endpoint."""

    @pytest.mark.asyncio
    async def test_list_users_success(self) -> None:
        """Test listing users successfully."""
        from app.api.v1.endpoints.users import list_users

        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.avatar_url = None
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)
        mock_user.last_login = None

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = [mock_user]
            mock_repo.count.return_value = 1
            mock_repo_class.return_value = mock_repo

            result = await list_users(
                current_user_id=uuid4(),
                session=mock_session,
                page=1,
                page_size=20,
                is_active=None,
            )

        assert result.total == 1
        assert result.page == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_list_users_with_filter(self) -> None:
        """Test listing users with active filter."""
        from app.api.v1.endpoints.users import list_users

        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = []
            mock_repo.count.return_value = 0
            mock_repo_class.return_value = mock_repo

            result = await list_users(
                current_user_id=uuid4(),
                session=mock_session,
                tenant_id=None,
                page=1,
                page_size=20,
                is_active=True,
            )

        mock_repo.list.assert_awaited_once_with(
            skip=0, limit=20, is_active=True, tenant_id=None
        )
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_users_pagination(self) -> None:
        """Test listing users with pagination."""
        from app.api.v1.endpoints.users import list_users

        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = []
            mock_repo.count.return_value = 50
            mock_repo_class.return_value = mock_repo

            result = await list_users(
                current_user_id=uuid4(),
                session=mock_session,
                tenant_id=None,
                page=3,
                page_size=10,
                is_active=None,
            )

        mock_repo.list.assert_awaited_once_with(
            skip=20, limit=10, is_active=None, tenant_id=None
        )
        assert result.pages == 5


class TestGetUserEndpoint:
    """Tests for /users/{user_id} (get) endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_success(self) -> None:
        """Test getting user successfully."""
        from app.api.v1.endpoints.users import get_user

        user_id = uuid4()
        mock_session = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.tenant_id = uuid4()
        mock_user.roles = []
        mock_user.created_at = datetime.now(UTC)
        mock_user.updated_at = datetime.now(UTC)
        mock_user.last_login = None
        mock_user.avatar_url = None
        mock_user.phone_number = None
        mock_user.language = "en"
        mock_user.timezone = "UTC"
        mock_user.mfa_enabled = False
        mock_user.email_verified = True

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            result = await get_user(
                user_id=user_id,
                current_user_id=uuid4(),
                tenant_id=None,
                session=mock_session,
            )

        assert result.id == user_id

    @pytest.mark.asyncio
    async def test_get_user_not_found(self) -> None:
        """Test getting user that doesn't exist."""
        from app.api.v1.endpoints.users import get_user

        user_id = uuid4()
        mock_session = AsyncMock()

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_user(
                    user_id=user_id,
                    current_user_id=uuid4(),
                    tenant_id=None,
                    session=mock_session,
                )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == "USER_NOT_FOUND"  # type: ignore[index]


class TestCreateUserEndpoint:
    """Tests for /users (create) endpoint."""

    def test_create_user_invalid_email_pydantic(self) -> None:
        """Test creating user with invalid email fails at Pydantic."""
        from pydantic import ValidationError

        from app.api.v1.schemas.users import UserCreate

        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="invalid-email",
                password="Password123!",
                first_name="Test",
                last_name="User",
            )

        assert "email" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_user_email_exists(self) -> None:
        """Test creating user with existing email."""
        from app.api.v1.endpoints.users import create_user
        from app.api.v1.schemas.users import UserCreate

        mock_session = AsyncMock()
        request = UserCreate(
            email="existing@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
        )

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.exists_by_email.return_value = True
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await create_user(
                    request=request,
                    superuser_id=uuid4(),
                    tenant_id=uuid4(),
                    session=mock_session,
                )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == "EMAIL_EXISTS"  # type: ignore[index]


class TestUserSchemas:
    """Tests for user schemas."""

    def test_user_create_valid(self) -> None:
        """Test valid UserCreate schema."""
        from app.api.v1.schemas.users import UserCreate

        user = UserCreate(
            email="test@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
        )

        assert user.email == "test@example.com"
        assert user.first_name == "Test"

    def test_user_update_valid(self) -> None:
        """Test valid UserUpdate schema."""
        from app.api.v1.schemas.users import UserUpdate

        update = UserUpdate(
            first_name="Updated",
            last_name="User",
            is_active=False,
        )

        assert update.first_name == "Updated"
        assert update.is_active is False

    def test_user_update_self_valid(self) -> None:
        """Test valid UserUpdateSelf schema."""
        from app.api.v1.schemas.users import UserUpdateSelf

        update = UserUpdateSelf(
            first_name="Self",
            last_name="Update",
        )

        assert update.first_name == "Self"

    def test_user_response_model(self) -> None:
        """Test UserResponse schema."""
        from app.api.v1.schemas.users import UserResponse

        response = UserResponse(
            id=uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_login=None,
        )

        assert response.email == "test@example.com"

    def test_user_list_response(self) -> None:
        """Test UserListResponse schema."""
        from app.api.v1.schemas.users import UserListResponse, UserResponse

        response = UserListResponse(
            items=[
                UserResponse(
                    id=uuid4(),
                    email="test@example.com",
                    first_name="Test",
                    last_name="User",
                    is_active=True,
                    is_superuser=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                    last_login=None,
                )
            ],
            total=1,
            page=1,
            page_size=20,
            pages=1,
        )

        assert len(response.items) == 1
        assert response.total == 1
