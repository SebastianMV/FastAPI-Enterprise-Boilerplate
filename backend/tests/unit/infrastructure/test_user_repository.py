# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Unit tests for SQLAlchemy User Repository implementation."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.user import User
from app.domain.exceptions.base import ConflictError
from app.domain.value_objects.email import Email
from app.infrastructure.database.repositories.user_repository import (
    SQLAlchemyUserRepository,
)


def create_mock_user(
    user_id=None,
    tenant_id=None,
    email="test@example.com",
    is_active=True,
):
    """Create a mock User entity for testing."""
    return User(
        id=user_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        email=Email(email),
        password_hash="hashed_password",
        first_name="Test",
        last_name="User",
        is_active=is_active,
        is_superuser=False,
        last_login=None,
        roles=[uuid4()],  # Use UUID instead of string
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by=uuid4(),
    )


def create_mock_user_model(user_id=None, tenant_id=None, email="test@example.com"):
    """Create a mock UserModel for testing."""
    mock = MagicMock()
    mock.id = user_id or uuid4()
    mock.tenant_id = tenant_id or uuid4()
    mock.email = email
    mock.password_hash = "hashed_password"
    mock.first_name = "Test"
    mock.last_name = "User"
    mock.is_active = True
    mock.is_superuser = False
    mock.last_login = None
    mock.roles = [uuid4()]  # Use UUID instead of string
    mock.created_at = datetime.now(UTC)
    mock.updated_at = datetime.now(UTC)
    mock.created_by = uuid4()
    mock.updated_by = None
    mock.is_deleted = False
    mock.deleted_at = None
    mock.deleted_by = None
    mock.tenant = MagicMock()
    mock.oauth_connections = []
    return mock


class TestSQLAlchemyUserRepositoryInit:
    """Tests for SQLAlchemyUserRepository initialization."""

    def test_init_with_session(self):
        """Test initialization with session."""
        session = AsyncMock()
        repo = SQLAlchemyUserRepository(session=session)

        assert repo._session is session


class TestSQLAlchemyUserRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        """Test getting user by ID when found."""
        session = AsyncMock()
        user_id = uuid4()
        mock_model = create_mock_user_model(user_id=user_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.get_by_id(user_id)

        assert result is not None
        assert result.id == user_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test getting user by ID when not found."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.get_by_id(uuid4())

        assert result is None


class TestSQLAlchemyUserRepositoryGetByEmail:
    """Tests for get_by_email method."""

    @pytest.mark.asyncio
    async def test_get_by_email_found(self):
        """Test getting user by email when found."""
        session = AsyncMock()
        email = "test@example.com"
        mock_model = create_mock_user_model(email=email)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.get_by_email(email)

        assert result is not None
        assert str(result.email) == email

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self):
        """Test getting user by email when not found."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.get_by_email("nonexistent@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_normalizes_input(self):
        """Test that email is normalized (lowercase, stripped)."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        await repo.get_by_email("  TEST@EXAMPLE.COM  ")

        # Verify execute was called
        assert session.execute.called


class TestSQLAlchemyUserRepositoryCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful user creation."""
        session = AsyncMock()
        user = create_mock_user()

        # Mock session methods
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        # We need to patch _to_entity to return the user
        repo = SQLAlchemyUserRepository(session=session)

        with patch.object(repo, "_to_entity", return_value=user):
            result = await repo.create(user)

        assert result is not None
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_email_conflict(self):
        """Test user creation with email conflict."""
        session = AsyncMock()
        user = create_mock_user()

        # Mock IntegrityError
        integrity_error = IntegrityError(
            statement="INSERT",
            params={},
            orig=Exception("duplicate key value violates unique constraint email"),
        )

        session.add = MagicMock()
        session.flush = AsyncMock(side_effect=integrity_error)
        session.rollback = AsyncMock()

        repo = SQLAlchemyUserRepository(session=session)

        with pytest.raises(ConflictError) as exc_info:
            await repo.create(user)

        assert "email" in str(exc_info.value.message).lower()
        session.rollback.assert_called_once()


class TestSQLAlchemyUserRepositoryUpdate:
    """Tests for update method."""

    @pytest.mark.asyncio
    async def test_update_success(self):
        """Test successful user update."""
        session = AsyncMock()
        user_id = uuid4()
        user = create_mock_user(user_id=user_id)
        mock_model = create_mock_user_model(user_id=user_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        repo = SQLAlchemyUserRepository(session=session)

        with patch.object(repo, "_to_entity", return_value=user):
            result = await repo.update(user)

        assert result is not None
        session.flush.assert_called_once()
        session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """Test update when user not found."""
        session = AsyncMock()
        user = create_mock_user()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)

        # Test raises some exception when user not found
        with pytest.raises(Exception):
            await repo.update(user)


class TestSQLAlchemyUserRepositoryDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(self):
        """Test successful user soft deletion."""
        session = AsyncMock()
        user_id = uuid4()
        mock_model = create_mock_user_model(user_id=user_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        repo = SQLAlchemyUserRepository(session=session)

        await repo.delete(user_id)

        assert mock_model.is_deleted is True
        assert mock_model.deleted_at is not None
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """Test delete when user not found."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)

        # Test raises some exception when user not found
        with pytest.raises(Exception):
            await repo.delete(uuid4())


class TestSQLAlchemyUserRepositoryList:
    """Tests for list method."""

    @pytest.mark.asyncio
    async def test_list_all_users(self):
        """Test listing all users."""
        session = AsyncMock()
        mock_model1 = create_mock_user_model()
        mock_model2 = create_mock_user_model()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_model1, mock_model2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.list()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_with_pagination(self):
        """Test listing users with pagination."""
        session = AsyncMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.list(skip=10, limit=5)

        assert result == []
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_active_users_only(self):
        """Test listing only active users."""
        session = AsyncMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.list(is_active=True)

        assert result == []


class TestSQLAlchemyUserRepositoryCount:
    """Tests for count method."""

    @pytest.mark.asyncio
    async def test_count_all_users(self):
        """Test counting all users."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.count()

        assert result == 42

    @pytest.mark.asyncio
    async def test_count_active_users(self):
        """Test counting active users only."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.count(is_active=True)

        assert result == 10


class TestSQLAlchemyUserRepositoryExistsByEmail:
    """Tests for exists_by_email method."""

    @pytest.mark.asyncio
    async def test_exists_by_email_true(self):
        """Test exists_by_email when user exists."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.exists_by_email("test@example.com")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_email_false(self):
        """Test exists_by_email when user doesn't exist."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 0
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.exists_by_email("nonexistent@example.com")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_by_email_normalizes_input(self):
        """Test that email is normalized for existence check."""
        session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 1
        session.execute = AsyncMock(return_value=mock_result)

        repo = SQLAlchemyUserRepository(session=session)
        result = await repo.exists_by_email("  TEST@EXAMPLE.COM  ")

        assert result is True


class TestSQLAlchemyUserRepositoryConversion:
    """Tests for entity/model conversion methods."""

    def test_to_entity_conversion(self):
        """Test converting model to entity."""
        session = AsyncMock()
        repo = SQLAlchemyUserRepository(session=session)

        mock_model = create_mock_user_model()

        entity = repo._to_entity(mock_model)

        assert entity.id == mock_model.id
        assert str(entity.email) == mock_model.email
        assert entity.first_name == mock_model.first_name
        assert entity.is_active == mock_model.is_active

    def test_to_model_conversion(self):
        """Test converting entity to model."""
        session = AsyncMock()
        repo = SQLAlchemyUserRepository(session=session)

        user = create_mock_user()

        model = repo._to_model(user)

        assert model.id == user.id
        assert model.email == str(user.email)
        assert model.first_name == user.first_name
        assert model.is_active == user.is_active
