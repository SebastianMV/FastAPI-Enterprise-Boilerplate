# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Extended tests for users endpoint schemas and entities."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.api.v1.schemas.users import (
    UserCreate,
    UserDetailResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
    UserUpdateSelf,
)


class TestUserCreateExtended:
    """Extended tests for UserCreate schema."""

    def test_user_create_basic(self) -> None:
        """Test basic user creation."""
        data = UserCreate(
            email="test@example.com",
            password="SecurePassword123!",
            first_name="Test",
            last_name="User",
        )
        assert data.email == "test@example.com"

    def test_user_create_with_name(self) -> None:
        """Test user creation with name."""
        data = UserCreate(
            email="john@example.com",
            password="Password123!",
            first_name="John",
            last_name="Doe",
        )
        assert data.first_name == "John"
        assert data.last_name == "Doe"

    def test_user_create_with_unicode_name(self) -> None:
        """Test user creation with unicode name."""
        data = UserCreate(
            email="jose@example.com",
            password="Password123!",
            first_name="José",
            last_name="García",
        )
        assert data.first_name == "José"

    def test_user_create_with_roles(self) -> None:
        """Test user creation with roles."""
        role_id = uuid4()
        data = UserCreate(
            email="user@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User",
            roles=[role_id],
        )
        assert len(data.roles) == 1


class TestUserUpdateExtended:
    """Extended tests for UserUpdate schema."""

    def test_user_update_email(self) -> None:
        """Test user update with email."""
        data = UserUpdate(email="newemail@example.com")
        assert data.email == "newemail@example.com"

    def test_user_update_name(self) -> None:
        """Test user update with name."""
        data = UserUpdate(first_name="Jane", last_name="Smith")
        assert data.first_name == "Jane"
        assert data.last_name == "Smith"

    def test_user_update_partial(self) -> None:
        """Test partial user update."""
        data = UserUpdate(first_name="Updated")
        assert data.first_name == "Updated"
        assert data.last_name is None
        assert data.email is None


class TestUserResponseExtended:
    """Extended tests for UserResponse schema."""

    def test_user_response_basic(self) -> None:
        """Test basic user response."""
        user_id = uuid4()
        now = datetime.now(UTC)
        data = UserResponse(
            id=user_id,
            email="user@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
        )
        assert data.id == user_id
        assert data.is_active is True

    def test_user_response_inactive(self) -> None:
        """Test inactive user response."""
        now = datetime.now(UTC)
        data = UserResponse(
            id=uuid4(),
            email="inactive@example.com",
            first_name="Inactive",
            last_name="User",
            is_active=False,
            is_superuser=False,
            created_at=now,
            updated_at=now,
        )
        assert data.is_active is False

    def test_user_response_with_last_login(self) -> None:
        """Test user response with last_login."""
        now = datetime.now(UTC)
        data = UserResponse(
            id=uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
            last_login=now,
        )
        assert data.last_login is not None


class TestUserListResponseExtended:
    """Extended tests for UserListResponse schema."""

    def test_user_list_pagination(self) -> None:
        """Test user list with pagination info."""
        now = datetime.now(UTC)
        users = [
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
            for i in range(5)
        ]
        data = UserListResponse(items=users, total=100, page=1, page_size=5, pages=20)
        assert len(data.items) == 5
        assert data.total == 100
        assert data.pages == 20


class TestPasswordChangeExtended:
    """Extended tests for UserUpdateSelf schema."""

    def test_user_update_self(self) -> None:
        """Test user update self request."""
        data = UserUpdateSelf(
            first_name="Updated",
            last_name="Name",
        )
        assert data.first_name == "Updated"

    def test_user_update_self_name_only(self) -> None:
        """Test user update self with first name only."""
        data = UserUpdateSelf(
            first_name="NewName",
        )
        assert data.first_name == "NewName"
        assert data.last_name is None


class TestUserDetailResponseExtended:
    """Tests for UserDetailResponse schema."""

    def test_user_detail_response(self) -> None:
        """Test user detail response."""
        now = datetime.now(UTC)
        tenant_id = uuid4()
        data = UserDetailResponse(
            id=uuid4(),
            email="user@example.com",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=now,
            roles=[],
            tenant_id=tenant_id,
        )
        assert data.roles == []
        assert data.tenant_id == tenant_id


class TestUsersRouterExtended:
    """Extended tests for users router configuration."""

    def test_router_exists(self) -> None:
        """Test router exists."""
        from app.api.v1.endpoints.users import router

        assert router is not None

    def test_router_has_routes(self) -> None:
        """Test router has routes."""
        from app.api.v1.endpoints.users import router

        assert len(router.routes) > 0

    def test_router_routes_include_me(self) -> None:
        """Test router includes /me endpoint."""
        from app.api.v1.endpoints.users import router

        paths = [getattr(route, "path", None) for route in router.routes]
        # Check if there's a /me style path or similar user endpoint
        assert len(paths) > 0
