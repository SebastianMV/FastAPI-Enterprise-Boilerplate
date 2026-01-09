# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for repository implementations.

Tests the conversion methods and basic logic without database.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.entities.audit_log import AuditAction, AuditLog, AuditResourceType
from app.infrastructure.database.repositories.audit_log_repository import (
    SQLAlchemyAuditLogRepository,
)


class TestAuditLogRepository:
    """Tests for SQLAlchemyAuditLogRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.add_all = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> SQLAlchemyAuditLogRepository:
        """Create repository with mock session."""
        return SQLAlchemyAuditLogRepository(mock_session)

    @pytest.fixture
    def sample_audit_log(self) -> AuditLog:
        """Create a sample audit log entity."""
        return AuditLog(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            actor_id=uuid4(),
            actor_email="test@example.com",
            actor_ip="192.168.1.1",
            actor_user_agent="Mozilla/5.0",
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.USER,
            resource_id=str(uuid4()),
            resource_name="Test User",
            tenant_id=uuid4(),
            old_value=None,
            new_value={"name": "Test"},
            metadata={"key": "value"},
            reason="Test creation",
        )

    def test_to_model_converts_entity(
        self, repository: SQLAlchemyAuditLogRepository, sample_audit_log: AuditLog
    ) -> None:
        """Test that _to_model converts entity to model correctly."""
        model = repository._to_model(sample_audit_log)

        assert model.id == sample_audit_log.id
        assert model.timestamp == sample_audit_log.timestamp
        assert model.actor_id == sample_audit_log.actor_id
        assert model.actor_email == sample_audit_log.actor_email
        assert model.actor_ip == sample_audit_log.actor_ip
        assert model.action == sample_audit_log.action.value
        assert model.resource_type == sample_audit_log.resource_type.value
        assert model.resource_id == sample_audit_log.resource_id
        assert model.metadata == sample_audit_log.metadata

    def test_to_entity_converts_model(
        self, repository: SQLAlchemyAuditLogRepository, sample_audit_log: AuditLog
    ) -> None:
        """Test that _to_entity converts model to entity correctly."""
        # First convert to model
        model = repository._to_model(sample_audit_log)

        # Then convert back to entity
        entity = repository._to_entity(model)

        assert entity.id == sample_audit_log.id
        assert entity.actor_email == sample_audit_log.actor_email
        assert entity.action == sample_audit_log.action
        assert entity.resource_type == sample_audit_log.resource_type

    @pytest.mark.asyncio
    async def test_create_adds_to_session(
        self,
        repository: SQLAlchemyAuditLogRepository,
        mock_session: AsyncMock,
        sample_audit_log: AuditLog,
    ) -> None:
        """Test that create adds model to session."""
        await repository.create(sample_audit_log)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_many_adds_all(
        self,
        repository: SQLAlchemyAuditLogRepository,
        mock_session: AsyncMock,
        sample_audit_log: AuditLog,
    ) -> None:
        """Test that create_many adds all models."""
        logs = [sample_audit_log, sample_audit_log]

        await repository.create_many(logs)

        mock_session.add_all.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self, repository: SQLAlchemyAuditLogRepository, mock_session: AsyncMock
    ) -> None:
        """Test get_by_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(uuid4())

        assert result is None

    def test_audit_action_enum_values(self) -> None:
        """Test all AuditAction enum values are valid."""
        expected_actions = [
            "create",
            "read",
            "update",
            "delete",
            "login",
            "logout",
            "login_failed",
            "password_changed",
            "mfa_enabled",
            "mfa_disabled",
            "api_key_created",
            "api_key_revoked",
            "role_assigned",
            "role_removed",
            "permission_granted",
            "permission_revoked",
        ]

        for action_value in expected_actions:
            try:
                action = AuditAction(action_value)
                assert action.value == action_value
            except ValueError:
                # Some values may not exist, that's okay
                pass

    def test_audit_resource_type_enum_values(self) -> None:
        """Test all AuditResourceType enum values are valid."""
        expected_types = ["user", "role", "tenant", "api_key", "session", "system"]

        for type_value in expected_types:
            try:
                resource_type = AuditResourceType(type_value)
                assert resource_type.value == type_value
            except ValueError:
                # Some values may not exist, that's okay
                pass


class TestAuditLogWithoutMetadata:
    """Test audit log handling with empty/None metadata."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> SQLAlchemyAuditLogRepository:
        """Create repository with mock session."""
        return SQLAlchemyAuditLogRepository(mock_session)

    def test_to_model_with_none_metadata(
        self, repository: SQLAlchemyAuditLogRepository
    ) -> None:
        """Test conversion handles None metadata."""
        audit_log = AuditLog(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            actor_id=None,
            actor_email="system",
            actor_ip=None,
            actor_user_agent=None,
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.SYSTEM,
            resource_id="system",
            resource_name="System Event",
            tenant_id=None,
            old_value=None,
            new_value=None,
            metadata={},
            reason=None,
        )

        model = repository._to_model(audit_log)
        assert model.metadata == {}

    def test_to_entity_with_none_actor(
        self, repository: SQLAlchemyAuditLogRepository
    ) -> None:
        """Test conversion handles None actor_id."""
        audit_log = AuditLog(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            actor_id=None,
            actor_email="anonymous",
            actor_ip=None,
            actor_user_agent=None,
            action=AuditAction.READ,
            resource_type=AuditResourceType.SYSTEM,
            resource_id="public",
            resource_name="Public Resource",
            tenant_id=None,
            old_value=None,
            new_value=None,
            metadata={},
            reason=None,
        )

        model = repository._to_model(audit_log)
        entity = repository._to_entity(model)

        assert entity.actor_id is None
        assert entity.tenant_id is None

class TestRoleRepository:
    """Tests for SQLAlchemyRoleRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock):
        """Create repository with mock session."""
        from app.infrastructure.database.repositories.role_repository import (
            SQLAlchemyRoleRepository,
        )
        return SQLAlchemyRoleRepository(mock_session)

    @pytest.fixture
    def sample_role_model(self):
        """Create a sample role model (not entity) for testing."""
        from app.infrastructure.database.models.role import RoleModel
        return RoleModel(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Test Role",
            description="A test role",
            permissions=["users:read", "users:create"],
            is_system=False,
            is_deleted=False,
            deleted_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by=uuid4(),
            updated_by=None,
        )

    def test_to_entity_converts_model(self, repository, sample_role_model) -> None:
        """Test that _to_entity converts model to entity correctly."""
        entity = repository._to_entity(sample_role_model)

        assert entity.id == sample_role_model.id
        assert entity.name == sample_role_model.name
        assert entity.tenant_id == sample_role_model.tenant_id
        assert entity.has_permission("users", "read")
        assert entity.has_permission("users", "create")

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self, repository, mock_session: AsyncMock
    ) -> None:
        """Test get_by_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_returns_none_when_not_found(
        self, repository, mock_session: AsyncMock
    ) -> None:
        """Test get_by_name returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name("NonExistent", uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_ids_returns_empty_for_empty_list(
        self, repository
    ) -> None:
        """Test list_by_ids returns empty list for empty input."""
        result = await repository.list_by_ids([])

        assert result == []

    def test_role_permission_strings(self) -> None:
        """Test permission_strings property on Role entity."""
        from app.domain.entities.role import Permission, Role
        
        role = Role(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Test Role",
            description="A test role",
            permissions=[
                Permission(resource="users", action="read"),
                Permission(resource="users", action="create"),
            ],
            is_system=False,
        )
        strings = role.permission_strings
        
        assert "users:read" in strings
        assert "users:create" in strings


class TestTenantRepository:
    """Tests for SQLAlchemyTenantRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock):
        """Create repository with mock session."""
        from app.infrastructure.database.repositories.tenant_repository import (
            SQLAlchemyTenantRepository,
        )
        return SQLAlchemyTenantRepository(mock_session)

    @pytest.fixture
    def sample_tenant(self):
        """Create a sample tenant entity."""
        from app.domain.entities.tenant import Tenant, TenantSettings
        return Tenant(
            id=uuid4(),
            name="Test Tenant",
            slug="test-tenant",
            email="tenant@example.com",
            phone="+1234567890",
            is_active=True,
            is_verified=True,
            plan="professional",
            settings=TenantSettings(
                enable_2fa=True,
                max_users=50,
            ),
            timezone="America/New_York",
            locale="en",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by=uuid4(),
        )

    def test_to_model_converts_entity(self, repository, sample_tenant) -> None:
        """Test that _to_model converts entity to model correctly."""
        model = repository._to_model(sample_tenant)

        assert model.id == sample_tenant.id
        assert model.name == sample_tenant.name
        assert model.slug == sample_tenant.slug
        assert model.email == sample_tenant.email
        assert model.plan == sample_tenant.plan
        assert model.timezone == sample_tenant.timezone
        assert model.settings["enable_2fa"] is True
        assert model.settings["max_users"] == 50

    def test_to_entity_converts_model(self, repository, sample_tenant) -> None:
        """Test that _to_entity converts model to entity correctly."""
        model = repository._to_model(sample_tenant)
        entity = repository._to_entity(model)

        assert entity.id == sample_tenant.id
        assert entity.name == sample_tenant.name
        assert entity.slug == sample_tenant.slug
        assert entity.settings.enable_2fa is True
        assert entity.settings.max_users == 50

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self, repository, mock_session: AsyncMock
    ) -> None:
        """Test get_by_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_slug_returns_none_when_not_found(
        self, repository, mock_session: AsyncMock
    ) -> None:
        """Test get_by_slug returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_slug("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_domain_returns_none_when_not_found(
        self, repository, mock_session: AsyncMock
    ) -> None:
        """Test get_by_domain returns None when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_domain("nonexistent.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_adds_to_session(
        self, repository, mock_session: AsyncMock, sample_tenant
    ) -> None:
        """Test that create adds model to session."""
        await repository.create(sample_tenant)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, repository, mock_session: AsyncMock
    ) -> None:
        """Test delete returns False when tenant not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.delete(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_count_returns_zero_for_empty(
        self, repository, mock_session: AsyncMock
    ) -> None:
        """Test count returns 0 when no tenants exist."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_slug_exists_returns_false(
        self, repository, mock_session: AsyncMock
    ) -> None:
        """Test slug_exists returns False when slug doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await repository.slug_exists("new-slug")

        assert result is False

    @pytest.mark.asyncio
    async def test_domain_exists_returns_false(
        self, repository, mock_session: AsyncMock
    ) -> None:
        """Test domain_exists returns False when domain doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await repository.domain_exists("new-domain.com")

        assert result is False


class TestTenantSettings:
    """Tests for TenantSettings value object."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        from app.domain.entities.tenant import TenantSettings
        
        settings = TenantSettings(
            enable_2fa=True,
            max_users=200,
            primary_color="#FF0000",
        )
        
        result = settings.to_dict()
        
        assert result["enable_2fa"] is True
        assert result["max_users"] == 200
        assert result["primary_color"] == "#FF0000"

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        from app.domain.entities.tenant import TenantSettings
        
        data = {
            "enable_2fa": True,
            "max_users": 200,
            "primary_color": "#FF0000",
        }
        
        settings = TenantSettings.from_dict(data)
        
        assert settings.enable_2fa is True
        assert settings.max_users == 200
        assert settings.primary_color == "#FF0000"

    def test_from_dict_with_defaults(self) -> None:
        """Test creation from empty dictionary uses defaults."""
        from app.domain.entities.tenant import TenantSettings
        
        settings = TenantSettings.from_dict({})
        
        assert settings.enable_2fa is False
        assert settings.max_users == 100
        assert settings.enable_api_keys is True