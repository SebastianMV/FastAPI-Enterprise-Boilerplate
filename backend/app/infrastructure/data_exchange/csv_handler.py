# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
CSV Handler for data import/export.

Provides CSV reading and writing capabilities.
"""

import csv
import io
from collections.abc import Iterator
from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.domain.ports.data_exchange import EntityConfig, FieldConfig


class CSVHandler:
    """
    Handler for CSV file operations.

    Provides methods for reading and writing CSV files
    with support for entity field configurations.
    """

    def __init__(self, encoding: str = "utf-8"):
        """
        Initialize CSV handler.

        Args:
            encoding: File encoding (default: utf-8)
        """
        self.encoding = encoding

    def read(
        self,
        file_content: bytes,
        entity_config: EntityConfig,
    ) -> Iterator[tuple[int, dict[str, Any], list[str]]]:
        """
        Read CSV file and yield rows with validation errors.

        Args:
            file_content: CSV file content as bytes
            entity_config: Entity configuration for field mapping

        Yields:
            Tuple of (row_number, row_data, errors)
        """
        # Detect delimiter
        text_content = file_content.decode(self.encoding)
        delimiter = self._detect_delimiter(text_content)

        # Parse CSV
        reader = csv.DictReader(
            io.StringIO(text_content),
            delimiter=delimiter,
        )

        # Build field map (header name -> field config)
        headers: list[str] = list(reader.fieldnames or [])
        field_map = self._build_field_map(headers, entity_config)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            row_data = {}
            errors = []

            for header, value in row.items():
                field_config = field_map.get(header)
                if not field_config:
                    continue  # Skip unknown columns

                if not field_config.importable:
                    continue  # Skip non-importable fields

                # Validate
                is_valid, error_msg = field_config.validate(value)
                if not is_valid:
                    errors.append(error_msg or f"Invalid value for {header}")
                    continue

                # Transform
                try:
                    transformed = field_config.transform(value)
                    row_data[field_config.name] = transformed
                except Exception:
                    errors.append(f"Transform error for {header}")

            # Check required fields
            for field in entity_config.get_required_fields():
                if field.name not in row_data or row_data[field.name] is None:
                    errors.append(f"Missing required field: {field.display_name}")

            yield row_num, row_data, errors

    def write(
        self,
        data: list[dict[str, Any]],
        entity_config: EntityConfig,
        columns: list[str] | None = None,
    ) -> bytes:
        """
        Write data to CSV format.

        Args:
            data: List of dictionaries to export
            entity_config: Entity configuration for field mapping
            columns: Specific columns to include (None = all exportable)

        Returns:
            CSV content as bytes
        """
        output = io.StringIO()

        # Get fields to export
        fields = entity_config.get_exportable_fields()
        if columns:
            fields = [f for f in fields if f.name in columns]

        # Write header
        writer = csv.writer(output)
        writer.writerow([f.display_name for f in fields])

        # Write data
        for row in data:
            row_values = []
            for field in fields:
                value = row.get(field.name)
                formatted = self._format_value(value, field)
                row_values.append(formatted)
            writer.writerow(row_values)

        return output.getvalue().encode(self.encoding)

    def generate_template(
        self,
        entity_config: EntityConfig,
        include_example: bool = True,
    ) -> bytes:
        """
        Generate an empty CSV template for import.

        Args:
            entity_config: Entity configuration
            include_example: Include an example row

        Returns:
            Template CSV content as bytes
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Get importable fields
        fields = entity_config.get_importable_fields()

        # Write header
        writer.writerow([f.display_name for f in fields])

        # Write example row
        if include_example:
            example_row = []
            for field in fields:
                example = self._get_example_value(field)
                example_row.append(example)
            writer.writerow(example_row)

        return output.getvalue().encode(self.encoding)

    def _detect_delimiter(self, content: str) -> str:
        """Detect CSV delimiter (comma, semicolon, tab)."""
        first_line = content.split("\n")[0] if content else ""

        # Count occurrences
        comma_count = first_line.count(",")
        semicolon_count = first_line.count(";")
        tab_count = first_line.count("\t")

        if semicolon_count > comma_count and semicolon_count > tab_count:
            return ";"
        if tab_count > comma_count:
            return "\t"
        return ","

    def _build_field_map(
        self,
        headers: list[str],
        entity_config: EntityConfig,
    ) -> dict[str, FieldConfig]:
        """Build mapping from CSV headers to field configs."""
        field_map = {}

        for header in headers:
            header_lower = header.lower().strip()

            # Try exact match on display_name
            for field in entity_config.fields:
                if field.display_name.lower() == header_lower:
                    field_map[header] = field
                    break
                # Also try matching on field name
                if field.name.lower() == header_lower:
                    field_map[header] = field
                    break

        return field_map

    @staticmethod
    def _sanitize_formula(value: str) -> str:
        """Prevent CSV formula injection by prefixing dangerous chars with a tab."""
        if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "\t" + value
        return value

    def _format_value(self, value: Any, field: FieldConfig) -> str:
        """Format a value for CSV output."""
        if value is None:
            return ""

        if isinstance(value, datetime):
            format_str = field.format or "%Y-%m-%d %H:%M:%S"
            return value.strftime(format_str)
        if isinstance(value, date):
            format_str = field.format or "%Y-%m-%d"
            return value.strftime(format_str)
        if isinstance(value, bool):
            return "Sí" if value else "No"
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, (dict, list)):
            import json

            return json.dumps(value, ensure_ascii=False)

        return self._sanitize_formula(str(value))

    def _get_example_value(self, field: FieldConfig) -> str:
        """Get an example value for a field."""
        from app.domain.ports.data_exchange import FieldType

        examples = {
            FieldType.STRING: "Texto ejemplo",
            FieldType.INTEGER: "123",
            FieldType.FLOAT: "123.45",
            FieldType.BOOLEAN: "Sí",
            FieldType.DATE: "2026-01-15",
            FieldType.DATETIME: "2026-01-15 10:30:00",
            FieldType.UUID: "550e8400-e29b-41d4-a716-446655440000",
            FieldType.EMAIL: "ejemplo@correo.com",
            FieldType.ENUM: field.choices[0] if field.choices else "opcion1",
            FieldType.JSON: '{"key": "value"}',
        }

        prefix = "(requerido) " if field.required else "(opcional) "

        return prefix + examples.get(field.field_type, "valor")


# Singleton instance
_csv_handler: CSVHandler | None = None


def get_csv_handler() -> CSVHandler:
    """Get CSV handler singleton."""
    global _csv_handler
    if _csv_handler is None:
        _csv_handler = CSVHandler()
    return _csv_handler
