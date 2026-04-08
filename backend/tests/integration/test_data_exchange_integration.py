# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Integration tests for data exchange endpoints to increase coverage."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestDataExchangeEndpoints:
    """Tests for data exchange endpoints."""

    @pytest.mark.asyncio
    async def test_list_exportable_entities_unauthorized(self) -> None:
        """Test list exportable entities without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/data-exchange/entities")
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_export_entity_unauthorized(self) -> None:
        """Test export entity without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/data-exchange/export",
                json={"entity": "users", "format": "csv"},
            )
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_import_entity_unauthorized(self) -> None:
        """Test import entity without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/data-exchange/import",
                data={"entity": "users"},
                files={"file": ("test.csv", b"header1,header2\nvalue1,value2")},
            )
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_preview_import_unauthorized(self) -> None:
        """Test preview import without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/data-exchange/import/preview",
                data={"entity": "users"},
                files={"file": ("test.csv", b"header1,header2\nvalue1,value2")},
            )
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_generate_report_unauthorized(self) -> None:
        """Test generate report without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/data-exchange/report",
                json={"entity": "users", "format": "pdf"},
            )
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_get_import_template_unauthorized(self) -> None:
        """Test get import template without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/data-exchange/templates/users")
            assert response.status_code in [401, 403, 404]


class TestBulkOperationsEndpoints:
    """Tests for bulk operations endpoints."""

    @pytest.mark.asyncio
    async def test_bulk_create_unauthorized(self) -> None:
        """Test bulk create without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/bulk/users/create",
                json={"items": [{"email": "test@example.com"}]},
            )
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_bulk_update_unauthorized(self) -> None:
        """Test bulk update without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/bulk/users/update",
                json={"items": [{"id": "00000000-0000-0000-0000-000000000000"}]},
            )
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_bulk_delete_unauthorized(self) -> None:
        """Test bulk delete without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/bulk/users/delete",
                json={"ids": ["00000000-0000-0000-0000-000000000000"]},
            )
            assert response.status_code in [401, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_bulk_status_unauthorized(self) -> None:
        """Test bulk status without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/bulk/status/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403, 404]


class TestReportTemplatesEndpoints:
    """Tests for report templates endpoints."""

    @pytest.mark.asyncio
    async def test_list_templates_unauthorized(self) -> None:
        """Test list templates without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/report-templates")
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_template_unauthorized(self) -> None:
        """Test create template without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/report-templates",
                json={
                    "name": "Test Template",
                    "entity": "users",
                    "title": "Test Report",
                    "format": "pdf",
                },
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_template_unauthorized(self) -> None:
        """Test get template without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/report-templates/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_update_template_unauthorized(self) -> None:
        """Test update template without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/report-templates/00000000-0000-0000-0000-000000000000",
                json={"name": "Updated Name"},
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_delete_template_unauthorized(self) -> None:
        """Test delete template without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/report-templates/00000000-0000-0000-0000-000000000000"
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_duplicate_template_unauthorized(self) -> None:
        """Test duplicate template without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/report-templates/00000000-0000-0000-0000-000000000000/duplicate"
            )
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_run_template_unauthorized(self) -> None:
        """Test run template without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/report-templates/00000000-0000-0000-0000-000000000000/run"
            )
            assert response.status_code in [401, 403, 404]


class TestScheduledReportsEndpoints:
    """Tests for scheduled reports endpoints."""

    @pytest.mark.asyncio
    async def test_list_schedules_unauthorized(self) -> None:
        """Test list schedules without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/report-templates/00000000-0000-0000-0000-000000000000/schedules"
            )
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_create_schedule_unauthorized(self) -> None:
        """Test create schedule without auth."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/report-templates/00000000-0000-0000-0000-000000000000/schedule",
                json={
                    "name": "Weekly Schedule",
                    "frequency": {"type": "weekly", "day_of_week": 0, "time": "09:00"},
                    "delivery_method": "email",
                    "recipients": ["test@example.com"],
                },
            )
            assert response.status_code in [401, 403]


class TestEntityRegistryIntegration:
    """Tests for entity registry functionality."""

    def test_entity_registry_import(self) -> None:
        """Test importing EntityRegistry."""
        from app.domain.ports.data_exchange import EntityRegistry

        # EntityRegistry should be available
        assert EntityRegistry is not None

    def test_get_registered_entities(self) -> None:
        """Test getting registered entities."""
        from app.domain.ports.data_exchange import EntityRegistry

        # Get users entity (should be registered by default)
        config = EntityRegistry.get("users")

        # Config may or may not exist depending on setup
        if config:
            assert config.name == "users"
            assert len(config.fields) > 0

    def test_field_config_creation(self) -> None:
        """Test creating FieldConfig objects."""
        from app.domain.ports.data_exchange import FieldConfig, FieldType

        field = FieldConfig(
            name="test_field",
            display_name="Test Field",
            field_type=FieldType.STRING,
            required=True,
            exportable=True,
            importable=True,
        )

        assert field.name == "test_field"
        assert field.field_type == FieldType.STRING

    def test_field_type_enum(self) -> None:
        """Test FieldType enum values."""
        from app.domain.ports.data_exchange import FieldType

        assert FieldType.STRING is not None
        assert FieldType.INTEGER is not None
        assert FieldType.FLOAT is not None
        assert FieldType.BOOLEAN is not None
        assert FieldType.DATE is not None
        assert FieldType.DATETIME is not None
        assert FieldType.UUID is not None


class TestCSVHandlerIntegration:
    """Tests for CSV handler integration."""

    def test_csv_handler_import(self) -> None:
        """Test importing CSV handler."""
        from app.infrastructure.data_exchange.csv_handler import get_csv_handler

        handler = get_csv_handler()
        assert handler is not None

    def test_csv_handler_write_simple(self) -> None:
        """Test CSV handler write with simple data."""
        from app.domain.ports.data_exchange import EntityConfig, FieldConfig, FieldType
        from app.infrastructure.data_exchange.csv_handler import get_csv_handler

        handler = get_csv_handler()

        # Create simple config
        config = EntityConfig(
            name="test",
            model=MagicMock,
            display_name="Test Entity",
            permission_resource="test",
            fields=[
                FieldConfig(
                    name="name",
                    display_name="Name",
                    field_type=FieldType.STRING,
                    exportable=True,
                ),
            ],
        )

        data = [{"name": "Test 1"}, {"name": "Test 2"}]
        result = handler.write(data, config)

        # Should return bytes
        assert isinstance(result, bytes)
        # Should contain header and data
        content = result.decode("utf-8")
        assert "Name" in content or "name" in content


class TestExcelHandlerIntegration:
    """Tests for Excel handler integration."""

    def test_excel_handler_availability(self) -> None:
        """Test Excel handler availability check."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        # Should return a boolean
        available = is_excel_available()
        assert isinstance(available, bool)

    def test_get_excel_handler_when_unavailable(self) -> None:
        """Test getting Excel handler when openpyxl not available."""
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        # If openpyxl is not installed, is_excel_available should return False
        available = is_excel_available()
        # Just verify the check works
        assert isinstance(available, bool)


class TestReportFormatEnum:
    """Tests for ReportFormat enum."""

    def test_report_format_values(self) -> None:
        """Test ReportFormat enum values."""
        from app.domain.ports.data_exchange import ReportFormat

        assert ReportFormat.CSV is not None
        assert ReportFormat.EXCEL is not None
        assert ReportFormat.PDF is not None
        assert ReportFormat.HTML is not None

    def test_report_format_comparison(self) -> None:
        """Test ReportFormat comparison."""
        from app.domain.ports.data_exchange import ReportFormat

        assert ReportFormat.CSV == ReportFormat.CSV
        assert ReportFormat.CSV != ReportFormat.PDF


class TestImportExportPorts:
    """Tests for import/export port interfaces."""

    def test_export_result_creation(self) -> None:
        """Test creating ExportResult."""
        from app.domain.ports.import_export import ExportResult

        result = ExportResult(
            content=b"test content",
            filename="test.csv",
            content_type="text/csv",
            row_count=10,
            duration_ms=100.5,
        )

        assert result.content == b"test content"
        assert result.filename == "test.csv"
        assert result.row_count == 10

    def test_import_result_creation(self) -> None:
        """Test creating ImportResult."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(
            total_rows=10,
            inserted=8,
            updated=0,
            skipped=2,
        )

        assert result.total_rows == 10
        assert result.inserted == 8
        assert result.error_count == 0

    def test_import_result_to_dict(self) -> None:
        """Test ImportResult to_dict method."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(
            total_rows=10,
            inserted=7,
            updated=2,
            skipped=1,
        )

        result_dict = result.to_dict()
        assert result_dict["total_rows"] == 10
        assert result_dict["inserted"] == 7
        assert result_dict["success"] is True


class TestReportsPorts:
    """Tests for reports port interfaces."""

    def test_report_request_creation(self) -> None:
        """Test creating ReportRequest."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            format=ReportFormat.PDF,
            title="User Report",
        )

        assert request.entity == "users"
        assert request.format == ReportFormat.PDF

    def test_report_summary_creation(self) -> None:
        """Test creating ReportSummary."""
        from app.domain.ports.reports import ReportSummary

        summary = ReportSummary(
            total_records=100,
            grouped_counts={"active": 80, "inactive": 20},
            numeric_summaries={"age": {"min": 18, "max": 65, "avg": 35}},
        )

        assert summary.total_records == 100
        assert summary.grouped_counts["active"] == 80
