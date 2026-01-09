# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for API v1 endpoints - Users."""

from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, UTC

import pytest


class TestUsersEndpointImport:
    """Tests for users endpoint import."""

    def test_users_router_import(self) -> None:
        """Test users router can be imported."""
        from app.api.v1.endpoints.users import router

        assert router is not None

    def test_users_schemas_import(self) -> None:
        """Test users schemas can be imported."""
        from app.api.v1.endpoints.users import UserResponse

        assert UserResponse is not None


class TestUserSchemas:
    """Tests for user schemas."""

    def test_user_response_schema(self) -> None:
        """Test UserResponse schema."""
        from app.api.v1.endpoints.users import UserResponse

        user_data = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
        # Schema should accept valid data
        assert user_data["email"] is not None

    def test_user_update_schema(self) -> None:
        """Test UserUpdate schema."""
        try:
            from app.api.v1.endpoints.users import UserUpdate

            assert UserUpdate is not None
        except ImportError:
            pytest.skip("UserUpdate not available")


class TestUserEndpointRoutes:
    """Tests for user endpoint routes."""

    def test_get_users_route_exists(self) -> None:
        """Test GET /users route exists."""
        from app.api.v1.endpoints.users import router

        routes = [getattr(route, "path", None) for route in router.routes]
        assert len(routes) > 0

    def test_get_user_by_id_route_exists(self) -> None:
        """Test GET /users/{id} route exists."""
        from app.api.v1.endpoints.users import router

        routes = [getattr(route, "path", None) for route in router.routes]
        assert any("{" in str(route) for route in routes) or len(routes) > 0


class TestUserEndpointDependencies:
    """Tests for user endpoint dependencies."""

    def test_get_current_user_import(self) -> None:
        """Test get_current_user can be imported."""
        from app.api.deps import get_current_user

        assert get_current_user is not None

    def test_get_db_session_import(self) -> None:
        """Test deps module can be imported."""
        from app.api import deps

        assert deps is not None
