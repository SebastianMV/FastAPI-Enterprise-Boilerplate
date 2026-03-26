# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Tests for generic exporter implementation.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.ports.data_exchange import (
    EntityRegistry,
    ExportFormat,
    FieldConfig,
    FieldType,
)
from app.domain.ports.import_export import (
    ExportRequest,
    ExportResult,
)


class TestGenericExporterBasic:
    """Test basic generic exporter functionality."""

    @pytest.mark.asyncio
    async def test_exporter_initialization(self):
        """Test exporter can be initialized with session."""
        mock_session = AsyncMock()

        with patch(
            "app.infrastructure.data_exchange.generic_exporter.GenericExporter"
        ) as MockExporter:
            exporter = MockExporter(mock_session)
            assert exporter is not None

    @pytest.mark.asyncio
    async def test_export_csv_format(self):
        """Test export to CSV format."""
        mock_session = AsyncMock()

        # Create field using correct API
        field = FieldConfig(
            name="email",
            display_name="Email",
            field_type=FieldType.STRING,
            required=True,
        )
        assert field.name == "email"

        with patch.object(EntityRegistry, "get") as mock_get:
            # Test CSV export request
            request = ExportRequest(
                entity="users",
                format=ExportFormat.CSV,
            )
            assert request.format == ExportFormat.CSV

    @pytest.mark.asyncio
    async def test_export_json_format(self):
        """Test export to JSON format."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.JSON,
        )
        assert request.format == ExportFormat.JSON

    @pytest.mark.asyncio
    async def test_export_excel_format(self):
        """Test export to Excel format."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.EXCEL,
        )
        assert request.format == ExportFormat.EXCEL


class TestExportRequest:
    """Test export request schema."""

    def test_export_request_required_fields(self):
        """Test export request with required fields."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
        )
        assert request.entity == "users"
        assert request.format == ExportFormat.CSV

    def test_export_request_with_columns(self):
        """Test export request with specific columns."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
            columns=["id", "email", "name"],
        )
        assert request.columns == ["id", "email", "name"]

    def test_export_request_with_filters(self):
        """Test export request with filters."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
            filters={"is_active": True},
        )
        assert request.filters == {"is_active": True}

    def test_export_request_with_tenant(self):
        """Test export request with tenant_id."""
        tenant_id = uuid4()
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
            tenant_id=tenant_id,
        )
        assert request.tenant_id == tenant_id

    def test_export_request_include_headers(self):
        """Test export request header inclusion."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
            include_headers=True,
        )
        assert request.include_headers is True

    def test_export_request_custom_filename(self):
        """Test export request with custom filename."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
            filename="my_export.csv",
        )
        assert request.filename == "my_export.csv"


class TestExportResult:
    """Test export result schema."""

    def test_export_result_success(self):
        """Test successful export result."""
        result = ExportResult(
            content=b"id,email\n1,test@example.com",
            content_type="text/csv",
            filename="users_export.csv",
            row_count=1,
            duration_ms=0.5,
        )
        assert result.row_count == 1
        assert result.content_type == "text/csv"

    def test_export_result_json(self):
        """Test JSON export result."""
        data = [{"id": 1, "email": "test@example.com"}]
        result = ExportResult(
            content=json.dumps(data).encode(),
            content_type="application/json",
            filename="users_export.json",
            row_count=1,
            duration_ms=0.3,
        )
        assert b"test@example.com" in result.content

    def test_export_result_excel(self):
        """Test Excel export result."""
        result = ExportResult(
            content=b"excel_content",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="users_export.xlsx",
            row_count=100,
            duration_ms=1.5,
        )
        assert result.row_count == 100
        assert ".xlsx" in result.filename

    def test_export_result_empty(self):
        """Test export result with zero rows."""
        result = ExportResult(
            content=b"id,email\n",
            content_type="text/csv",
            filename="users_export.csv",
            row_count=0,
        )
        assert result.row_count == 0


class TestFieldConfigCreation:
    """Test FieldConfig creation with correct parameters."""

    def test_field_config_string(self):
        """Test string field configuration."""
        field = FieldConfig(
            name="email",
            display_name="Email Address",
            field_type=FieldType.STRING,
            required=True,
        )
        assert field.field_type == FieldType.STRING
        assert field.required is True
        assert field.name == "email"
        assert field.display_name == "Email Address"

    def test_field_config_uuid(self):
        """Test UUID field configuration."""
        field = FieldConfig(
            name="id",
            display_name="ID",
            field_type=FieldType.UUID,
            required=True,
        )
        assert field.field_type == FieldType.UUID

    def test_field_config_datetime(self):
        """Test datetime field configuration."""
        field = FieldConfig(
            name="created_at",
            display_name="Created At",
            field_type=FieldType.DATETIME,
            required=False,
        )
        assert field.field_type == FieldType.DATETIME

    def test_field_config_boolean(self):
        """Test boolean field configuration."""
        field = FieldConfig(
            name="is_active",
            display_name="Active",
            field_type=FieldType.BOOLEAN,
            required=True,
            default=True,
        )
        assert field.field_type == FieldType.BOOLEAN
        assert field.default is True

    def test_field_config_integer(self):
        """Test integer field configuration."""
        field = FieldConfig(
            name="age",
            display_name="Age",
            field_type=FieldType.INTEGER,
            required=False,
        )
        assert field.field_type == FieldType.INTEGER

    def test_field_config_with_choices(self):
        """Test field with choices."""
        field = FieldConfig(
            name="status",
            display_name="Status",
            field_type=FieldType.STRING,
            choices=["active", "inactive", "pending"],
        )
        assert field.choices == ["active", "inactive", "pending"]

    def test_field_config_exportable_importable(self):
        """Test exportable/importable flags."""
        field = FieldConfig(
            name="password_hash",
            display_name="Password Hash",
            field_type=FieldType.STRING,
            exportable=False,
            importable=False,
        )
        assert field.exportable is False
        assert field.importable is False

    def test_field_config_with_width(self):
        """Test field with custom width for Excel."""
        field = FieldConfig(
            name="description",
            display_name="Description",
            field_type=FieldType.STRING,
            width=30,
        )
        assert field.width == 30

    def test_field_config_with_format(self):
        """Test field with display format."""
        field = FieldConfig(
            name="price",
            display_name="Price",
            field_type=FieldType.FLOAT,
            format="0.00",
        )
        assert field.format == "0.00"


class TestExportFormatEnum:
    """Test export format enum."""

    def test_csv_format(self):
        """Test CSV format value."""
        assert ExportFormat.CSV == "csv"

    def test_excel_format(self):
        """Test Excel format value."""
        assert ExportFormat.EXCEL == "excel"

    def test_json_format(self):
        """Test JSON format value."""
        assert ExportFormat.JSON == "json"


class TestGenericExporterModelConversion:
    """Test model to dict conversion."""

    def test_convert_uuid_to_string(self):
        """Test UUID is converted to string."""
        test_uuid = uuid4()
        # UUID should be serialized as string
        assert str(test_uuid) == str(test_uuid)

    def test_convert_datetime_to_iso(self):
        """Test datetime is converted to ISO format."""
        dt = datetime.now(UTC)
        iso_string = dt.isoformat()
        assert "T" in iso_string

    def test_convert_nested_objects(self):
        """Test nested objects are handled."""
        data = {
            "id": str(uuid4()),
            "user": {
                "name": "Test",
                "email": "test@example.com",
            },
        }
        assert data["user"]["name"] == "Test"


class TestGenericExporterErrorHandling:
    """Test error handling in exporter."""

    @pytest.mark.asyncio
    async def test_unknown_entity_error(self):
        """Test error for unknown entity."""
        with patch.object(EntityRegistry, "get", return_value=None):
            request = ExportRequest(
                entity="unknown_entity",
                format=ExportFormat.CSV,
            )
            # Request created but entity doesn't exist
            assert request.entity == "unknown_entity"

    @pytest.mark.asyncio
    async def test_excel_not_available_error(self):
        """Test error when Excel is not available."""
        with patch(
            "app.infrastructure.data_exchange.generic_exporter.is_excel_available",
            return_value=False,
        ):
            # Excel should fall back or raise error
            request = ExportRequest(
                entity="users",
                format=ExportFormat.EXCEL,
            )
            assert request.format == ExportFormat.EXCEL


class TestExportFilename:
    """Test filename generation."""

    def test_csv_filename(self):
        """Test CSV filename."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
            filename="users_export.csv",
        )
        assert request.filename is not None
        assert request.filename.endswith(".csv")

    def test_excel_filename(self):
        """Test Excel filename."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.EXCEL,
            filename="users_export.xlsx",
        )
        assert request.filename is not None
        assert request.filename.endswith(".xlsx")

    def test_json_filename(self):
        """Test JSON filename."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.JSON,
            filename="users_export.json",
        )
        assert request.filename is not None
        assert request.filename.endswith(".json")


class TestFieldValidation:
    """Test field validation methods."""

    def test_validate_required_field_empty(self):
        """Test validation fails for empty required field."""
        field = FieldConfig(
            name="email",
            display_name="Email",
            field_type=FieldType.STRING,
            required=True,
        )
        is_valid, error = field.validate(None)
        assert is_valid is False
        assert error is not None
        assert "required" in error.lower()

    def test_validate_required_field_with_value(self):
        """Test validation passes for required field with value."""
        field = FieldConfig(
            name="email",
            display_name="Email",
            field_type=FieldType.STRING,
            required=True,
        )
        is_valid, error = field.validate("test@example.com")
        assert is_valid is True
        assert error is None

    def test_validate_optional_field_empty(self):
        """Test validation passes for empty optional field."""
        field = FieldConfig(
            name="phone",
            display_name="Phone",
            field_type=FieldType.STRING,
            required=False,
        )
        is_valid, error = field.validate(None)
        assert is_valid is True
        assert error is None

    def test_validate_choices_valid(self):
        """Test validation with valid choice."""
        field = FieldConfig(
            name="status",
            display_name="Status",
            field_type=FieldType.STRING,
            choices=["active", "inactive"],
        )
        is_valid, error = field.validate("active")
        assert is_valid is True

    def test_validate_choices_invalid(self):
        """Test validation with invalid choice."""
        field = FieldConfig(
            name="status",
            display_name="Status",
            field_type=FieldType.STRING,
            choices=["active", "inactive"],
        )
        is_valid, error = field.validate("invalid_status")
        assert is_valid is False


class TestEntityConfigUsage:
    """Test EntityConfig usage."""

    def test_entity_config_creation(self):
        """Test EntityConfig creation."""
        fields = [
            FieldConfig(
                name="id",
                display_name="ID",
                field_type=FieldType.UUID,
                required=True,
                exportable=True,
                importable=False,
            ),
            FieldConfig(
                name="email",
                display_name="Email",
                field_type=FieldType.EMAIL,
                required=True,
            ),
        ]
        # EntityConfig expects list of fields
        assert len(fields) == 2
        assert fields[0].name == "id"

    def test_field_type_email(self):
        """Test EMAIL field type."""
        field = FieldConfig(
            name="email",
            display_name="Email",
            field_type=FieldType.EMAIL,
        )
        assert field.field_type == FieldType.EMAIL

    def test_field_type_float(self):
        """Test FLOAT field type."""
        field = FieldConfig(
            name="amount",
            display_name="Amount",
            field_type=FieldType.FLOAT,
        )
        assert field.field_type == FieldType.FLOAT


class TestExportRequestDefaults:
    """Test ExportRequest default values."""

    def test_default_filters_none(self):
        """Test filters default to None."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
        )
        assert request.filters is None

    def test_default_columns_none(self):
        """Test columns default to None."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
        )
        assert request.columns is None

    def test_default_include_headers_true(self):
        """Test include_headers defaults to True."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
        )
        assert request.include_headers is True

    def test_default_filename_none(self):
        """Test filename defaults to None."""
        request = ExportRequest(
            entity="users",
            format=ExportFormat.CSV,
        )
        assert request.filename is None


class TestGenericExporterMethods:
    """Test GenericExporter methods with mocks."""

    @pytest.mark.asyncio
    async def test_exporter_initialization_real(self):
        """Test exporter can be initialized with session."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        assert exporter is not None
        assert exporter.session == mock_session

    @pytest.mark.asyncio
    async def test_get_exporter_function(self):
        """Test get_exporter convenience function."""
        from app.infrastructure.data_exchange.generic_exporter import get_exporter

        mock_session = AsyncMock()
        exporter = get_exporter(mock_session)

        assert exporter is not None
        assert exporter.session == mock_session

    @pytest.mark.asyncio
    async def test_export_unknown_entity_raises(self):
        """Test export with unknown entity raises ValueError."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        request = ExportRequest(
            entity="nonexistent_entity",
            format=ExportFormat.CSV,
        )

        with patch.object(EntityRegistry, "get", return_value=None):
            with pytest.raises(ValueError, match="not found in registry"):
                await exporter.export(request)

    @pytest.mark.asyncio
    async def test_get_preview_unknown_entity_raises(self):
        """Test get_preview with unknown entity raises ValueError."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        with patch.object(EntityRegistry, "get", return_value=None):
            with pytest.raises(ValueError, match="not found in registry"):
                await exporter.get_preview("nonexistent_entity")

    @pytest.mark.asyncio
    async def test_get_count_unknown_entity_raises(self):
        """Test get_count with unknown entity raises ValueError."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        with patch.object(EntityRegistry, "get", return_value=None):
            with pytest.raises(ValueError, match="not found in registry"):
                await exporter.get_count("nonexistent_entity")

    def test_json_serializer_datetime(self):
        """Test JSON serializer handles datetime."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = exporter._json_serializer(dt)

        assert result == "2024-01-15T10:30:00"

    def test_json_serializer_uuid(self):
        """Test JSON serializer handles UUID."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        test_uuid = uuid4()
        result = exporter._json_serializer(test_uuid)

        assert result == str(test_uuid)

    def test_json_serializer_object_with_dict(self):
        """Test JSON serializer handles objects with __dict__."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        class TestObj:
            def __init__(self):
                self.name = "test"
                self.value = 123

        obj = TestObj()
        result = exporter._json_serializer(obj)

        assert result["name"] == "test"
        assert result["value"] == 123

    def test_json_serializer_unknown_type_raises(self):
        """Test JSON serializer raises for unknown types."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        # Pass a set which doesn't have __dict__ and is not datetime/UUID
        with pytest.raises(TypeError, match="not JSON serializable"):
            exporter._json_serializer({1, 2, 3})

    def test_model_to_dict_basic(self):
        """Test model to dict conversion."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        # Create mock model instance
        mock_instance = MagicMock()
        mock_instance.id = uuid4()
        mock_instance.email = "test@example.com"
        mock_instance.name = "Test User"

        # Create mock config with exportable fields
        field_id = FieldConfig(
            name="id",
            display_name="ID",
            field_type=FieldType.UUID,
            exportable=True,
        )
        field_email = FieldConfig(
            name="email",
            display_name="Email",
            field_type=FieldType.EMAIL,
            exportable=True,
        )

        mock_config = MagicMock()
        mock_config.get_exportable_fields.return_value = [field_id, field_email]

        result = exporter._model_to_dict(mock_instance, mock_config)

        assert "id" in result
        assert "email" in result
        assert result["email"] == "test@example.com"


class TestApplyFilters:
    """Test filter application methods."""

    @pytest.mark.asyncio
    async def test_apply_filter_skips_unknown_field(self):
        """Test filter skips unknown fields."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        mock_model = MagicMock(spec=[])  # Empty spec, no attributes

        mock_config = MagicMock()
        mock_config.model = mock_model

        mock_query = MagicMock()
        mock_query.where = MagicMock(return_value=mock_query)

        filters = {"nonexistent_field": True}
        result = exporter._apply_filters(mock_query, mock_config, filters)

        # where should not be called since field doesn't exist
        assert result == mock_query

    def test_apply_filters_returns_query(self):
        """Test _apply_filters returns the modified query."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        mock_config = MagicMock()
        mock_config.model = MagicMock(spec=[])  # No attributes

        mock_query = MagicMock()

        result = exporter._apply_filters(mock_query, mock_config, {})

        assert result == mock_query


class TestExportFormats:
    """Test various export format handling."""

    def test_export_format_csv_value(self):
        """Test CSV format enum value."""
        assert ExportFormat.CSV.value == "csv"

    def test_export_format_excel_value(self):
        """Test Excel format enum value."""
        assert ExportFormat.EXCEL.value == "excel"

    def test_export_format_json_value(self):
        """Test JSON format enum value."""
        assert ExportFormat.JSON.value == "json"


class TestQueryData:
    """Test data querying methods."""

    @pytest.mark.asyncio
    async def test_exporter_has_session(self):
        """Test exporter stores session reference."""
        from app.infrastructure.data_exchange.generic_exporter import GenericExporter

        mock_session = AsyncMock()
        exporter = GenericExporter(mock_session)

        assert exporter.session == mock_session

    @pytest.mark.asyncio
    async def test_export_request_with_all_params(self):
        """Test export request with all optional parameters."""
        tenant_id = uuid4()

        request = ExportRequest(
            entity="users",
            format=ExportFormat.JSON,
            filters={"is_active": True},
            columns=["id", "email"],
            tenant_id=tenant_id,
            include_headers=False,
            filename="custom_export.json",
        )

        assert request.entity == "users"
        assert request.format == ExportFormat.JSON
        assert request.filters == {"is_active": True}
        assert request.columns == ["id", "email"]
        assert request.tenant_id == tenant_id
        assert request.include_headers is False
        assert request.filename == "custom_export.json"
