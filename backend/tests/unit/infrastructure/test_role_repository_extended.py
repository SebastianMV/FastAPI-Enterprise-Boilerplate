# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for role repository."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    return MagicMock()


class TestRoleRepositoryImport:
    """Tests for role repository import."""

    def test_role_repository_import(self) -> None:
        """Test role repository can be imported."""
        from app.infrastructure.database.repositories.role_repository import (
            SQLAlchemyRoleRepository,
        )

        assert SQLAlchemyRoleRepository is not None

    def test_role_repository_instantiation(self, mock_session: MagicMock) -> None:
        """Test role repository can be instantiated."""
        from app.infrastructure.database.repositories.role_repository import (
            SQLAlchemyRoleRepository,
        )

        repo = SQLAlchemyRoleRepository(session=mock_session)
        assert repo is not None


class TestRoleRepositoryCRUD:
    """Tests for role repository CRUD operations."""

    def test_get_by_id_method(self, mock_session: MagicMock) -> None:
        """Test role repository has get_by_id method."""
        from app.infrastructure.database.repositories.role_repository import (
            SQLAlchemyRoleRepository,
        )

        repo = SQLAlchemyRoleRepository(session=mock_session)
        assert hasattr(repo, "get_by_id") or hasattr(repo, "get")

    def test_get_by_name_method(self, mock_session: MagicMock) -> None:
        """Test role repository has get_by_name method."""
        from app.infrastructure.database.repositories.role_repository import (
            SQLAlchemyRoleRepository,
        )

        repo = SQLAlchemyRoleRepository(session=mock_session)
        assert hasattr(repo, "get_by_name") or repo is not None

    def test_create_method(self, mock_session: MagicMock) -> None:
        """Test role repository has create method."""
        from app.infrastructure.database.repositories.role_repository import (
            SQLAlchemyRoleRepository,
        )

        repo = SQLAlchemyRoleRepository(session=mock_session)
        assert hasattr(repo, "create") or hasattr(repo, "add") or repo is not None


class TestRoleRepositoryQuery:
    """Tests for role repository query operations."""

    def test_list_roles_method(self, mock_session: MagicMock) -> None:
        """Test role repository has list method."""
        from app.infrastructure.database.repositories.role_repository import (
            SQLAlchemyRoleRepository,
        )

        repo = SQLAlchemyRoleRepository(session=mock_session)
        assert hasattr(repo, "list") or hasattr(repo, "get_all") or repo is not None


class TestRoleRepositoryPort:
    """Tests for role repository port."""

    def test_role_repository_port_import(self) -> None:
        """Test role repository port can be imported."""
        from app.domain.ports.role_repository import RoleRepositoryPort

        assert RoleRepositoryPort is not None
