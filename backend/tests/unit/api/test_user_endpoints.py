# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for user endpoints module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.users import (
    UserCreate,
    UserDetailResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
    UserUpdateSelf,
)


class TestUserCreateSchema:
    """Tests for UserCreate schema."""

    def test_user_create_minimal(self) -> None:
        """Test user create with minimal fields."""
        data = UserCreate(
            email="test@example.com",
            password="SecurePass123!",
            first_name="John",
            last_name="Doe",
        )
        assert data.email == "test@example.com"
        assert data.first_name == "John"
        assert data.is_active is True
        assert data.is_superuser is False
        assert data.roles == []

    def test_user_create_full(self) -> None:
        """Test user create with all fields."""
        role_id = uuid4()
        data = UserCreate(
            email="admin@example.com",
            password="StrongP@ssw0rd!",
            first_name="Jane",
            last_name="Admin",
            is_active=True,
            is_superuser=True,
            roles=[role_id],
        )
        assert data.email == "admin@example.com"
        assert data.is_superuser is True
        assert len(data.roles) == 1

    def test_user_create_invalid_email_fails(self) -> None:
        """Test user create with invalid email fails."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                password="SecurePass123!",
                first_name="John",
                last_name="Doe",
            )

    def test_user_create_short_password_fails(self) -> None:
        """Test user create with short password fails."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="short",
                first_name="John",
                last_name="Doe",
            )

    def test_user_create_empty_first_name_fails(self) -> None:
        """Test user create with empty first name fails."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="SecurePass123!",
                first_name="",
                last_name="Doe",
            )


class TestUserUpdateSchema:
    """Tests for UserUpdate schema."""

    def test_user_update_partial(self) -> None:
        """Test partial user update."""
        data = UserUpdate(first_name="Updated")
        assert data.first_name == "Updated"
        assert data.email is None
        assert data.last_name is None
        assert data.is_active is None

    def test_user_update_full(self) -> None:
        """Test full user update."""
        role_id = uuid4()
        data = UserUpdate(
            email="new@example.com",
            first_name="New",
            last_name="Name",
            is_active=False,
            roles=[role_id],
        )
        assert data.email == "new@example.com"
        assert data.first_name == "New"
        assert data.is_active is False
        assert data.roles is not None and len(data.roles) == 1

    def test_user_update_empty(self) -> None:
        """Test empty update."""
        data = UserUpdate()
        assert data.email is None
        assert data.first_name is None


class TestUserUpdateSelfSchema:
    """Tests for UserUpdateSelf schema."""

    def test_update_self_name(self) -> None:
        """Test self update with names."""
        data = UserUpdateSelf(first_name="NewFirst", last_name="NewLast")
        assert data.first_name == "NewFirst"
        assert data.last_name == "NewLast"

    def test_update_self_partial(self) -> None:
        """Test partial self update."""
        data = UserUpdateSelf(first_name="OnlyFirst")
        assert data.first_name == "OnlyFirst"
        assert data.last_name is None


class TestUserResponseSchema:
    """Tests for UserResponse schema."""

    def test_user_response_creation(self) -> None:
        """Test user response creation."""
        user_id = uuid4()
        now = datetime.now(UTC)
        response = UserResponse(
            id=user_id,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
        )
        assert response.id == user_id
        assert response.email == "test@example.com"
        assert response.is_active is True
        assert response.last_login is None

    def test_user_response_with_last_login(self) -> None:
        """Test user response with last login."""
        now = datetime.now(UTC)
        response = UserResponse(
            id=uuid4(),
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
            last_login=now,
        )
        assert response.last_login is not None


class TestUserDetailResponseSchema:
    """Tests for UserDetailResponse schema."""

    def test_user_detail_response(self) -> None:
        """Test user detail response."""
        user_id = uuid4()
        tenant_id = uuid4()
        role_id = uuid4()
        now = datetime.now(UTC)
        response = UserDetailResponse(
            id=user_id,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
            roles=[role_id],
            tenant_id=tenant_id,
        )
        assert response.id == user_id
        assert response.tenant_id == tenant_id
        assert len(response.roles) == 1

    def test_user_detail_response_no_roles(self) -> None:
        """Test user detail response without roles."""
        now = datetime.now(UTC)
        response = UserDetailResponse(
            id=uuid4(),
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
            tenant_id=uuid4(),
        )
        assert response.roles == []


class TestUserListResponseSchema:
    """Tests for UserListResponse schema."""

    def test_user_list_response(self) -> None:
        """Test user list response."""
        now = datetime.now(UTC)
        items = [
            UserResponse(
                id=uuid4(),
                email=f"user{i}@example.com",
                first_name=f"User{i}",
                last_name="Test",
                is_active=True,
                is_superuser=False,
                created_at=now,
                updated_at=now,
            )
            for i in range(3)
        ]
        response = UserListResponse(
            items=items,
            total=50,
            page=1,
            page_size=20,
            pages=3,
        )
        assert len(response.items) == 3
        assert response.total == 50
        assert response.pages == 3

    def test_user_list_response_empty(self) -> None:
        """Test empty user list."""
        response = UserListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            pages=0,
        )
        assert len(response.items) == 0
        assert response.total == 0


def create_mock_user(user_id=None, tenant_id=None):
    """Create mock user with all required attributes."""
    if user_id is None:
        user_id = uuid4()
    if tenant_id is None:
        tenant_id = uuid4()
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.tenant_id = tenant_id
    mock_user.email = "test@example.com"
    mock_user.first_name = "Test"
    mock_user.last_name = "User"
    mock_user.avatar_url = None
    mock_user.is_active = True
    mock_user.is_superuser = False
    mock_user.created_at = datetime.now(UTC)
    mock_user.updated_at = datetime.now(UTC)
    mock_user.last_login = None
    mock_user.roles = []
    return mock_user


class TestListUsersEndpoint:
    """Tests for list users endpoint."""

    @pytest.mark.asyncio
    async def test_list_users_success(self) -> None:
        """Test listing users successfully."""
        from app.api.v1.endpoints.users import list_users

        mock_user = create_mock_user()

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = [mock_user]
            mock_repo.count.return_value = 1
            mock_repo_class.return_value = mock_repo

            mock_session = AsyncMock()

            result = await list_users(
                current_user_id=uuid4(),
                session=mock_session,
                page=1,
                page_size=20,
                is_active=None,
            )

            assert result.total == 1
            assert len(result.items) == 1
            assert result.page == 1


class TestGetUserEndpoint:
    """Tests for get user endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_success(self) -> None:
        """Test getting user by ID."""
        from app.api.v1.endpoints.users import get_user

        user_id = uuid4()
        mock_user = create_mock_user(user_id)

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            mock_session = AsyncMock()

            result = await get_user(
                user_id=user_id,
                current_user_id=uuid4(),
                tenant_id=None,
                session=mock_session,
            )

            assert result.id == user_id

    @pytest.mark.asyncio
    async def test_get_user_not_found(self) -> None:
        """Test getting non-existent user."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.users import get_user

        with patch(
            "app.api.v1.endpoints.users.SQLAlchemyUserRepository"
        ) as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            mock_session = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await get_user(
                    user_id=uuid4(),
                    current_user_id=uuid4(),
                    tenant_id=None,
                    session=mock_session,
                )

            assert exc_info.value.status_code == 404


class TestUserEdgeCases:
    """Edge case tests for user schemas."""

    def test_user_create_long_password(self) -> None:
        """Test user create with long password."""
        data = UserCreate(
            email="test@example.com",
            password="A" * 100 + "a1!",
            first_name="John",
            last_name="Doe",
        )
        assert len(data.password) == 103

    def test_user_create_password_too_long_fails(self) -> None:
        """Test user create with password too long."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="x" * 129,
                first_name="John",
                last_name="Doe",
            )

    def test_user_update_with_multiple_roles(self) -> None:
        """Test user update with multiple roles."""
        roles = [uuid4() for _ in range(5)]
        data = UserUpdate(roles=roles)
        assert data.roles is not None and len(data.roles) == 5

    def test_user_response_email_value_object(self) -> None:
        """Test user response handles email value object."""
        now = datetime.now(UTC)

        # Mock email value object
        class MockEmail:
            value = "test@example.com"

        # This tests the validator
        response = UserResponse(
            id=uuid4(),
            email=MockEmail(),  # type: ignore[arg-type]
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
        )
        assert response.email == "test@example.com"

    def test_user_list_pagination_calculation(self) -> None:
        """Test pagination pages calculation."""
        now = datetime.now(UTC)
        # 45 items with page_size 20 = 3 pages
        response = UserListResponse(
            items=[],
            total=45,
            page=1,
            page_size=20,
            pages=3,
        )
        assert response.pages == 3
