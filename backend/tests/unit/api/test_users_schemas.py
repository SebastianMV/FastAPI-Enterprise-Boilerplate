# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for user endpoint schemas."""

from datetime import UTC, datetime
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


class TestUserCreate:
    """Tests for UserCreate schema."""

    def test_user_create_valid(self):
        """Test valid user creation."""
        user = UserCreate(
            email="test@example.com",
            password="securepass123",
            first_name="John",
            last_name="Doe",
        )
        assert user.email == "test@example.com"
        assert user.password == "securepass123"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.roles == []

    def test_user_create_with_roles(self):
        """Test user creation with roles."""
        role_id = uuid4()
        user = UserCreate(
            email="admin@example.com",
            password="adminpass123",
            first_name="Admin",
            last_name="User",
            is_superuser=True,
            roles=[role_id],
        )
        assert user.is_superuser is True
        assert len(user.roles) == 1
        assert user.roles[0] == role_id

    def test_user_create_email_validation(self):
        """Test email validation."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="invalid-email",
                password="password123",
                first_name="John",
                last_name="Doe",
            )

    def test_user_create_password_min_length(self):
        """Test password minimum length."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="short",
                first_name="John",
                last_name="Doe",
            )

    def test_user_create_password_max_length(self):
        """Test password maximum length."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="x" * 129,
                first_name="John",
                last_name="Doe",
            )

    def test_user_create_name_min_length(self):
        """Test name minimum length."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="password123",
                first_name="",
                last_name="Doe",
            )

    def test_user_create_name_max_length(self):
        """Test name maximum length."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="password123",
                first_name="x" * 101,
                last_name="Doe",
            )


class TestUserUpdate:
    """Tests for UserUpdate schema."""

    def test_user_update_empty(self):
        """Test update with no fields."""
        update = UserUpdate()
        assert update.email is None
        assert update.first_name is None
        assert update.last_name is None
        assert update.is_active is None
        assert update.roles is None

    def test_user_update_partial(self):
        """Test update with partial fields."""
        update = UserUpdate(email="new@example.com", is_active=False)
        assert update.email == "new@example.com"
        assert update.is_active is False
        assert update.first_name is None

    def test_user_update_all_fields(self):
        """Test update with all fields."""
        role_id = uuid4()
        update = UserUpdate(
            email="updated@example.com",
            first_name="Updated",
            last_name="User",
            is_active=True,
            roles=[role_id],
        )
        assert update.email == "updated@example.com"
        assert update.first_name == "Updated"
        assert update.roles is not None and len(update.roles) == 1

    def test_user_update_name_validation(self):
        """Test name validation in update."""
        with pytest.raises(ValidationError):
            UserUpdate(first_name="")
        with pytest.raises(ValidationError):
            UserUpdate(last_name="x" * 101)


class TestUserUpdateSelf:
    """Tests for UserUpdateSelf schema."""

    def test_update_self_valid(self):
        """Test valid self update."""
        update = UserUpdateSelf(first_name="NewFirst", last_name="NewLast")
        assert update.first_name == "NewFirst"
        assert update.last_name == "NewLast"

    def test_update_self_partial(self):
        """Test partial self update."""
        update = UserUpdateSelf(first_name="OnlyFirst")
        assert update.first_name == "OnlyFirst"
        assert update.last_name is None

    def test_update_self_empty(self):
        """Test empty self update."""
        update = UserUpdateSelf()
        assert update.first_name is None
        assert update.last_name is None

    def test_update_self_validation(self):
        """Test validation in self update."""
        with pytest.raises(ValidationError):
            UserUpdateSelf(first_name="")


class TestUserResponse:
    """Tests for UserResponse schema."""

    def test_user_response_valid(self):
        """Test valid user response."""
        now = datetime.now(UTC)
        response = UserResponse(
            id=uuid4(),
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
            last_login=None,
        )
        assert response.email == "user@example.com"
        assert response.is_active is True
        assert response.last_login is None

    def test_user_response_with_last_login(self):
        """Test user response with last login."""
        now = datetime.now(UTC)
        response = UserResponse(
            id=uuid4(),
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
            last_login=now,
        )
        assert response.last_login == now

    def test_user_response_superuser(self):
        """Test superuser response."""
        now = datetime.now(UTC)
        response = UserResponse(
            id=uuid4(),
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_superuser=True,
            created_at=now,
            updated_at=now,
        )
        assert response.is_superuser is True


class TestUserDetailResponse:
    """Tests for UserDetailResponse schema."""

    def test_user_detail_response(self):
        """Test user detail response."""
        now = datetime.now(UTC)
        user_id = uuid4()
        tenant_id = uuid4()
        role_id = uuid4()

        response = UserDetailResponse(
            id=user_id,
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
            roles=[role_id],
            tenant_id=tenant_id,
        )
        assert response.tenant_id == tenant_id
        assert len(response.roles) == 1
        assert response.roles[0] == role_id

    def test_user_detail_response_no_roles(self):
        """Test user detail with no roles."""
        now = datetime.now(UTC)
        response = UserDetailResponse(
            id=uuid4(),
            email="user@example.com",
            first_name="John",
            last_name="Doe",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
            tenant_id=uuid4(),
        )
        assert response.roles == []


class TestUserListResponse:
    """Tests for UserListResponse schema."""

    def test_user_list_response(self):
        """Test user list response."""
        now = datetime.now(UTC)
        response = UserListResponse(
            items=[
                UserResponse(
                    id=uuid4(),
                    email="user1@example.com",
                    first_name="User",
                    last_name="One",
                    is_active=True,
                    is_superuser=False,
                    created_at=now,
                    updated_at=now,
                )
            ],
            total=50,
            page=1,
            page_size=20,
            pages=3,
        )
        assert len(response.items) == 1
        assert response.total == 50
        assert response.page == 1
        assert response.pages == 3

    def test_user_list_response_empty(self):
        """Test empty user list."""
        response = UserListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        assert len(response.items) == 0
        assert response.total == 0

    def test_user_list_response_pagination(self):
        """Test user list pagination values."""
        now = datetime.now(UTC)
        response = UserListResponse(items=[], total=100, page=5, page_size=10, pages=10)
        assert response.page == 5
        assert response.page_size == 10
        assert response.pages == 10
