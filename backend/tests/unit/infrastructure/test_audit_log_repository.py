# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for SQLAlchemy Audit Log Repository implementation."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.infrastructure.database.repositories.audit_log_repository import SQLAlchemyAuditLogRepository
from app.domain.entities.audit_log import AuditLog, AuditAction, AuditResourceType


def create_mock_audit_log(
    audit_id=None,
    actor_id=None,
    tenant_id=None,
    action=AuditAction.CREATE,
    resource_type=AuditResourceType.USER,
):
    """Create a mock AuditLog entity for testing."""
    return AuditLog(
        id=audit_id or uuid4(),
        timestamp=datetime.now(UTC),
        actor_id=actor_id or uuid4(),
        actor_email="actor@example.com",
        actor_ip="127.0.0.1",
        actor_user_agent="TestAgent",
        action=action,
        resource_type=resource_type,
        resource_id=str(uuid4()),
        resource_name="Test Resource",
        tenant_id=tenant_id or uuid4(),
        old_value=None,
        new_value={"key": "value"},
        metadata={"extra": "data"},
        reason="Test reason",
    )


def create_mock_audit_log_model(
    audit_id=None,
    actor_id=None,
    tenant_id=None,
    action="CREATE",
    resource_type="user",
):
    """Create a mock AuditLogModel for testing."""
    mock = MagicMock()
    mock.id = audit_id or uuid4()
    mock.timestamp = datetime.now(UTC)
    mock.actor_id = actor_id or uuid4()
    mock.actor_email = "actor@example.com"
    mock.actor_ip = "127.0.0.1"
    mock.actor_user_agent = "TestAgent"
    mock.action = action
    mock.resource_type = resource_type
    mock.resource_id = str(uuid4())
    mock.resource_name = "Test Resource"
    mock.tenant_id = tenant_id or uuid4()
    mock.old_value = None
    mock.new_value = {"key": "value"}
    mock.metadata = {"extra": "data"}
    mock.reason = "Test reason"
    return mock


class TestSQLAlchemyAuditLogRepositoryInit:
    """Tests for SQLAlchemyAuditLogRepository initialization."""

    def test_init_with_session(self):
        """Test initialization with session."""
        session = AsyncMock()
        repo = SQLAlchemyAuditLogRepository(session=session)
        
        assert repo._session is session


class TestSQLAlchemyAuditLogRepositoryCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful audit log creation."""
        session = AsyncMock()
        audit_log = create_mock_audit_log()
        
        session.add = MagicMock()
        session.flush = AsyncMock()
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        
        with patch.object(repo, '_to_entity', return_value=audit_log):
            result = await repo.create(audit_log)
        
        assert result is not None
        session.add.assert_called_once()
        session.flush.assert_called_once()


class TestSQLAlchemyAuditLogRepositoryCreateMany:
    """Tests for create_many method."""

    @pytest.mark.asyncio
    async def test_create_many_success(self):
        """Test successful bulk audit log creation."""
        session = AsyncMock()
        audit_logs = [
            create_mock_audit_log(),
            create_mock_audit_log(),
        ]
        
        session.add_all = MagicMock()
        session.flush = AsyncMock()
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        
        with patch.object(repo, '_to_entity', side_effect=audit_logs):
            result = await repo.create_many(audit_logs)
        
        assert len(result) == 2
        session.add_all.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_many_empty_list(self):
        """Test bulk creation with empty list."""
        session = AsyncMock()
        
        session.add_all = MagicMock()
        session.flush = AsyncMock()
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.create_many([])
        
        assert result == []


class TestSQLAlchemyAuditLogRepositoryGetById:
    """Tests for get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self):
        """Test getting audit log by ID when found."""
        session = AsyncMock()
        audit_id = uuid4()
        mock_model = create_mock_audit_log_model(audit_id=audit_id)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.get_by_id(audit_id)
        
        assert result is not None
        assert result.id == audit_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Test getting audit log by ID when not found."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.get_by_id(uuid4())
        
        assert result is None


class TestSQLAlchemyAuditLogRepositoryListByActor:
    """Tests for list_by_actor method."""

    @pytest.mark.asyncio
    async def test_list_by_actor_success(self):
        """Test listing audit logs by actor."""
        session = AsyncMock()
        actor_id = uuid4()
        mock_model = create_mock_audit_log_model(actor_id=actor_id)
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([mock_model])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_by_actor(actor_id)
        
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_by_actor_with_pagination(self):
        """Test listing with pagination."""
        session = AsyncMock()
        actor_id = uuid4()
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_by_actor(actor_id, limit=50, offset=10)
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_by_actor_with_date_range(self):
        """Test listing with date range filters."""
        session = AsyncMock()
        actor_id = uuid4()
        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_by_actor(
            actor_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        assert len(result) == 0


class TestSQLAlchemyAuditLogRepositoryListByResource:
    """Tests for list_by_resource method."""

    @pytest.mark.asyncio
    async def test_list_by_resource_success(self):
        """Test listing audit logs by resource."""
        session = AsyncMock()
        resource_id = str(uuid4())
        mock_model = create_mock_audit_log_model()
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([mock_model])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_by_resource(
            AuditResourceType.USER,
            resource_id,
        )
        
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_by_resource_with_pagination(self):
        """Test listing by resource with pagination."""
        session = AsyncMock()
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_by_resource(
            AuditResourceType.TENANT,
            str(uuid4()),
            limit=25,
            offset=5,
        )
        
        assert len(result) == 0


class TestSQLAlchemyAuditLogRepositoryListByTenant:
    """Tests for list_by_tenant method."""

    @pytest.mark.asyncio
    async def test_list_by_tenant_success(self):
        """Test listing audit logs by tenant."""
        session = AsyncMock()
        tenant_id = uuid4()
        mock_model = create_mock_audit_log_model(tenant_id=tenant_id)
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([mock_model])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_by_tenant(tenant_id)
        
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_by_tenant_with_action_filter(self):
        """Test listing by tenant with action filter."""
        session = AsyncMock()
        tenant_id = uuid4()
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_by_tenant(
            tenant_id,
            action=AuditAction.CREATE,
        )
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_by_tenant_with_resource_type_filter(self):
        """Test listing by tenant with resource type filter."""
        session = AsyncMock()
        tenant_id = uuid4()
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_by_tenant(
            tenant_id,
            resource_type=AuditResourceType.USER,
        )
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_by_tenant_with_all_filters(self):
        """Test listing by tenant with all filters."""
        session = AsyncMock()
        tenant_id = uuid4()
        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_by_tenant(
            tenant_id,
            limit=50,
            offset=0,
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.ROLE,
            start_date=start_date,
            end_date=end_date,
        )
        
        assert len(result) == 0


class TestSQLAlchemyAuditLogRepositoryCountByTenant:
    """Tests for count_by_tenant method."""

    @pytest.mark.asyncio
    async def test_count_by_tenant_success(self):
        """Test counting audit logs by tenant."""
        session = AsyncMock()
        tenant_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.count_by_tenant(tenant_id)
        
        assert result == 42

    @pytest.mark.asyncio
    async def test_count_by_tenant_with_action_filter(self):
        """Test counting with action filter."""
        session = AsyncMock()
        tenant_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.count_by_tenant(
            tenant_id,
            action=AuditAction.DELETE,
        )
        
        assert result == 10

    @pytest.mark.asyncio
    async def test_count_by_tenant_with_resource_type_filter(self):
        """Test counting with resource type filter."""
        session = AsyncMock()
        tenant_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.count_by_tenant(
            tenant_id,
            resource_type=AuditResourceType.USER,
        )
        
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_by_tenant_with_date_range(self):
        """Test counting with date range."""
        session = AsyncMock()
        tenant_id = uuid4()
        start_date = datetime.now(UTC) - timedelta(days=30)
        end_date = datetime.now(UTC)
        
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.count_by_tenant(
            tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        
        assert result == 100


class TestSQLAlchemyAuditLogRepositoryListRecentLogins:
    """Tests for list_recent_logins method."""

    @pytest.mark.asyncio
    async def test_list_recent_logins_success(self):
        """Test listing recent logins."""
        session = AsyncMock()
        mock_model = create_mock_audit_log_model(action="LOGIN")
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([mock_model])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_recent_logins()
        
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_recent_logins_with_tenant(self):
        """Test listing recent logins for specific tenant."""
        session = AsyncMock()
        tenant_id = uuid4()
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_recent_logins(tenant_id=tenant_id)
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_recent_logins_exclude_failed(self):
        """Test listing logins excluding failed attempts."""
        session = AsyncMock()
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_recent_logins(include_failed=False)
        
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_recent_logins_with_limit(self):
        """Test listing logins with custom limit."""
        session = AsyncMock()
        
        mock_scalars = MagicMock()
        mock_scalars.__iter__ = lambda self: iter([])
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        
        repo = SQLAlchemyAuditLogRepository(session=session)
        result = await repo.list_recent_logins(limit=10)
        
        assert len(result) == 0


class TestSQLAlchemyAuditLogRepositoryConversion:
    """Tests for entity/model conversion methods."""

    def test_to_model_conversion(self):
        """Test converting entity to model."""
        session = AsyncMock()
        repo = SQLAlchemyAuditLogRepository(session=session)
        
        audit_log = create_mock_audit_log()
        
        model = repo._to_model(audit_log)
        
        assert model.id == audit_log.id
        assert model.actor_id == audit_log.actor_id
        assert model.action == audit_log.action.value
        assert model.resource_type == audit_log.resource_type.value

    def test_to_entity_conversion(self):
        """Test converting model to entity."""
        session = AsyncMock()
        repo = SQLAlchemyAuditLogRepository(session=session)
        
        mock_model = create_mock_audit_log_model()
        
        entity = repo._to_entity(mock_model)
        
        assert entity.id == mock_model.id
        assert entity.actor_id == mock_model.actor_id
        assert entity.action == AuditAction(mock_model.action)
        assert entity.resource_type == AuditResourceType(mock_model.resource_type)

    def test_to_entity_with_null_actor_id(self):
        """Test converting model with null actor_id."""
        session = AsyncMock()
        repo = SQLAlchemyAuditLogRepository(session=session)
        
        mock_model = create_mock_audit_log_model()
        mock_model.actor_id = None
        
        entity = repo._to_entity(mock_model)
        
        assert entity.actor_id is None

    def test_to_entity_with_null_tenant_id(self):
        """Test converting model with null tenant_id."""
        session = AsyncMock()
        repo = SQLAlchemyAuditLogRepository(session=session)
        
        mock_model = create_mock_audit_log_model()
        mock_model.tenant_id = None
        
        entity = repo._to_entity(mock_model)
        
        assert entity.tenant_id is None

    def test_to_entity_with_null_metadata(self):
        """Test converting model with null metadata."""
        session = AsyncMock()
        repo = SQLAlchemyAuditLogRepository(session=session)
        
        mock_model = create_mock_audit_log_model()
        mock_model.metadata = None
        
        entity = repo._to_entity(mock_model)
        
        assert entity.metadata == {}
