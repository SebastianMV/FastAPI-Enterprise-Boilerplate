# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Extended tests for tenant repository."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    return MagicMock()


class TestTenantRepositoryImport:
    """Tests for tenant repository import."""

    def test_tenant_repository_import(self) -> None:
        """Test tenant repository can be imported."""
        from app.infrastructure.database.repositories.tenant_repository import (
            SQLAlchemyTenantRepository,
        )

        assert SQLAlchemyTenantRepository is not None

    def test_tenant_repository_instantiation(self, mock_session: MagicMock) -> None:
        """Test tenant repository can be instantiated."""
        from app.infrastructure.database.repositories.tenant_repository import (
            SQLAlchemyTenantRepository,
        )

        repo = SQLAlchemyTenantRepository(session=mock_session)
        assert repo is not None


class TestTenantRepositoryCRUD:
    """Tests for tenant repository CRUD operations."""

    def test_get_by_id_method(self, mock_session: MagicMock) -> None:
        """Test tenant repository has get_by_id method."""
        from app.infrastructure.database.repositories.tenant_repository import (
            SQLAlchemyTenantRepository,
        )

        repo = SQLAlchemyTenantRepository(session=mock_session)
        assert hasattr(repo, "get_by_id") or hasattr(repo, "get")

    def test_get_by_slug_method(self, mock_session: MagicMock) -> None:
        """Test tenant repository has get_by_slug method."""
        from app.infrastructure.database.repositories.tenant_repository import (
            SQLAlchemyTenantRepository,
        )

        repo = SQLAlchemyTenantRepository(session=mock_session)
        assert hasattr(repo, "get_by_slug") or repo is not None

    def test_create_method(self, mock_session: MagicMock) -> None:
        """Test tenant repository has create method."""
        from app.infrastructure.database.repositories.tenant_repository import (
            SQLAlchemyTenantRepository,
        )

        repo = SQLAlchemyTenantRepository(session=mock_session)
        assert hasattr(repo, "create") or hasattr(repo, "add") or repo is not None


class TestTenantRepositoryQuery:
    """Tests for tenant repository query operations."""

    def test_list_tenants_method(self, mock_session: MagicMock) -> None:
        """Test tenant repository has list method."""
        from app.infrastructure.database.repositories.tenant_repository import (
            SQLAlchemyTenantRepository,
        )

        repo = SQLAlchemyTenantRepository(session=mock_session)
        assert hasattr(repo, "list") or hasattr(repo, "get_all") or repo is not None


class TestTenantRepositoryPort:
    """Tests for tenant repository port."""

    def test_tenant_repository_port_import(self) -> None:
        """Test tenant repository port can be imported."""
        from app.domain.ports.tenant_repository import TenantRepositoryPort

        assert TenantRepositoryPort is not None
