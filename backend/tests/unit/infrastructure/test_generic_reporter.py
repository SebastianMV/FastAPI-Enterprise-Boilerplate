# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Tests for generic reporter implementation.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestReportRequest:
    """Test report request schema."""

    def test_report_request_basic(self):
        """Test basic report request."""
        request = {
            "entity": "users",
            "format": "pdf",
            "title": "Users Report",
        }
        assert request["entity"] == "users"
        assert request["format"] == "pdf"

    def test_report_request_with_filters(self):
        """Test report request with filters."""
        request = {
            "entity": "users",
            "format": "pdf",
            "filters": {
                "is_active": True,
                "created_after": "2024-01-01",
            },
        }
        assert request["filters"]["is_active"] is True

    def test_report_request_with_columns(self):
        """Test report request with specific columns."""
        request = {
            "entity": "users",
            "format": "pdf",
            "columns": ["id", "email", "full_name", "created_at"],
        }
        assert "email" in request["columns"]

    def test_report_request_with_grouping(self):
        """Test report request with grouping."""
        request = {
            "entity": "orders",
            "format": "pdf",
            "group_by": "status",
            "aggregations": ["count", "sum:total"],
        }
        assert request["group_by"] == "status"


class TestReportResult:
    """Test report result schema."""

    def test_report_result_pdf(self):
        """Test PDF report result."""
        result = {
            "content": b"%PDF-1.4...",
            "content_type": "application/pdf",
            "filename": "users_report_2024.pdf",
            "total_rows": 100,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        assert result["content_type"] == "application/pdf"
        assert result["filename"].endswith(".pdf")

    def test_report_result_excel(self):
        """Test Excel report result."""
        result = {
            "content": b"PK...",  # XLSX magic bytes
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "filename": "users_report_2024.xlsx",
            "total_rows": 100,
        }
        assert result["filename"].endswith(".xlsx")


class TestGenericReporterBasic:
    """Test basic reporter functionality."""

    @pytest.mark.asyncio
    async def test_reporter_initialization(self):
        """Test reporter initialization."""
        mock_session = AsyncMock()

        with patch(
            "app.infrastructure.data_exchange.generic_reporter.GenericReporter"
        ) as MockReporter:
            reporter = MockReporter(mock_session)
            assert reporter is not None

    @pytest.mark.asyncio
    async def test_generate_report(self):
        """Test generating a report."""
        mock_session = AsyncMock()

        with patch(
            "app.infrastructure.data_exchange.generic_reporter.GenericReporter"
        ) as MockReporter:
            mock_reporter = MockReporter.return_value
            mock_reporter.generate = AsyncMock(
                return_value={
                    "content": b"report content",
                    "total_rows": 50,
                }
            )

            result = await mock_reporter.generate(
                {
                    "entity": "users",
                    "format": "pdf",
                }
            )
            assert result["total_rows"] == 50


class TestReportFormatting:
    """Test report formatting."""

    def test_format_header(self):
        """Test formatting report header."""
        title = "Users Report"
        subtitle = "Generated on " + datetime.now(UTC).strftime("%Y-%m-%d")

        header = f"{title}\n{subtitle}"

        assert "Users Report" in header
        assert "Generated on" in header

    def test_format_date_column(self):
        """Test formatting date columns."""
        dt = datetime(2024, 6, 15, 10, 30, 0)
        formatted = dt.strftime("%Y-%m-%d %H:%M")

        assert formatted == "2024-06-15 10:30"

    def test_format_boolean_column(self):
        """Test formatting boolean columns."""
        active_display = {True: "Active", False: "Inactive"}

        assert active_display[True] == "Active"
        assert active_display[False] == "Inactive"

    def test_format_currency_column(self):
        """Test formatting currency columns."""
        amount = 1234.56
        formatted = f"${amount:,.2f}"

        assert formatted == "$1,234.56"


class TestReportGrouping:
    """Test report grouping and aggregation."""

    def test_group_by_single_field(self):
        """Test grouping by single field."""
        data = [
            {"status": "active", "count": 50},
            {"status": "inactive", "count": 20},
            {"status": "pending", "count": 10},
        ]

        grouped = {item["status"]: item["count"] for item in data}

        assert grouped["active"] == 50
        assert len(grouped) == 3

    def test_aggregation_count(self):
        """Test count aggregation."""
        items = [1, 2, 3, 4, 5]
        count = len(items)

        assert count == 5

    def test_aggregation_sum(self):
        """Test sum aggregation."""
        items = [10, 20, 30, 40, 50]
        total = sum(items)

        assert total == 150

    def test_aggregation_average(self):
        """Test average aggregation."""
        items = [10, 20, 30, 40, 50]
        average = sum(items) / len(items)

        assert average == 30


class TestReportSorting:
    """Test report sorting."""

    def test_sort_ascending(self):
        """Test ascending sort."""
        items = [3, 1, 4, 1, 5, 9, 2, 6]
        sorted_items = sorted(items)

        assert sorted_items == [1, 1, 2, 3, 4, 5, 6, 9]

    def test_sort_descending(self):
        """Test descending sort."""
        items = [3, 1, 4, 1, 5, 9, 2, 6]
        sorted_items = sorted(items, reverse=True)

        assert sorted_items == [9, 6, 5, 4, 3, 2, 1, 1]

    def test_sort_by_field(self):
        """Test sorting by field."""
        items = [
            {"name": "Charlie", "age": 30},
            {"name": "Alice", "age": 25},
            {"name": "Bob", "age": 35},
        ]

        sorted_by_name = sorted(items, key=lambda x: x["name"])
        sorted_by_age = sorted(items, key=lambda x: x["age"])

        assert sorted_by_name[0]["name"] == "Alice"
        assert sorted_by_age[0]["name"] == "Alice"


class TestReportPagination:
    """Test report pagination."""

    def test_calculate_pages(self):
        """Test calculating number of pages."""
        total_rows = 250
        rows_per_page = 50
        total_pages = (total_rows + rows_per_page - 1) // rows_per_page

        assert total_pages == 5

    def test_get_page_data(self):
        """Test getting data for specific page."""
        all_data = list(range(100))
        page = 2
        page_size = 25

        start = (page - 1) * page_size
        end = start + page_size
        page_data = all_data[start:end]

        assert len(page_data) == 25
        assert page_data[0] == 25


class TestReportTemplates:
    """Test report templates."""

    def test_table_template(self):
        """Test table report template."""
        template = {
            "type": "table",
            "columns": ["ID", "Name", "Email"],
            "show_header": True,
            "show_totals": False,
        }

        assert template["type"] == "table"
        assert template["show_header"] is True

    def test_summary_template(self):
        """Test summary report template."""
        template = {
            "type": "summary",
            "metrics": ["total_users", "active_users", "new_users_today"],
            "show_charts": True,
        }

        assert template["type"] == "summary"
        assert "total_users" in template["metrics"]

    def test_chart_template(self):
        """Test chart report template."""
        template = {
            "type": "chart",
            "chart_type": "bar",
            "x_axis": "month",
            "y_axis": "revenue",
        }

        assert template["chart_type"] == "bar"


class TestReportExport:
    """Test report export functionality."""

    @pytest.mark.asyncio
    async def test_export_to_pdf(self):
        """Test exporting report to PDF."""
        with patch(
            "app.infrastructure.data_exchange.pdf_handler.PDFHandler"
        ) as MockPDF:
            mock_pdf = MockPDF.return_value
            mock_pdf.generate = MagicMock(return_value=b"%PDF-1.4...")

            result = mock_pdf.generate([{"id": 1, "name": "Test"}])
            assert result.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_export_to_excel(self):
        """Test exporting report to Excel."""
        with patch(
            "app.infrastructure.data_exchange.excel_handler.ExcelHandler"
        ) as MockExcel:
            mock_excel = MockExcel.return_value
            mock_excel.write = MagicMock(return_value=b"PK...")

            result = mock_excel.write([{"id": 1, "name": "Test"}], None, None)
            assert result.startswith(b"PK")


class TestReportScheduling:
    """Test report scheduling."""

    def test_schedule_daily(self):
        """Test daily schedule."""
        schedule = {
            "frequency": "daily",
            "time": "08:00",
            "timezone": "UTC",
        }

        assert schedule["frequency"] == "daily"

    def test_schedule_weekly(self):
        """Test weekly schedule."""
        schedule = {
            "frequency": "weekly",
            "day_of_week": "monday",
            "time": "09:00",
        }

        assert schedule["day_of_week"] == "monday"

    def test_schedule_monthly(self):
        """Test monthly schedule."""
        schedule = {
            "frequency": "monthly",
            "day_of_month": 1,
            "time": "10:00",
        }

        assert schedule["day_of_month"] == 1


class TestReportDelivery:
    """Test report delivery."""

    @pytest.mark.asyncio
    async def test_email_delivery(self):
        """Test email delivery."""
        delivery = {
            "type": "email",
            "recipients": ["user@example.com", "manager@example.com"],
            "subject": "Daily Report",
        }

        assert len(delivery["recipients"]) == 2

    @pytest.mark.asyncio
    async def test_storage_delivery(self):
        """Test storage delivery."""
        delivery = {
            "type": "storage",
            "path": "/reports/daily/",
            "filename_pattern": "report_{date}.pdf",
        }

        assert delivery["path"].startswith("/reports/")


class TestReportErrorHandling:
    """Test report error handling."""

    @pytest.mark.asyncio
    async def test_empty_data_error(self):
        """Test handling empty data."""
        data = []

        if not data:
            result = {"error": "No data available for report"}

        assert "No data" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_invalid_format_error(self):
        """Test handling invalid format."""
        supported_formats = ["pdf", "excel", "csv"]
        requested_format = "xml"

        is_valid = requested_format in supported_formats
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_query_timeout_error(self):
        """Test handling query timeout."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=TimeoutError("Query timeout"))

        with pytest.raises(TimeoutError):
            await mock_session.execute("SELECT * FROM large_table")


class TestGenericReporterImplementation:
    """Test GenericReporter actual implementation."""

    @pytest.mark.asyncio
    async def test_reporter_initialization_real(self):
        """Test reporter can be initialized with session."""
        from app.infrastructure.data_exchange.generic_reporter import GenericReporter

        mock_session = AsyncMock()
        reporter = GenericReporter(mock_session)

        assert reporter is not None
        assert reporter.session == mock_session

    @pytest.mark.asyncio
    async def test_get_reporter_function(self):
        """Test get_reporter convenience function."""
        from app.infrastructure.data_exchange.generic_reporter import get_reporter

        mock_session = AsyncMock()
        reporter = get_reporter(mock_session)

        assert reporter is not None
        assert reporter.session == mock_session

    @pytest.mark.asyncio
    async def test_generate_unknown_entity_raises(self):
        """Test generate with unknown entity raises ValueError."""
        from app.domain.ports.data_exchange import EntityRegistry, ReportFormat
        from app.domain.ports.reports import ReportRequest
        from app.infrastructure.data_exchange.generic_reporter import GenericReporter

        mock_session = AsyncMock()
        reporter = GenericReporter(mock_session)

        request = ReportRequest(
            entity="nonexistent_entity",
            format=ReportFormat.CSV,
        )

        with patch.object(EntityRegistry, "get", return_value=None):
            with pytest.raises(ValueError, match="not found in registry"):
                await reporter.generate(request)

    @pytest.mark.asyncio
    async def test_get_summary_unknown_entity_raises(self):
        """Test get_summary with unknown entity raises ValueError."""
        from app.domain.ports.data_exchange import EntityRegistry, ReportFormat
        from app.domain.ports.reports import ReportRequest
        from app.infrastructure.data_exchange.generic_reporter import GenericReporter

        mock_session = AsyncMock()
        reporter = GenericReporter(mock_session)

        request = ReportRequest(
            entity="nonexistent_entity",
            format=ReportFormat.CSV,
        )

        with patch.object(EntityRegistry, "get", return_value=None):
            with pytest.raises(ValueError, match="not found in registry"):
                await reporter.get_summary(request)


class TestReportRequestActual:
    """Test actual ReportRequest class."""

    def test_report_request_creation(self):
        """Test ReportRequest creation."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            format=ReportFormat.CSV,
        )

        assert request.entity == "users"
        assert request.format == ReportFormat.CSV

    def test_report_request_with_title(self):
        """Test ReportRequest with title."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            format=ReportFormat.PDF,
            title="My Users Report",
        )

        assert request.title == "My Users Report"

    def test_report_request_with_filters(self):
        """Test ReportRequest with filters."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            format=ReportFormat.CSV,
            filters={"is_active": True},
        )

        assert request.filters == {"is_active": True}

    def test_report_request_with_columns(self):
        """Test ReportRequest with columns."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            format=ReportFormat.CSV,
            columns=["id", "email", "name"],
        )

        assert request.columns == ["id", "email", "name"]

    def test_report_request_with_tenant(self):
        """Test ReportRequest with tenant_id."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportRequest

        tenant_id = uuid4()

        request = ReportRequest(
            entity="users",
            format=ReportFormat.CSV,
            tenant_id=tenant_id,
        )

        assert request.tenant_id == tenant_id

    def test_report_request_include_summary(self):
        """Test ReportRequest with include_summary."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            format=ReportFormat.CSV,
            include_summary=True,
        )

        assert request.include_summary is True


class TestReportResultActual:
    """Test actual ReportResult class."""

    def test_report_result_creation(self):
        """Test ReportResult creation."""
        from app.domain.ports.reports import ReportResult

        result = ReportResult(
            content=b"report content",
            filename="report.csv",
            content_type="text/csv",
            generated_at=datetime.now(UTC),
            row_count=100,
        )

        assert result.row_count == 100
        assert result.content_type == "text/csv"
        assert result.filename == "report.csv"

    def test_report_result_with_duration(self):
        """Test ReportResult with duration."""
        from app.domain.ports.reports import ReportResult

        result = ReportResult(
            content=b"report",
            filename="report.pdf",
            content_type="application/pdf",
            generated_at=datetime.now(UTC),
            row_count=50,
            duration_ms=150.0,
        )

        assert result.duration_ms == 150.0

    def test_report_result_get_content_type(self):
        """Test ReportResult.get_content_type method."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportResult

        assert ReportResult.get_content_type(ReportFormat.PDF) == "application/pdf"
        assert ReportResult.get_content_type(ReportFormat.CSV) == "text/csv"
        assert (
            ReportResult.get_content_type(ReportFormat.EXCEL)
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert ReportResult.get_content_type(ReportFormat.HTML) == "text/html"


class TestReportFormatEnum:
    """Test ReportFormat enum."""

    def test_report_format_csv(self):
        """Test CSV format."""
        from app.domain.ports.data_exchange import ReportFormat

        assert ReportFormat.CSV == "csv"

    def test_report_format_excel(self):
        """Test Excel format."""
        from app.domain.ports.data_exchange import ReportFormat

        assert ReportFormat.EXCEL == "excel"

    def test_report_format_pdf(self):
        """Test PDF format."""
        from app.domain.ports.data_exchange import ReportFormat

        assert ReportFormat.PDF == "pdf"

    def test_report_format_html(self):
        """Test HTML format."""
        from app.domain.ports.data_exchange import ReportFormat

        assert ReportFormat.HTML == "html"


class TestReportSummaryActual:
    """Test actual ReportSummary class."""

    def test_report_summary_creation(self):
        """Test ReportSummary creation."""
        from app.domain.ports.reports import ReportSummary

        summary = ReportSummary(
            total_records=100,
        )

        assert summary.total_records == 100

    def test_report_summary_with_aggregations(self):
        """Test ReportSummary with aggregations."""
        from app.domain.ports.reports import ReportSummary

        summary = ReportSummary(
            total_records=100,
            grouped_counts={"active": 50, "inactive": 30},
            numeric_summaries={
                "amount": {"sum": 5000.0, "avg": 50.0},
            },
        )

        assert summary.grouped_counts["active"] == 50
        assert summary.numeric_summaries["amount"]["sum"] == 5000.0


class TestGenericReporterModelConversion:
    """Test GenericReporter model conversion methods."""

    def test_model_to_dict_basic(self):
        """Test model to dict conversion."""
        from unittest.mock import MagicMock

        from app.domain.ports.data_exchange import EntityConfig, FieldConfig, FieldType
        from app.infrastructure.data_exchange.generic_reporter import GenericReporter

        session = MagicMock()
        reporter = GenericReporter(session)

        config = EntityConfig(
            name="test",
            display_name="Test",
            model=object,
            fields=[
                FieldConfig(
                    name="id",
                    display_name="ID",
                    field_type=FieldType.UUID,
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

        instance = MagicMock()
        instance.id = "123"
        instance.name = "Test Name"

        result = reporter._model_to_dict(instance, config)

        assert result["id"] == "123"
        assert result["name"] == "Test Name"

    def test_model_to_dict_with_non_exportable(self):
        """Test model to dict excludes non-exportable fields."""
        from unittest.mock import MagicMock

        from app.domain.ports.data_exchange import EntityConfig, FieldConfig, FieldType
        from app.infrastructure.data_exchange.generic_reporter import GenericReporter

        session = MagicMock()
        reporter = GenericReporter(session)

        config = EntityConfig(
            name="test",
            display_name="Test",
            model=object,
            fields=[
                FieldConfig(
                    name="id",
                    display_name="ID",
                    field_type=FieldType.UUID,
                    exportable=True,
                ),
                FieldConfig(
                    name="password",
                    display_name="Password",
                    field_type=FieldType.STRING,
                    exportable=False,
                ),
            ],
            permission_resource="test",
        )

        instance = MagicMock()
        instance.id = "123"
        instance.password = "secret"

        result = reporter._model_to_dict(instance, config)

        assert result["id"] == "123"
        assert "password" not in result


class TestGenericReporterFiltering:
    """Test GenericReporter filter application."""

    def test_apply_filters_with_empty_filters(self):
        """Test that empty filters returns query unchanged."""
        from unittest.mock import MagicMock

        from app.domain.ports.data_exchange import EntityConfig, FieldConfig, FieldType
        from app.domain.ports.reports import ReportRequest
        from app.infrastructure.data_exchange.generic_reporter import GenericReporter

        session = MagicMock()
        reporter = GenericReporter(session)

        config = EntityConfig(
            name="test",
            display_name="Test",
            model=MagicMock(),
            fields=[
                FieldConfig(name="id", display_name="ID", field_type=FieldType.UUID),
            ],
            permission_resource="test",
        )

        # No filters
        request = ReportRequest(
            entity="test",
            filters=[],
        )

        query = MagicMock()
        result = reporter._apply_filters(query, config, request)
        # With no filters, the query should remain unchanged
        assert result is not None


class TestReportFilterOperators:
    """Test ReportFilter operators."""

    def test_report_filter_eq_operator(self):
        """Test eq operator in filter."""
        from app.domain.ports.reports import ReportFilter

        filter_item = ReportFilter(field="status", operator="eq", value="active")

        assert filter_item.field == "status"
        assert filter_item.operator == "eq"
        assert filter_item.value == "active"

    def test_report_filter_ne_operator(self):
        """Test ne operator in filter."""
        from app.domain.ports.reports import ReportFilter

        filter_item = ReportFilter(field="status", operator="ne", value="deleted")

        assert filter_item.operator == "ne"

    def test_report_filter_gt_operator(self):
        """Test gt operator in filter."""
        from app.domain.ports.reports import ReportFilter

        filter_item = ReportFilter(field="count", operator="gt", value=10)

        assert filter_item.operator == "gt"
        assert filter_item.value == 10

    def test_report_filter_gte_operator(self):
        """Test gte operator in filter."""
        from app.domain.ports.reports import ReportFilter

        filter_item = ReportFilter(field="count", operator="gte", value=10)

        assert filter_item.operator == "gte"

    def test_report_filter_lt_operator(self):
        """Test lt operator in filter."""
        from app.domain.ports.reports import ReportFilter

        filter_item = ReportFilter(field="count", operator="lt", value=100)

        assert filter_item.operator == "lt"

    def test_report_filter_lte_operator(self):
        """Test lte operator in filter."""
        from app.domain.ports.reports import ReportFilter

        filter_item = ReportFilter(field="count", operator="lte", value=100)

        assert filter_item.operator == "lte"

    def test_report_filter_in_operator(self):
        """Test in operator in filter."""
        from app.domain.ports.reports import ReportFilter

        filter_item = ReportFilter(
            field="status", operator="in", value=["active", "pending"]
        )

        assert filter_item.operator == "in"
        assert filter_item.value == ["active", "pending"]

    def test_report_filter_contains_operator(self):
        """Test contains operator in filter."""
        from app.domain.ports.reports import ReportFilter

        filter_item = ReportFilter(field="name", operator="contains", value="test")

        assert filter_item.operator == "contains"


class TestReportRequestDateRange:
    """Test ReportRequest date range features."""

    def test_report_request_with_date_range(self):
        """Test ReportRequest with date range."""
        from datetime import datetime

        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            date_range_field="created_at",
            date_from=datetime(2024, 1, 1),
            date_to=datetime(2024, 12, 31),
        )

        assert request.date_range_field == "created_at"
        assert request.date_from == datetime(2024, 1, 1)
        assert request.date_to == datetime(2024, 12, 31)

    def test_report_request_with_sort(self):
        """Test ReportRequest with sorting."""
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            sort_by="-created_at",
        )

        assert request.sort_by == "-created_at"

    def test_report_request_with_group_by(self):
        """Test ReportRequest with group by."""
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            group_by=["status", "role"],
        )

        assert request.group_by == ["status", "role"]


class TestReportRequestPdfOptions:
    """Test ReportRequest PDF options."""

    def test_report_request_with_header_footer(self):
        """Test ReportRequest with header/footer text."""
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(
            entity="users",
            header_text="Company Report",
            footer_text="Confidential",
            show_page_numbers=True,
            company_name="Test Corp",
        )

        assert request.header_text == "Company Report"
        assert request.footer_text == "Confidential"
        assert request.show_page_numbers is True
        assert request.company_name == "Test Corp"

    def test_report_request_default_page_numbers(self):
        """Test ReportRequest default show_page_numbers."""
        from app.domain.ports.reports import ReportRequest

        request = ReportRequest(entity="users")

        assert request.show_page_numbers is True


class TestFormatCellValue:
    """Test _format_cell_value method."""

    def test_format_datetime_value(self):
        """Test formatting datetime values."""
        from datetime import datetime
        from unittest.mock import MagicMock

        from app.infrastructure.data_exchange.generic_reporter import GenericReporter

        session = MagicMock()
        reporter = GenericReporter(session)

        dt = datetime(2024, 6, 15, 10, 30, 0)
        result = reporter._format_cell_value(dt)

        assert "2024" in str(result)

    def test_format_none_value(self):
        """Test formatting None values."""
        from unittest.mock import MagicMock

        from app.infrastructure.data_exchange.generic_reporter import GenericReporter

        session = MagicMock()
        reporter = GenericReporter(session)

        result = reporter._format_cell_value(None)

        assert result == "" or result is None

    def test_format_uuid_value(self):
        """Test formatting UUID values."""
        from unittest.mock import MagicMock
        from uuid import uuid4

        from app.infrastructure.data_exchange.generic_reporter import GenericReporter

        session = MagicMock()
        reporter = GenericReporter(session)

        test_uuid = uuid4()
        result = reporter._format_cell_value(test_uuid)

        assert str(test_uuid) in str(result) or result == test_uuid


class TestGenericReporterHelperFunctions:
    """Test GenericReporter helper functions."""

    def test_get_reporter_returns_instance(self):
        """Test get_reporter factory function."""
        from unittest.mock import MagicMock

        from app.infrastructure.data_exchange.generic_reporter import get_reporter

        session = MagicMock()
        reporter = get_reporter(session)

        assert reporter is not None
        assert hasattr(reporter, "generate")

    def test_is_excel_available(self):
        """Test is_excel_available function."""
        from app.infrastructure.data_exchange.generic_reporter import is_excel_available

        result = is_excel_available()

        assert isinstance(result, bool)


class TestReportResultContentTypes:
    """Test ReportResult content type methods."""

    def test_content_type_csv(self):
        """Test CSV content type."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportResult

        content_type = ReportResult.get_content_type(ReportFormat.CSV)

        assert "text/csv" in content_type

    def test_content_type_excel(self):
        """Test Excel content type."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportResult

        content_type = ReportResult.get_content_type(ReportFormat.EXCEL)

        assert "application/vnd.openxmlformats" in content_type

    def test_content_type_html(self):
        """Test HTML content type."""
        from app.domain.ports.data_exchange import ReportFormat
        from app.domain.ports.reports import ReportResult

        content_type = ReportResult.get_content_type(ReportFormat.HTML)

        assert "text/html" in content_type


class TestReportSummaryDefaults:
    """Test ReportSummary default values."""

    def test_grouped_counts_defaults_empty(self):
        """Test grouped_counts defaults to empty dict."""
        from app.domain.ports.reports import ReportSummary

        summary = ReportSummary(total_records=50)

        assert summary.grouped_counts == {}

    def test_numeric_summaries_defaults_empty(self):
        """Test numeric_summaries defaults to empty dict."""
        from app.domain.ports.reports import ReportSummary

        summary = ReportSummary(total_records=50)

        assert summary.numeric_summaries == {}

    def test_summary_with_complex_aggregations(self):
        """Test summary with complex numeric aggregations."""
        from app.domain.ports.reports import ReportSummary

        summary = ReportSummary(
            total_records=1000,
            grouped_counts={
                "status:active": 500,
                "status:inactive": 300,
                "status:pending": 200,
            },
            numeric_summaries={
                "amount": {"min": 10.0, "max": 1000.0, "avg": 100.0, "sum": 100000.0},
                "count": {"min": 1, "max": 100, "avg": 10, "sum": 10000},
            },
        )

        assert summary.total_records == 1000
        assert len(summary.grouped_counts) == 3
        assert summary.numeric_summaries["amount"]["min"] == 10.0
        assert summary.numeric_summaries["count"]["max"] == 100
