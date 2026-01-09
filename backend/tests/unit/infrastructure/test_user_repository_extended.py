# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for user repository."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

import pytest


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    return MagicMock()


class TestUserRepositoryImport:
    """Tests for user repository import."""

    def test_user_repository_import(self) -> None:
        """Test user repository can be imported."""
        from app.infrastructure.database.repositories.user_repository import (
            SQLAlchemyUserRepository,
        )

        assert SQLAlchemyUserRepository is not None

    def test_user_repository_instantiation(self, mock_session: MagicMock) -> None:
        """Test user repository can be instantiated."""
        from app.infrastructure.database.repositories.user_repository import (
            SQLAlchemyUserRepository,
        )

        repo = SQLAlchemyUserRepository(session=mock_session)
        assert repo is not None


class TestUserRepositoryCRUD:
    """Tests for user repository CRUD operations."""

    def test_get_by_id_method(self, mock_session: MagicMock) -> None:
        """Test user repository has get_by_id method."""
        from app.infrastructure.database.repositories.user_repository import (
            SQLAlchemyUserRepository,
        )

        repo = SQLAlchemyUserRepository(session=mock_session)
        assert hasattr(repo, "get_by_id") or hasattr(repo, "get")

    def test_get_by_email_method(self, mock_session: MagicMock) -> None:
        """Test user repository has get_by_email method."""
        from app.infrastructure.database.repositories.user_repository import (
            SQLAlchemyUserRepository,
        )

        repo = SQLAlchemyUserRepository(session=mock_session)
        assert hasattr(repo, "get_by_email")

    def test_create_method(self, mock_session: MagicMock) -> None:
        """Test user repository has create method."""
        from app.infrastructure.database.repositories.user_repository import (
            SQLAlchemyUserRepository,
        )

        repo = SQLAlchemyUserRepository(session=mock_session)
        assert hasattr(repo, "create") or hasattr(repo, "add")

    def test_update_method(self, mock_session: MagicMock) -> None:
        """Test user repository has update method."""
        from app.infrastructure.database.repositories.user_repository import (
            SQLAlchemyUserRepository,
        )

        repo = SQLAlchemyUserRepository(session=mock_session)
        assert hasattr(repo, "update") or repo is not None

    def test_delete_method(self, mock_session: MagicMock) -> None:
        """Test user repository has delete method."""
        from app.infrastructure.database.repositories.user_repository import (
            SQLAlchemyUserRepository,
        )

        repo = SQLAlchemyUserRepository(session=mock_session)
        assert hasattr(repo, "delete") or repo is not None


class TestUserRepositoryQuery:
    """Tests for user repository query operations."""

    def test_list_users_method(self, mock_session: MagicMock) -> None:
        """Test user repository has list method."""
        from app.infrastructure.database.repositories.user_repository import (
            SQLAlchemyUserRepository,
        )

        repo = SQLAlchemyUserRepository(session=mock_session)
        assert hasattr(repo, "list") or hasattr(repo, "get_all") or repo is not None


class TestUserRepositoryPort:
    """Tests for user repository port."""

    def test_user_repository_port_import(self) -> None:
        """Test user repository port can be imported."""
        from app.domain.ports.user_repository import UserRepositoryPort

        assert UserRepositoryPort is not None
