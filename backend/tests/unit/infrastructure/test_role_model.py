# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for Role SQLAlchemy model."""

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.infrastructure.database.connection import Base
from app.infrastructure.database.models.role import RoleModel, JSONEncodedList


@pytest.fixture
def sqlite_session():
    """Create SQLite in-memory session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_role_data():
    """Sample role data for testing."""
    tenant_id = uuid4()
    return {
        "tenant_id": tenant_id,
        "name": "admin",
        "description": "Administrator role",
        "permissions": ["users:read", "users:write", "users:delete"],
        "is_system": True,
        "created_by": uuid4(),
        "updated_by": uuid4(),
    }


class TestRoleModelCreation:
    """Test Role model creation and basic attributes."""
    
    def test_create_role_with_all_fields(self, sqlite_session, sample_role_data):
        """Test creating a role with all fields."""
        role = RoleModel(**sample_role_data)
        sqlite_session.add(role)
        sqlite_session.commit()
        
        assert role.id is not None
        assert isinstance(role.id, UUID)
        assert role.tenant_id == sample_role_data["tenant_id"]
        assert role.name == "admin"
        assert role.description == "Administrator role"
        assert role.permissions == ["users:read", "users:write", "users:delete"]
        assert role.is_system is True
        assert role.is_deleted is False
        assert role.deleted_at is None
        assert role.created_at is not None
        assert role.updated_at is not None
    
    def test_create_role_with_minimal_fields(self, sqlite_session):
        """Test creating a role with only required fields."""
        role = RoleModel(
            tenant_id=uuid4(),
            name="user",
        )
        sqlite_session.add(role)
        sqlite_session.commit()
        
        assert role.id is not None
        assert role.name == "user"
        assert role.description == ""
        assert role.permissions == []
        assert role.is_system is False
        assert role.is_deleted is False
    
    def test_role_with_empty_permissions(self, sqlite_session):
        """Test role with empty permissions list."""
        role = RoleModel(
            tenant_id=uuid4(),
            name="viewer",
            permissions=[],
        )
        sqlite_session.add(role)
        sqlite_session.commit()
        
        assert role.permissions == []
    
    def test_role_with_multiple_permissions(self, sqlite_session):
        """Test role with many permissions."""
        permissions = [
            "users:read",
            "users:write",
            "roles:read",
            "roles:write",
            "tenants:read",
        ]
        role = RoleModel(
            tenant_id=uuid4(),
            name="super_admin",
            permissions=permissions,
        )
        sqlite_session.add(role)
        sqlite_session.commit()
        
        assert role.permissions == permissions
        assert len(role.permissions) == 5


class TestRoleModelSoftDelete:
    """Test soft delete functionality."""
    
    def test_role_not_deleted_by_default(self, sqlite_session):
        """Test that role is not deleted by default."""
        role = RoleModel(
            tenant_id=uuid4(),
            name="user",
        )
        sqlite_session.add(role)
        sqlite_session.commit()
        
        assert role.is_deleted is False
        assert role.deleted_at is None
    
    def test_mark_role_as_deleted(self, sqlite_session):
        """Test marking role as deleted."""
        role = RoleModel(
            tenant_id=uuid4(),
            name="user",
        )
        sqlite_session.add(role)
        sqlite_session.commit()
        
        # Soft delete
        role.is_deleted = True
        role.deleted_at = datetime.now(timezone.utc)
        sqlite_session.commit()
        
        assert role.is_deleted is True
        assert role.deleted_at is not None


class TestRoleModelRepresentation:
    """Test string representation."""
    
    def test_repr(self, sqlite_session):
        """Test __repr__ method."""
        role = RoleModel(
            tenant_id=uuid4(),
            name="admin",
        )
        sqlite_session.add(role)
        sqlite_session.commit()
        
        repr_str = repr(role)
        assert "Role" in repr_str
        assert str(role.id) in repr_str
        assert "admin" in repr_str


class TestJSONEncodedListTypeDecorator:
    """Test JSONEncodedList type decorator."""
    
    def test_process_bind_param_none(self):
        """Test processing None value for bind."""
        decorator = JSONEncodedList()
        
        from sqlalchemy.engine import default
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_bind_param(None, dialect)
        assert result is None
    
    def test_process_bind_param_list_sqlite(self):
        """Test processing list for SQLite."""
        decorator = JSONEncodedList()
        
        from sqlalchemy.engine import default
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        permissions = ["users:read", "users:write"]
        result = decorator.process_bind_param(permissions, dialect)
        assert result == '["users:read", "users:write"]'
        assert isinstance(result, str)
    
    def test_process_result_value_none(self):
        """Test processing None value from database."""
        decorator = JSONEncodedList()
        
        from sqlalchemy.engine import default
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_result_value(None, dialect)
        assert result == []
    
    def test_process_result_value_empty_sqlite(self):
        """Test processing empty string from SQLite."""
        decorator = JSONEncodedList()
        
        from sqlalchemy.engine import default
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_result_value('', dialect)
        assert result == []
    
    def test_process_result_value_list_sqlite(self):
        """Test processing JSON list from SQLite."""
        decorator = JSONEncodedList()
        
        from sqlalchemy.engine import default
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        json_str = '["users:read", "users:write"]'
        result = decorator.process_result_value(json_str, dialect)
        assert result == ["users:read", "users:write"]
    
    def test_load_dialect_impl_sqlite(self):
        """Test loading SQLite dialect implementation."""
        decorator = JSONEncodedList()
        
        from sqlalchemy.engine import default
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        impl = decorator.load_dialect_impl(dialect)
        assert impl is not None
