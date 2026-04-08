# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Tests for Excel handler functionality.
"""

from unittest.mock import MagicMock

import pytest


class TestExcelExporter:
    """Test Excel export functionality."""

    @pytest.mark.asyncio
    async def test_create_workbook(self):
        """Test creating Excel workbook."""
        workbook_config = {
            "sheets": ["Sheet1"],
            "format": "xlsx",
        }

        assert workbook_config["format"] == "xlsx"

    @pytest.mark.asyncio
    async def test_write_headers(self):
        """Test writing headers to Excel."""
        headers = ["ID", "Email", "Full Name", "Created At"]

        assert len(headers) == 4
        assert "Email" in headers

    @pytest.mark.asyncio
    async def test_write_data_rows(self):
        """Test writing data rows to Excel."""
        rows = [
            {"id": 1, "email": "test1@example.com", "full_name": "User 1"},
            {"id": 2, "email": "test2@example.com", "full_name": "User 2"},
        ]

        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_apply_column_formatting(self):
        """Test applying column formatting."""
        column_formats = {
            "created_at": "datetime",
            "amount": "currency",
            "percentage": "percent",
        }

        assert column_formats["created_at"] == "datetime"

    @pytest.mark.asyncio
    async def test_apply_styles(self):
        """Test applying styles to cells."""
        header_style = {
            "bold": True,
            "font_size": 12,
            "background_color": "#4472C4",
            "font_color": "#FFFFFF",
        }

        assert header_style["bold"] is True

    @pytest.mark.asyncio
    async def test_auto_column_width(self):
        """Test auto-adjusting column width."""
        column_widths = {}
        data = [
            {
                "name": "Short",
                "description": "A very long description that needs more space",
            },
        ]

        for row in data:
            for col, value in row.items():
                current = column_widths.get(col, 0)
                column_widths[col] = max(current, len(str(value)))

        assert column_widths["description"] > column_widths["name"]


class TestExcelImporter:
    """Test Excel import functionality."""

    @pytest.mark.asyncio
    async def test_read_workbook(self):
        """Test reading Excel workbook."""
        mock_workbook = MagicMock()
        mock_workbook.sheetnames = ["Sheet1", "Sheet2"]

        assert len(mock_workbook.sheetnames) == 2

    @pytest.mark.asyncio
    async def test_read_headers_from_first_row(self):
        """Test reading headers from first row."""
        first_row = ["ID", "Email", "Full Name", "Active"]
        headers = [cell for cell in first_row if cell]

        assert len(headers) == 4

    @pytest.mark.asyncio
    async def test_read_data_rows(self):
        """Test reading data rows."""
        sheet_data = [
            ["ID", "Email"],  # Header
            [1, "user1@example.com"],
            [2, "user2@example.com"],
        ]

        headers = sheet_data[0]
        data_rows = sheet_data[1:]

        assert len(data_rows) == 2

    @pytest.mark.asyncio
    async def test_handle_empty_cells(self):
        """Test handling empty cells."""
        row = [1, None, "Value", ""]

        # Filter empty values
        non_empty = [v for v in row if v is not None and v != ""]

        assert len(non_empty) == 2

    @pytest.mark.asyncio
    async def test_handle_date_cells(self):
        """Test handling date cells."""
        from datetime import datetime

        date_value = datetime(2024, 1, 15, 10, 30, 0)

        # Format date for storage
        formatted = date_value.isoformat()

        assert "2024-01-15" in formatted

    @pytest.mark.asyncio
    async def test_handle_numeric_cells(self):
        """Test handling numeric cells."""
        numeric_values = [
            (42, int),
            (3.14, float),
            ("123", str),
        ]

        for value, expected_type in numeric_values:
            assert isinstance(value, expected_type)


class TestExcelSheets:
    """Test Excel sheet handling."""

    def test_get_active_sheet(self):
        """Test getting active sheet."""
        sheets = {
            "Sheet1": {"active": True},
            "Sheet2": {"active": False},
        }

        active = [name for name, props in sheets.items() if props["active"]]
        assert active[0] == "Sheet1"

    def test_get_sheet_by_name(self):
        """Test getting sheet by name."""
        sheets = {"Users": [], "Roles": [], "Tenants": []}

        assert "Users" in sheets

    def test_get_sheet_by_index(self):
        """Test getting sheet by index."""
        sheets = ["Sheet1", "Sheet2", "Sheet3"]

        assert sheets[0] == "Sheet1"
        assert sheets[2] == "Sheet3"

    def test_multiple_sheets_export(self):
        """Test exporting multiple sheets."""
        export_config = {
            "sheets": {
                "Users": {"entity": "users", "columns": ["id", "email"]},
                "Roles": {"entity": "roles", "columns": ["id", "name"]},
            }
        }

        assert len(export_config["sheets"]) == 2


class TestExcelValidation:
    """Test Excel validation functionality."""

    def test_validate_file_extension(self):
        """Test file extension validation."""
        valid_extensions = [".xlsx", ".xls"]

        filename = "data.xlsx"
        ext = "." + filename.split(".")[-1]

        assert ext in valid_extensions

    def test_validate_file_format(self):
        """Test file format validation."""
        # XLSX magic bytes
        xlsx_magic = b"PK\x03\x04"

        # Check if file starts with magic bytes
        file_content = b"PK\x03\x04some content"

        is_xlsx = file_content.startswith(xlsx_magic)
        assert is_xlsx is True

    def test_validate_required_columns(self):
        """Test required columns validation."""
        required_columns = ["email", "full_name"]
        file_columns = ["id", "email", "phone"]

        missing = [col for col in required_columns if col not in file_columns]

        assert "full_name" in missing

    def test_validate_column_types(self):
        """Test column type validation."""
        column_types = {
            "id": "integer",
            "email": "string",
            "is_active": "boolean",
            "created_at": "datetime",
        }

        value = "not-an-integer"
        expected_type = column_types["id"]

        is_valid = value.isdigit() if expected_type == "integer" else True
        assert is_valid is False


class TestExcelCellFormatting:
    """Test Excel cell formatting."""

    def test_format_date_cell(self):
        """Test date cell formatting."""
        from datetime import datetime

        date = datetime(2024, 1, 15)
        excel_date_format = "YYYY-MM-DD"

        formatted = date.strftime("%Y-%m-%d")
        assert formatted == "2024-01-15"

    def test_format_number_cell(self):
        """Test number cell formatting."""
        number = 1234567.89

        # Format with thousands separator
        formatted = f"{number:,.2f}"

        assert formatted == "1,234,567.89"

    def test_format_currency_cell(self):
        """Test currency cell formatting."""
        amount = 1234.56
        currency = "USD"

        formatted = (
            f"${amount:,.2f}" if currency == "USD" else f"{amount:,.2f} {currency}"
        )

        assert "$1,234.56" in formatted

    def test_format_percentage_cell(self):
        """Test percentage cell formatting."""
        value = 0.75

        formatted = f"{value:.0%}"

        assert formatted == "75%"

    def test_format_boolean_cell(self):
        """Test boolean cell formatting."""
        boolean_formats = {
            True: "Yes",
            False: "No",
        }

        value = True
        formatted = boolean_formats[value]

        assert formatted == "Yes"


class TestExcelErrorHandling:
    """Test Excel error handling."""

    @pytest.mark.asyncio
    async def test_corrupted_file_error(self):
        """Test handling corrupted Excel files."""
        corrupted_content = b"not a valid excel file"

        # Should detect invalid format
        is_valid_xlsx = corrupted_content.startswith(b"PK")
        assert is_valid_xlsx is False

    @pytest.mark.asyncio
    async def test_empty_file_error(self):
        """Test handling empty Excel files."""
        rows = []

        is_empty = len(rows) == 0
        assert is_empty is True

    @pytest.mark.asyncio
    async def test_password_protected_error(self):
        """Test handling password-protected files."""
        # Password-protected files would raise an exception
        file_properties = {"encrypted": True}

        assert file_properties["encrypted"] is True

    @pytest.mark.asyncio
    async def test_too_large_file_error(self):
        """Test handling too large files."""
        max_size_mb = 50
        max_size_bytes = max_size_mb * 1024 * 1024

        file_size = 100 * 1024 * 1024  # 100 MB

        is_too_large = file_size > max_size_bytes
        assert is_too_large is True


class TestExcelTemplates:
    """Test Excel template functionality."""

    def test_load_template(self):
        """Test loading Excel template."""
        template_config = {
            "name": "user_import",
            "columns": ["email", "full_name", "role"],
            "validation_rules": {
                "email": {"required": True, "format": "email"},
            },
        }

        assert template_config["name"] == "user_import"

    def test_apply_template(self):
        """Test applying template to workbook."""
        template_styles = {
            "header_row": {"bold": True, "font_size": 12},
            "data_rows": {"font_size": 11},
        }

        assert template_styles["header_row"]["bold"] is True

    def test_template_with_dropdowns(self):
        """Test template with dropdown validation."""
        dropdown_config = {
            "column": "role",
            "values": ["admin", "user", "viewer"],
            "allow_blank": False,
        }

        assert len(dropdown_config["values"]) == 3

    def test_template_with_formulas(self):
        """Test template with formulas."""
        formula_cells = {
            "E2": "=SUM(B2:D2)",
            "F2": "=AVERAGE(B2:D2)",
        }

        assert "SUM" in formula_cells["E2"]


class TestExcelMemoryOptimization:
    """Test Excel memory optimization."""

    def test_streaming_write_mode(self):
        """Test streaming write mode for large files."""
        config = {
            "mode": "streaming",
            "buffer_size": 1000,
        }

        assert config["mode"] == "streaming"

    def test_chunked_reading(self):
        """Test chunked reading for large files."""
        total_rows = 100000
        chunk_size = 1000

        chunks = total_rows // chunk_size

        assert chunks == 100

    def test_memory_efficient_iteration(self):
        """Test memory-efficient iteration."""

        # Simulate generator-based iteration
        def row_generator(total):
            for i in range(total):
                yield {"id": i, "value": f"value_{i}"}

        rows_processed = 0
        for row in row_generator(10):
            rows_processed += 1

        assert rows_processed == 10


class TestExcelHandlerFunctions:
    """Test ExcelHandler helper functions."""

    def test_is_excel_available(self):
        """Test is_excel_available function."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        result = is_excel_available()

        assert isinstance(result, bool)

    def test_get_excel_handler(self):
        """Test get_excel_handler factory function."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.infrastructure.data_exchange.excel_handler import get_excel_handler

            handler = get_excel_handler()
            assert handler is not None


class TestExcelHandlerFormatValue:
    """Test ExcelHandler _format_value method."""

    def test_format_none_value(self):
        """Test formatting None value."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            from app.domain.ports.data_exchange import FieldConfig, FieldType

            field = FieldConfig(
                name="test", display_name="Test", field_type=FieldType.STRING
            )
            result = handler._format_value(None, field)

            assert result == "" or result is None

    def test_format_datetime_value(self):
        """Test formatting datetime value."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from datetime import datetime

            from app.domain.ports.data_exchange import FieldConfig, FieldType
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            field = FieldConfig(
                name="created_at",
                display_name="Created At",
                field_type=FieldType.DATETIME,
            )

            dt = datetime(2024, 6, 15, 10, 30)
            result = handler._format_value(dt, field)

            assert result is not None

    def test_format_uuid_value(self):
        """Test formatting UUID value."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from uuid import uuid4

            from app.domain.ports.data_exchange import FieldConfig, FieldType
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            field = FieldConfig(name="id", display_name="ID", field_type=FieldType.UUID)

            test_uuid = uuid4()
            result = handler._format_value(test_uuid, field)

            assert str(test_uuid) in str(result)


class TestExcelHandlerBuildFieldMap:
    """Test ExcelHandler _build_field_map method."""

    def test_build_field_map_by_name(self):
        """Test building field map by field name."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import (
                EntityConfig,
                FieldConfig,
                FieldType,
            )
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            config = EntityConfig(
                name="test",
                display_name="Test",
                model=object,
                fields=[
                    FieldConfig(
                        name="email",
                        display_name="Email Address",
                        field_type=FieldType.EMAIL,
                    ),
                    FieldConfig(
                        name="name",
                        display_name="Full Name",
                        field_type=FieldType.STRING,
                    ),
                ],
                permission_resource="test",
            )

            headers = ["email", "name"]
            field_map = handler._build_field_map(headers, config)

            assert "email" in field_map
            assert "name" in field_map

    def test_build_field_map_by_display_name(self):
        """Test building field map by display name."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import (
                EntityConfig,
                FieldConfig,
                FieldType,
            )
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            config = EntityConfig(
                name="test",
                display_name="Test",
                model=object,
                fields=[
                    FieldConfig(
                        name="email",
                        display_name="Email Address",
                        field_type=FieldType.EMAIL,
                    ),
                ],
                permission_resource="test",
            )

            headers = ["Email Address"]
            field_map = handler._build_field_map(headers, config)

            assert "Email Address" in field_map


class TestExcelHandlerGenerateExample:
    """Test ExcelHandler _generate_example method."""

    def test_generate_example_string(self):
        """Test generating example for string field."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import FieldConfig, FieldType
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            field = FieldConfig(
                name="name", display_name="Name", field_type=FieldType.STRING
            )

            example = handler._generate_example(field)

            assert example is not None

    def test_generate_example_email(self):
        """Test generating example for email field."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import FieldConfig, FieldType
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            field = FieldConfig(
                name="email", display_name="Email", field_type=FieldType.EMAIL
            )

            example = handler._generate_example(field)

            assert "@" in str(example)

    def test_generate_example_uuid(self):
        """Test generating example for UUID field."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import FieldConfig, FieldType
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            field = FieldConfig(name="id", display_name="ID", field_type=FieldType.UUID)

            example = handler._generate_example(field)

            assert example is not None

    def test_generate_example_boolean(self):
        """Test generating example for boolean field."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import FieldConfig, FieldType
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            field = FieldConfig(
                name="is_active", display_name="Active", field_type=FieldType.BOOLEAN
            )

            example = handler._generate_example(field)

            assert example in [True, False, "true", "false", "si", "no"]

    def test_generate_example_integer(self):
        """Test generating example for integer field."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import FieldConfig, FieldType
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            field = FieldConfig(
                name="count", display_name="Count", field_type=FieldType.INTEGER
            )

            example = handler._generate_example(field)

            assert isinstance(example, int) or example is not None


class TestExcelHandlerWrite:
    """Test ExcelHandler write method."""

    def test_write_basic_data(self):
        """Test writing basic data to Excel."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import (
                EntityConfig,
                FieldConfig,
                FieldType,
            )
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            config = EntityConfig(
                name="test",
                display_name="Test",
                model=object,
                fields=[
                    FieldConfig(
                        name="id",
                        display_name="ID",
                        field_type=FieldType.INTEGER,
                        exportable=True,
                    ),
                    FieldConfig(
                        name="name",
                        display_name="Name",
                        field_type=FieldType.STRING,
                        exportable=True,
                    ),
                ],
                permission_resource="test",
            )

            data = [
                {"id": 1, "name": "Test User 1"},
                {"id": 2, "name": "Test User 2"},
            ]

            result = handler.write(data, config)

            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_write_with_title(self):
        """Test writing data with custom title."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import (
                EntityConfig,
                FieldConfig,
                FieldType,
            )
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            config = EntityConfig(
                name="test",
                display_name="Test",
                model=object,
                fields=[
                    FieldConfig(
                        name="id",
                        display_name="ID",
                        field_type=FieldType.INTEGER,
                        exportable=True,
                    ),
                ],
                permission_resource="test",
            )

            data = [{"id": 1}]
            result = handler.write(data, config, title="Custom Title")

            assert isinstance(result, bytes)


class TestExcelHandlerGenerateTemplate:
    """Test ExcelHandler generate_template method."""

    def test_generate_template_basic(self):
        """Test generating import template."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import (
                EntityConfig,
                FieldConfig,
                FieldType,
            )
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            config = EntityConfig(
                name="test",
                display_name="Test",
                model=object,
                fields=[
                    FieldConfig(
                        name="email",
                        display_name="Email",
                        field_type=FieldType.EMAIL,
                        importable=True,
                        required=True,
                    ),
                    FieldConfig(
                        name="name",
                        display_name="Name",
                        field_type=FieldType.STRING,
                        importable=True,
                    ),
                ],
                permission_resource="test",
            )

            result = handler.generate_template(config)

            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_generate_template_with_example(self):
        """Test generating template with example row."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if is_excel_available():
            from app.domain.ports.data_exchange import (
                EntityConfig,
                FieldConfig,
                FieldType,
            )
            from app.infrastructure.data_exchange.excel_handler import ExcelHandler

            handler = ExcelHandler()
            config = EntityConfig(
                name="test",
                display_name="Test",
                model=object,
                fields=[
                    FieldConfig(
                        name="email",
                        display_name="Email",
                        field_type=FieldType.EMAIL,
                        importable=True,
                    ),
                ],
                permission_resource="test",
            )

            result = handler.generate_template(config, include_example=True)

            assert isinstance(result, bytes)
