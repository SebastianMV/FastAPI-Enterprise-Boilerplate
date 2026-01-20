# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Custom SQLAlchemy type decorators for cross-database compatibility.

These types ensure models work with both PostgreSQL (production) and SQLite (tests).
"""

import json
from uuid import UUID
from sqlalchemy import Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PgUUID
from sqlalchemy import String


class JSONEncodedList(TypeDecorator):
    """
    Type decorator that stores list as JSON for SQLite compatibility.
    
    Uses PostgreSQL ARRAY when available, falls back to JSON/TEXT for SQLite.
    """
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        """Load appropriate type based on dialect."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(String(100)))
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        """Convert Python list to storage format."""
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        # For SQLite/others, encode as JSON
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        """Convert storage format to Python list."""
        if value is None:
            return []
        if dialect.name == 'postgresql':
            return value if value else []
        # For SQLite/others, decode JSON
        return json.loads(value) if value else []


class JSONEncodedUUIDList(TypeDecorator):
    """
    Type decorator that stores list of UUIDs as JSON for SQLite compatibility.
    
    Uses PostgreSQL ARRAY(UUID) when available, falls back to JSON/TEXT for SQLite.
    """
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        """Load appropriate type based on dialect."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(PgUUID(as_uuid=True)))
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        """Convert Python list of UUIDs to storage format."""
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        # For SQLite/others, encode as JSON (convert UUIDs to strings)
        return json.dumps([str(uuid) for uuid in value])
    
    def process_result_value(self, value, dialect):
        """Convert storage format to Python list of UUIDs."""
        if value is None:
            return []
        if dialect.name == 'postgresql':
            return value if value else []
        # For SQLite/others, decode JSON and convert strings to UUIDs
        uuid_strings = json.loads(value) if value else []
        return [UUID(s) for s in uuid_strings]


class JSONBCompat(TypeDecorator):
    """
    Type decorator for JSONB that's SQLite compatible.
    
    Uses JSONB on PostgreSQL, falls back to TEXT+JSON on SQLite.
    """
    impl = Text
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        """Load appropriate type based on dialect."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())
    
    def process_bind_param(self, value, dialect):
        """Convert Python dict to storage format."""
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        # For SQLite/others, encode as JSON
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        """Convert storage format to Python dict."""
        if value is None:
            return {}
        if dialect.name == 'postgresql':
            return value if value else {}
        # For SQLite/others, decode JSON
        return json.loads(value) if value else {}

