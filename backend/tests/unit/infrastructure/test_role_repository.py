# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for SQLAlchemy Role Repository implementation."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.role import Permission, Role
from app.domain.exceptions.base import ConflictError
from app.infrastructure.database.repositories.role_repository import (
    SQLAlchemyRoleRepository,
)


def create_mock_role(
    role_id=None,
    tenant_id=None,
    name="Test Role",
    is_system=False,
):
    """Create a mock Role entity for testing."""
    return Role(
        id=role_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        name=name,
        description="Test description",
        permissions=[Permission(resource="users", action="read")],
        is_system=is_system,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by=uuid4(),
    )


def create_mock_role_model(
    role_id=None,
    tenant_id=None,
    name="Test Role",
    is_system=False,
):
    """Create a mock RoleModel for testing."""
    mock = MagicMock()
    mock.id = role_id or uuid4()
    mock.tenant_id = tenant_id or uuid4()
    mock.name = name
    mock.description = "Test description"
    mock.permissions = ["users:read"]
    mock.is_system = is_system
    mock.created_at = datetime.now(UTC)
    mock.updated_at = datetime.now(UTC)
    mock.created_by = uuid4()
    mock.updated_by = None
    mock.is_deleted = False
    mock.deleted_at = None
    return mock


class TestSQLAlchemyRoleRepositoryInit:
    """Tests for SQLAlchemyRoleRepository initialization."""

    def test_init_with_session(self):
        """Test initialization with session."""
        session = AsyncMock()
        repo = SQLAlchemyRoleRepository(session=session)

        assert repo._session is session


class TestSQLAlchemyRoleRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        """Test getting role by ID when found."""
        session = AsyncMock()
        role_id = uuid4()
        mock_model = create_mock_role_model(role_id=role_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.get_by_id(role_id)

        assert result is not None
        assert result.id == role_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test getting role by ID when not found."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.get_by_id(uuid4())

        assert result is None


class TestSQLAlchemyRoleRepositoryGetByName:
    """Tests for get_by_name method."""

    @pytest.mark.asyncio
    async def test_get_by_name_found(self):
        """Test getting role by name when found."""
        session = AsyncMock()
        tenant_id = uuid4()
        mock_model = create_mock_role_model(name="Admin", tenant_id=tenant_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.get_by_name("Admin", tenant_id)

        assert result is not None
        assert result.name == "Admin"

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self):
        """Test getting role by name when not found."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.get_by_name("NonExistent", uuid4())

        assert result is None


class TestSQLAlchemyRoleRepositoryCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful role creation."""
        session = AsyncMock()
        role = create_mock_role()

        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        repo = SQLAlchemyRoleRepository(session=session)

        with patch.object(repo, "_to_entity", return_value=role):
            result = await repo.create(role)

        assert result is not None
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_name_conflict(self):
        """Test role creation with name conflict."""
        session = AsyncMock()
        role = create_mock_role(name="DuplicateName")

        integrity_error = IntegrityError(
            statement="INSERT",
            params={},
            orig=Exception("duplicate key value"),
        )

        session.add = MagicMock()
        session.flush = AsyncMock(side_effect=integrity_error)
        session.rollback = AsyncMock()

        repo = SQLAlchemyRoleRepository(session=session)

        with pytest.raises(ConflictError) as exc_info:
            await repo.create(role)

        assert "DuplicateName" in exc_info.value.message
        session.rollback.assert_called_once()


class TestSQLAlchemyRoleRepositoryUpdate:
    """Tests for update method."""

    @pytest.mark.asyncio
    async def test_update_success(self):
        """Test successful role update."""
        session = AsyncMock()
        role_id = uuid4()
        role = create_mock_role(role_id=role_id)
        mock_model = create_mock_role_model(role_id=role_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        repo = SQLAlchemyRoleRepository(session=session)

        with patch.object(repo, "_to_entity", return_value=role):
            result = await repo.update(role)

        assert result is not None
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """Test update when role not found."""
        session = AsyncMock()
        role = create_mock_role()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)

        with pytest.raises(Exception):
            await repo.update(role)


class TestSQLAlchemyRoleRepositoryDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """Test successful role soft deletion."""
        session = AsyncMock()
        role_id = uuid4()
        mock_model = create_mock_role_model(role_id=role_id, is_system=False)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = SQLAlchemyRoleRepository(session=session)

        await repo.delete(role_id)

        assert mock_model.is_deleted is True
        assert mock_model.deleted_at is not None
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """Test delete when role not found."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)

        with pytest.raises(Exception):
            await repo.delete(uuid4())

    @pytest.mark.asyncio
    async def test_delete_system_role(self):
        """Test deleting system role raises conflict."""
        session = AsyncMock()
        role_id = uuid4()
        mock_model = create_mock_role_model(role_id=role_id, is_system=True)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)

        with pytest.raises(ConflictError) as exc_info:
            await repo.delete(role_id)

        assert "system role" in exc_info.value.message.lower()


class TestSQLAlchemyRoleRepositoryList:
    """Tests for list method."""

    @pytest.mark.asyncio
    async def test_list_roles(self):
        """Test listing roles for tenant."""
        session = AsyncMock()
        tenant_id = uuid4()
        mock_model1 = create_mock_role_model(tenant_id=tenant_id)
        mock_model2 = create_mock_role_model(tenant_id=tenant_id)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_model1, mock_model2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.list(tenant_id=tenant_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_with_pagination(self):
        """Test listing roles with pagination."""
        session = AsyncMock()
        tenant_id = uuid4()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.list(tenant_id=tenant_id, skip=10, limit=5)

        assert result == []


class TestSQLAlchemyRoleRepositoryListByIds:
    """Tests for list_by_ids method."""

    @pytest.mark.asyncio
    async def test_list_by_ids_success(self):
        """Test listing roles by IDs."""
        session = AsyncMock()
        role_id1 = uuid4()
        role_id2 = uuid4()
        mock_model1 = create_mock_role_model(role_id=role_id1)
        mock_model2 = create_mock_role_model(role_id=role_id2)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_model1, mock_model2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.list_by_ids([role_id1, role_id2])

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_by_ids_empty_list(self):
        """Test listing roles with empty ID list."""
        session = AsyncMock()

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.list_by_ids([])

        assert result == []
        # Should not call execute for empty list
        session.execute.assert_not_called()


class TestSQLAlchemyRoleRepositoryGetUserRoles:
    """Tests for get_user_roles method."""

    @pytest.mark.asyncio
    async def test_get_user_roles_success(self):
        """Test getting user's roles."""
        session = AsyncMock()
        user_id = uuid4()
        role_id1 = uuid4()
        role_id2 = uuid4()

        # First call returns user's role IDs
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = [role_id1, role_id2]

        # Second call returns roles
        mock_model1 = create_mock_role_model(role_id=role_id1)
        mock_model2 = create_mock_role_model(role_id=role_id2)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_model1, mock_model2]
        mock_roles_result = MagicMock()
        mock_roles_result.scalars.return_value = mock_scalars

        session.execute = AsyncMock(side_effect=[mock_user_result, mock_roles_result])

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.get_user_roles(user_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_user_roles_no_roles(self):
        """Test getting roles when user has none."""
        session = AsyncMock()
        user_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyRoleRepository(session=session)
        result = await repo.get_user_roles(user_id)

        assert result == []


class TestSQLAlchemyRoleRepositoryConversion:
    """Tests for entity/model conversion methods."""

    def test_to_entity_conversion(self):
        """Test converting model to entity."""
        session = AsyncMock()
        repo = SQLAlchemyRoleRepository(session=session)

        mock_model = create_mock_role_model()

        entity = repo._to_entity(mock_model)

        assert entity.id == mock_model.id
        assert entity.name == mock_model.name
        assert entity.is_system == mock_model.is_system
        assert len(entity.permissions) == 1

    def test_to_entity_with_empty_permissions(self):
        """Test converting model with empty permissions."""
        session = AsyncMock()
        repo = SQLAlchemyRoleRepository(session=session)

        mock_model = create_mock_role_model()
        mock_model.permissions = None

        entity = repo._to_entity(mock_model)

        assert entity.permissions == []

    def test_to_model_conversion(self):
        """Test converting entity to model."""
        session = AsyncMock()
        repo = SQLAlchemyRoleRepository(session=session)

        role = create_mock_role()

        model = repo._to_model(role)

        assert model.id == role.id
        assert model.name == role.name
        assert model.is_system == role.is_system
