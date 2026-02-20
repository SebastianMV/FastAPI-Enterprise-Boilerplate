# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Custom SQLAlchemy type decorators for cross-database compatibility.

These types ensure models work with both PostgreSQL (production) and SQLite (tests).
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID


class JSONEncodedList(TypeDecorator[list[Any]]):
    """
    Type decorator that stores list as JSON for SQLite compatibility.

    Uses PostgreSQL ARRAY when available, falls back to JSON/TEXT for SQLite.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        """Load appropriate type based on dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String(100)))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: list[Any] | None, dialect: Any) -> Any:
        """Convert Python list to storage format."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        # For SQLite/others, encode as JSON
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> list[Any]:
        """Convert storage format to Python list."""
        if value is None:
            return []
        if dialect.name == "postgresql":
            return value if value else []
        # For SQLite/others, decode JSON
        return json.loads(value) if value else []


class JSONEncodedUUIDList(TypeDecorator[list[UUID]]):
    """
    Type decorator that stores list of UUIDs as JSON for SQLite compatibility.

    Uses PostgreSQL ARRAY(UUID) when available, falls back to JSON/TEXT for SQLite.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        """Load appropriate type based on dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(PgUUID(as_uuid=True)))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: list[UUID] | None, dialect: Any) -> Any:
        """Convert Python list of UUIDs to storage format."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        # For SQLite/others, encode as JSON (convert UUIDs to strings)
        return json.dumps([str(uuid) for uuid in value])

    def process_result_value(self, value: Any, dialect: Any) -> list[UUID]:
        """Convert storage format to Python list of UUIDs."""
        if value is None:
            return []
        if dialect.name == "postgresql":
            return value if value else []
        # For SQLite/others, decode JSON and convert strings to UUIDs
        uuid_strings = json.loads(value) if value else []
        return [UUID(s) for s in uuid_strings]


class JSONBCompat(TypeDecorator[dict[str, Any]]):
    """
    Type decorator for JSONB that's SQLite compatible.

    Uses JSONB on PostgreSQL, falls back to TEXT+JSON on SQLite.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        """Load appropriate type based on dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: dict[str, Any] | None, dialect: Any) -> Any:
        """Convert Python dict to storage format."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        # For SQLite/others, encode as JSON
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> dict[str, Any]:
        """Convert storage format to Python dict."""
        if value is None:
            return {}
        if dialect.name == "postgresql":
            return value if value else {}
        # For SQLite/others, decode JSON
        return json.loads(value) if value else {}
