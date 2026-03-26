# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Data Exchange port interfaces.

Defines the configuration system for flexible import/export/reports
that can work with any entity in the system.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, TypeVar
from uuid import UUID

T = TypeVar("T")


class FieldType(str, Enum):
    """Supported field types for import/export."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"
    EMAIL = "email"
    ENUM = "enum"
    JSON = "json"


class ImportMode(str, Enum):
    """Import operation modes."""

    INSERT = "insert"  # Only insert new records
    UPSERT = "upsert"  # Insert or update based on unique fields
    UPDATE_ONLY = "update_only"  # Only update existing records


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


class ReportFormat(str, Enum):
    """Supported report formats."""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    HTML = "html"


@dataclass
class FieldConfig:
    """
    Configuration for a single field in import/export operations.

    Attributes:
        name: Internal name (database column)
        display_name: Human-readable name for reports/templates
        field_type: Data type of the field
        required: Whether field is required for import
        exportable: Include in exports
        importable: Allow in imports
        default: Default value if not provided
        choices: Valid values for enum fields
        validator: Custom validation function
        transformer: Function to transform values during import
        width: Column width for Excel exports
        format: Display format (e.g., "0.00" for decimals)
    """

    name: str
    display_name: str
    field_type: FieldType = FieldType.STRING
    required: bool = False
    exportable: bool = True
    importable: bool = True
    default: Any = None
    choices: list[str] | None = None
    validator: Callable[[Any], bool] | None = None
    transformer: Callable[[Any], Any] | None = None
    width: int = 15
    format: str | None = None

    def validate(self, value: Any) -> tuple[bool, str | None]:
        """
        Validate a value for this field.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required
        if self.required and (value is None or value == ""):
            return False, f"Field '{self.display_name}' is required"

        # Skip validation for None/empty if not required
        if value is None or value == "":
            return True, None

        # Type validation
        try:
            self._validate_type(value)
        except (ValueError, TypeError):
            return False, f"Invalid value for '{self.display_name}'"

        # Choices validation
        if self.choices and value not in self.choices:
            return False, f"Invalid choice for '{self.display_name}'"

        # Custom validator
        if self.validator and not self.validator(value):
            return False, f"Validation failed for '{self.display_name}'"

        return True, None

    def _validate_type(self, value: Any) -> None:
        """Validate value matches field type."""
        if self.field_type == FieldType.INTEGER:
            if not isinstance(value, int) and not str(value).isdigit():
                raise ValueError("Expected an integer value")
        elif self.field_type == FieldType.FLOAT:
            float(value)
        elif self.field_type == FieldType.BOOLEAN:
            if not isinstance(value, bool) and str(value).lower() not in (
                "true",
                "false",
                "1",
                "0",
                "yes",
                "no",
                "sí",
                "si",
            ):
                raise ValueError("Expected a boolean value")
        elif self.field_type == FieldType.EMAIL:
            if "@" not in str(value) or "." not in str(value):
                raise ValueError("Invalid email format")
        elif self.field_type == FieldType.UUID:
            UUID(str(value))
        elif self.field_type == FieldType.DATE:
            if not isinstance(value, date):
                # Try parsing common formats
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                    try:
                        datetime.strptime(str(value), fmt)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError("Invalid date format")
        elif self.field_type == FieldType.DATETIME:
            if not isinstance(value, datetime):
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
                    try:
                        datetime.strptime(str(value), fmt)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError("Invalid datetime format")

    def transform(self, value: Any) -> Any:
        """Transform a value for import."""
        if value is None or value == "":
            return self.default

        # Apply custom transformer first
        if self.transformer:
            value = self.transformer(value)

        # Type conversion
        if self.field_type == FieldType.INTEGER:
            return int(value)
        if self.field_type == FieldType.FLOAT:
            return float(value)
        if self.field_type == FieldType.BOOLEAN:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes", "sí", "si")
        if self.field_type == FieldType.UUID:
            return UUID(str(value)) if not isinstance(value, UUID) else value
        if self.field_type == FieldType.DATE:
            if isinstance(value, date):
                return value
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(str(value), fmt).date()
                except ValueError:
                    continue
            return value
        if self.field_type == FieldType.DATETIME:
            if isinstance(value, datetime):
                return value
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    return datetime.strptime(str(value), fmt)
                except ValueError:
                    continue
            return value

        return value


@dataclass
class EntityConfig:
    """
    Complete configuration for an entity's import/export/report capabilities.

    Attributes:
        name: Unique identifier for the entity
        display_name: Human-readable name for UI
        model: SQLAlchemy model class
        fields: List of field configurations
        permission_resource: ACL resource name for permission checks
        unique_fields: Fields used for upsert matching
        batch_size: Number of records per batch in import
        default_sort: Default sort field for exports
        max_export_rows: Maximum rows allowed in single export
        report_title: Title for generated reports
        report_grouping: Fields to group by in reports
    """

    name: str
    display_name: str
    model: type[Any]
    fields: list[FieldConfig]
    permission_resource: str
    unique_fields: list[str] = field(default_factory=list)
    batch_size: int = 100
    default_sort: str = "created_at"
    max_export_rows: int = 10000
    report_title: str = ""
    report_grouping: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.report_title:
            self.report_title = f"Reporte de {self.display_name}"

    def get_exportable_fields(self) -> list[FieldConfig]:
        """Get fields that can be exported."""
        return [f for f in self.fields if f.exportable]

    def get_importable_fields(self) -> list[FieldConfig]:
        """Get fields that can be imported."""
        return [f for f in self.fields if f.importable]

    def get_required_fields(self) -> list[FieldConfig]:
        """Get required fields for import."""
        return [f for f in self.fields if f.required and f.importable]

    def get_field(self, name: str) -> FieldConfig | None:
        """Get a field configuration by name."""
        for f in self.fields:
            if f.name == name:
                return f
        return None


class EntityRegistry:
    """
    Central registry for entity configurations.

    This allows any part of the application to register entities
    that should be available for import/export/reports.

    Usage:
        # Register an entity
        EntityRegistry.register(USER_CONFIG)

        # Get an entity
        config = EntityRegistry.get("users")

        # List all entities
        all_entities = EntityRegistry.list_all()
    """

    _entities: dict[str, EntityConfig] = {}

    @classmethod
    def register(cls, config: EntityConfig) -> None:
        """Register an entity configuration."""
        cls._entities[config.name] = config

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister an entity configuration."""
        cls._entities.pop(name, None)

    @classmethod
    def get(cls, name: str) -> EntityConfig | None:
        """Get an entity configuration by name."""
        return cls._entities.get(name)

    @classmethod
    def list_all(cls) -> list[EntityConfig]:
        """List all registered entity configurations."""
        return list(cls._entities.values())

    @classmethod
    def list_exportable(cls) -> list[EntityConfig]:
        """List entities that have exportable fields."""
        return [
            e for e in cls._entities.values() if any(f.exportable for f in e.fields)
        ]

    @classmethod
    def list_importable(cls) -> list[EntityConfig]:
        """List entities that have importable fields."""
        return [
            e for e in cls._entities.values() if any(f.importable for f in e.fields)
        ]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered entities (useful for testing)."""
        cls._entities.clear()
