# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Tests for custom SQLAlchemy type decorators.
"""

import json
from uuid import UUID, uuid4
import pytest
from sqlalchemy.engine import default
from sqlalchemy.dialects import postgresql

from app.infrastructure.database.models.custom_types import (
    JSONEncodedList,
    JSONEncodedUUIDList,
    JSONBCompat,
)


class TestJSONEncodedList:
    """Test JSONEncodedList type decorator."""

    def test_load_dialect_impl_postgresql(self):
        """Test loading PostgreSQL dialect implementation."""
        decorator = JSONEncodedList()
        dialect = postgresql.dialect()
        
        impl = decorator.load_dialect_impl(dialect)
        assert impl is not None

    def test_load_dialect_impl_sqlite(self):
        """Test loading SQLite dialect implementation."""
        decorator = JSONEncodedList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        impl = decorator.load_dialect_impl(dialect)
        assert impl is not None

    def test_process_bind_param_none(self):
        """Test processing None value for bind."""
        decorator = JSONEncodedList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_bind_param(None, dialect)
        assert result is None

    def test_process_bind_param_list_postgresql(self):
        """Test processing list for PostgreSQL."""
        decorator = JSONEncodedList()
        dialect = postgresql.dialect()
        
        permissions = ["users:read", "users:write"]
        result = decorator.process_bind_param(permissions, dialect)
        assert result == permissions

    def test_process_bind_param_list_sqlite(self):
        """Test processing list for SQLite."""
        decorator = JSONEncodedList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        permissions = ["users:read", "users:write"]
        result = decorator.process_bind_param(permissions, dialect)
        assert result == '["users:read", "users:write"]'
        assert isinstance(result, str)

    def test_process_result_value_none(self):
        """Test processing None value from database."""
        decorator = JSONEncodedList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_result_value(None, dialect)
        assert result == []

    def test_process_result_value_empty_string_sqlite(self):
        """Test processing empty string from SQLite."""
        decorator = JSONEncodedList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_result_value('', dialect)
        assert result == []

    def test_process_result_value_list_sqlite(self):
        """Test processing JSON list from SQLite."""
        decorator = JSONEncodedList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        json_str = '["users:read", "users:write"]'
        result = decorator.process_result_value(json_str, dialect)
        assert result == ["users:read", "users:write"]

    def test_process_result_value_list_postgresql(self):
        """Test processing list from PostgreSQL."""
        decorator = JSONEncodedList()
        dialect = postgresql.dialect()
        
        permissions = ["users:read", "users:write"]
        result = decorator.process_result_value(permissions, dialect)
        assert result == permissions

    def test_process_result_value_empty_list_postgresql(self):
        """Test processing empty list from PostgreSQL."""
        decorator = JSONEncodedList()
        dialect = postgresql.dialect()
        
        result = decorator.process_result_value([], dialect)
        assert result == []

    def test_process_result_value_none_postgresql(self):
        """Test processing None value from PostgreSQL."""
        decorator = JSONEncodedList()
        dialect = postgresql.dialect()
        
        result = decorator.process_result_value(None, dialect)
        assert result == []


class TestJSONEncodedUUIDList:
    """Test JSONEncodedUUIDList type decorator."""

    def test_load_dialect_impl_postgresql(self):
        """Test loading PostgreSQL dialect implementation."""
        decorator = JSONEncodedUUIDList()
        dialect = postgresql.dialect()
        
        impl = decorator.load_dialect_impl(dialect)
        assert impl is not None

    def test_load_dialect_impl_sqlite(self):
        """Test loading SQLite dialect implementation."""
        decorator = JSONEncodedUUIDList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        impl = decorator.load_dialect_impl(dialect)
        assert impl is not None

    def test_process_bind_param_none(self):
        """Test processing None value for bind."""
        decorator = JSONEncodedUUIDList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_bind_param(None, dialect)
        assert result is None

    def test_process_bind_param_uuids_postgresql(self):
        """Test processing UUID list for PostgreSQL."""
        decorator = JSONEncodedUUIDList()
        dialect = postgresql.dialect()
        
        uuid1 = uuid4()
        uuid2 = uuid4()
        uuids = [uuid1, uuid2]
        
        result = decorator.process_bind_param(uuids, dialect)
        assert result == uuids

    def test_process_bind_param_uuids_sqlite(self):
        """Test processing UUID list for SQLite."""
        decorator = JSONEncodedUUIDList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        uuid1 = uuid4()
        uuid2 = uuid4()
        uuids = [uuid1, uuid2]
        
        result = decorator.process_bind_param(uuids, dialect)
        assert isinstance(result, str)
        
        # Verify it's valid JSON with UUID strings
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0] == str(uuid1)
        assert parsed[1] == str(uuid2)

    def test_process_result_value_none(self):
        """Test processing None value from database."""
        decorator = JSONEncodedUUIDList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_result_value(None, dialect)
        assert result == []

    def test_process_result_value_empty_string_sqlite(self):
        """Test processing empty string from SQLite."""
        decorator = JSONEncodedUUIDList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_result_value('', dialect)
        assert result == []

    def test_process_result_value_uuids_sqlite(self):
        """Test processing UUID JSON from SQLite."""
        decorator = JSONEncodedUUIDList()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        uuid1 = uuid4()
        uuid2 = uuid4()
        json_str = json.dumps([str(uuid1), str(uuid2)])
        
        result = decorator.process_result_value(json_str, dialect)
        assert len(result) == 2
        assert isinstance(result[0], UUID)
        assert isinstance(result[1], UUID)
        assert result[0] == uuid1
        assert result[1] == uuid2

    def test_process_result_value_uuids_postgresql(self):
        """Test processing UUID list from PostgreSQL."""
        decorator = JSONEncodedUUIDList()
        dialect = postgresql.dialect()
        
        uuid1 = uuid4()
        uuid2 = uuid4()
        uuids = [uuid1, uuid2]
        
        result = decorator.process_result_value(uuids, dialect)
        assert result == uuids

    def test_process_result_value_empty_list_postgresql(self):
        """Test processing empty list from PostgreSQL."""
        decorator = JSONEncodedUUIDList()
        dialect = postgresql.dialect()
        
        result = decorator.process_result_value([], dialect)
        assert result == []

    def test_process_result_value_none_postgresql(self):
        """Test processing None value from PostgreSQL."""
        decorator = JSONEncodedUUIDList()
        dialect = postgresql.dialect()
        
        result = decorator.process_result_value(None, dialect)
        assert result == []


class TestJSONBCompat:
    """Test JSONBCompat type decorator."""

    def test_load_dialect_impl_postgresql(self):
        """Test loading PostgreSQL dialect implementation."""
        decorator = JSONBCompat()
        dialect = postgresql.dialect()
        
        impl = decorator.load_dialect_impl(dialect)
        assert impl is not None

    def test_load_dialect_impl_sqlite(self):
        """Test loading SQLite dialect implementation."""
        decorator = JSONBCompat()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        impl = decorator.load_dialect_impl(dialect)
        assert impl is not None

    def test_process_bind_param_none(self):
        """Test processing None value for bind."""
        decorator = JSONBCompat()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_bind_param(None, dialect)
        assert result is None

    def test_process_bind_param_dict_postgresql(self):
        """Test processing dict for PostgreSQL."""
        decorator = JSONBCompat()
        dialect = postgresql.dialect()
        
        data = {"key": "value", "count": 42}
        result = decorator.process_bind_param(data, dialect)
        assert result == data

    def test_process_bind_param_dict_sqlite(self):
        """Test processing dict for SQLite."""
        decorator = JSONBCompat()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        data = {"key": "value", "count": 42}
        result = decorator.process_bind_param(data, dialect)
        assert isinstance(result, str)
        assert json.loads(result) == data

    def test_process_result_value_none(self):
        """Test processing None value from database."""
        decorator = JSONBCompat()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_result_value(None, dialect)
        assert result == {}

    def test_process_result_value_empty_string_sqlite(self):
        """Test processing empty string from SQLite."""
        decorator = JSONBCompat()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        result = decorator.process_result_value('', dialect)
        assert result == {}

    def test_process_result_value_dict_sqlite(self):
        """Test processing JSON dict from SQLite."""
        decorator = JSONBCompat()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        data = {"key": "value", "count": 42}
        json_str = json.dumps(data)
        
        result = decorator.process_result_value(json_str, dialect)
        assert result == data

    def test_process_result_value_dict_postgresql(self):
        """Test processing dict from PostgreSQL."""
        decorator = JSONBCompat()
        dialect = postgresql.dialect()
        
        data = {"key": "value", "count": 42}
        result = decorator.process_result_value(data, dialect)
        assert result == data

    def test_process_result_value_empty_dict_postgresql(self):
        """Test processing empty dict from PostgreSQL."""
        decorator = JSONBCompat()
        dialect = postgresql.dialect()
        
        result = decorator.process_result_value({}, dialect)
        assert result == {}

    def test_process_result_value_none_postgresql(self):
        """Test processing None value from PostgreSQL."""
        decorator = JSONBCompat()
        dialect = postgresql.dialect()
        
        result = decorator.process_result_value(None, dialect)
        assert result == {}

    def test_process_result_value_complex_nested_sqlite(self):
        """Test processing complex nested JSON from SQLite."""
        decorator = JSONBCompat()
        dialect = default.DefaultDialect()
        dialect.name = 'sqlite'
        
        data = {
            "user": {"name": "John", "age": 30},
            "roles": ["admin", "user"],
            "settings": {"theme": "dark", "notifications": True}
        }
        json_str = json.dumps(data)
        
        result = decorator.process_result_value(json_str, dialect)
        assert result == data
