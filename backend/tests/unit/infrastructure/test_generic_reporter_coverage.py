# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Coverage tests for GenericReporter - targeting uncovered lines.

Patches select() to avoid SQLAlchemy ArgumentError with mock models.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.ports.data_exchange import (
    EntityConfig,
    EntityRegistry,
    FieldConfig,
    FieldType,
    ReportFormat,
)
from app.domain.ports.reports import (
    ReportFilter,
    ReportRequest,
    ReportSummary,
)
from app.infrastructure.data_exchange.generic_reporter import (
    GenericReporter,
    get_reporter,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_config(name="test_entity", fields=None, default_sort="-created_at"):
    if fields is None:
        fields = [
            FieldConfig(
                name="id", display_name="ID", field_type=FieldType.UUID, exportable=True
            ),
            FieldConfig(
                name="email",
                display_name="Email",
                field_type=FieldType.EMAIL,
                exportable=True,
            ),
            FieldConfig(
                name="name",
                display_name="Name",
                field_type=FieldType.STRING,
                exportable=True,
            ),
            FieldConfig(
                name="is_active",
                display_name="Active",
                field_type=FieldType.BOOLEAN,
                exportable=True,
            ),
            FieldConfig(
                name="created_at",
                display_name="Created At",
                field_type=FieldType.DATETIME,
                exportable=True,
            ),
            FieldConfig(
                name="amount",
                display_name="Amount",
                field_type=FieldType.FLOAT,
                exportable=True,
            ),
        ]
    # Use spec to control which attributes hasattr() finds on the model.
    # This prevents MagicMock from auto-creating tenant_id, which would
    # trigger the tenant-aware validation in _apply_tenant_filter().
    field_names = [f.name for f in fields]
    mock_model = MagicMock(spec=field_names + ["__name__"])
    mock_model.__name__ = name
    return EntityConfig(
        name=name,
        display_name=name.title(),
        model=mock_model,
        fields=fields,
        permission_resource=name,
        default_sort=default_sort,
    )


def _make_model_instance(**kwargs):
    obj = MagicMock()
    for k, v in kwargs.items():
        setattr(obj, k, v)
    obj.__class__ = type("MockModel", (), kwargs)  # pyright: ignore[reportAttributeAccessIssue]
    return obj


def _session_with_results(items, scalar_value=0):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalar.return_value = scalar_value
    result.all.return_value = []
    result.one_or_none.return_value = None
    session.execute.return_value = result
    return session


def _chainable_query():
    q = MagicMock()
    q.where.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.select_from.return_value = q
    q.group_by.return_value = q
    return q


# ============================================================================
# Factory
# ============================================================================


class TestGetReporter:
    def test_returns_generic_reporter(self):
        assert isinstance(get_reporter(AsyncMock()), GenericReporter)


# ============================================================================
# generate – CSV
# ============================================================================


class TestGenerateCSV:
    @pytest.mark.asyncio
    async def test_csv_report(self):
        item = _make_model_instance(
            id=uuid4(),
            email="a@b.com",
            name="Alice",
            is_active=True,
            created_at=datetime.now(UTC),
            amount=100.0,
        )
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[item]),
            patch.object(reporter, "get_summary", return_value=None),
        ):
            req = ReportRequest(
                entity="test_entity", format=ReportFormat.CSV, include_summary=False
            )
            result = await reporter.generate(req)

        assert result.content_type.startswith("text/csv")
        assert result.filename.endswith(".csv")


# ============================================================================
# generate – Excel
# ============================================================================


class TestGenerateExcel:
    @pytest.mark.asyncio
    async def test_excel_report(self):
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if not is_excel_available():
            pytest.skip("openpyxl not installed")

        item = _make_model_instance(
            id=uuid4(),
            email="a@b.com",
            name="Alice",
            is_active=True,
            created_at=datetime.now(UTC),
            amount=100.0,
        )
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[item]),
            patch.object(reporter, "get_summary", return_value=None),
        ):
            req = ReportRequest(
                entity="test_entity", format=ReportFormat.EXCEL, include_summary=False
            )
            result = await reporter.generate(req)

        assert "spreadsheetml" in result.content_type

    @pytest.mark.asyncio
    async def test_excel_with_summary(self):
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if not is_excel_available():
            pytest.skip("openpyxl not installed")

        item = _make_model_instance(
            id=uuid4(),
            email="a@b.com",
            name="Alice",
            is_active=True,
            created_at=datetime.now(UTC),
            amount=100.0,
        )
        summary = ReportSummary(
            total_records=1,
            grouped_counts={"is_active:True": 1},
        )
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[item]),
            patch.object(reporter, "get_summary", return_value=summary),
        ):
            req = ReportRequest(
                entity="test_entity", format=ReportFormat.EXCEL, include_summary=True
            )
            result = await reporter.generate(req)

        assert "spreadsheetml" in result.content_type

    @pytest.mark.asyncio
    async def test_excel_unavailable_raises(self):
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[]),
            patch.object(reporter, "get_summary", return_value=None),
            patch(
                "app.infrastructure.data_exchange.generic_reporter.is_excel_available",
                return_value=False,
            ),
        ):
            req = ReportRequest(
                entity="test_entity", format=ReportFormat.EXCEL, include_summary=False
            )
            with pytest.raises(ValueError, match="Excel support not available"):
                await reporter.generate(req)


# ============================================================================
# generate – HTML
# ============================================================================


class TestGenerateHTML:
    @pytest.mark.asyncio
    async def test_html_report(self):
        item = _make_model_instance(
            id=uuid4(),
            email="a@b.com",
            name="Alice",
            is_active=True,
            created_at=datetime.now(UTC),
            amount=100.0,
        )
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[item]),
            patch.object(reporter, "get_summary", return_value=None),
        ):
            req = ReportRequest(
                entity="test_entity", format=ReportFormat.HTML, include_summary=False
            )
            result = await reporter.generate(req)

        assert result.content_type.startswith("text/html")
        html = result.content.decode("utf-8")
        assert "a@b.com" in html

    @pytest.mark.asyncio
    async def test_html_with_summary(self):
        item = _make_model_instance(
            id=uuid4(),
            email="a@b.com",
            name="Alice",
            is_active=True,
            created_at=datetime.now(UTC),
            amount=100.0,
        )
        summary = ReportSummary(total_records=1)
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[item]),
            patch.object(reporter, "get_summary", return_value=summary),
        ):
            req = ReportRequest(
                entity="test_entity", format=ReportFormat.HTML, include_summary=True
            )
            result = await reporter.generate(req)

        html = result.content.decode("utf-8")
        assert "Resumen" in html

    @pytest.mark.asyncio
    async def test_html_with_company_name(self):
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[]),
            patch.object(reporter, "get_summary", return_value=None),
        ):
            req = ReportRequest(
                entity="test_entity",
                format=ReportFormat.HTML,
                include_summary=False,
                company_name="Acme Corp",
            )
            result = await reporter.generate(req)

        html = result.content.decode("utf-8")
        assert "Acme Corp" in html

    @pytest.mark.asyncio
    async def test_html_without_page_numbers(self):
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[]),
            patch.object(reporter, "get_summary", return_value=None),
        ):
            req = ReportRequest(
                entity="test_entity",
                format=ReportFormat.HTML,
                include_summary=False,
                show_page_numbers=False,
            )
            result = await reporter.generate(req)

        assert result.content_type.startswith("text/html")


# ============================================================================
# generate – PDF (fallback path)
# ============================================================================


class TestGeneratePDF:
    @pytest.mark.asyncio
    async def test_pdf_report_fallback(self):
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[]),
            patch.object(reporter, "get_summary", return_value=None),
        ):
            req = ReportRequest(
                entity="test_entity", format=ReportFormat.PDF, include_summary=False
            )
            result = await reporter.generate(req)

        # Either real PDF or HTML fallback
        assert result.content_type == "application/pdf"


# ============================================================================
# generate – unsupported
# ============================================================================


class TestGenerateErrors:
    @pytest.mark.asyncio
    async def test_unsupported_format(self):
        session = AsyncMock()
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(reporter, "_query_data", return_value=[]),
            patch.object(reporter, "get_summary", return_value=None),
        ):
            req = ReportRequest(entity="test_entity", format="xml")  # type: ignore
            with pytest.raises(ValueError, match="Unsupported.*format"):
                await reporter.generate(req)

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        reporter = GenericReporter(AsyncMock())
        with patch.object(EntityRegistry, "get", return_value=None):
            req = ReportRequest(entity="missing", format=ReportFormat.CSV)
            with pytest.raises(ValueError, match="not found"):
                await reporter.generate(req)


# ============================================================================
# get_preview – patch select()
# ============================================================================


class TestGetPreview:
    @pytest.mark.asyncio
    async def test_preview_returns_list(self):
        item = _make_model_instance(
            id=uuid4(),
            email="d@e.com",
            name="Dave",
            is_active=True,
            created_at=datetime.now(UTC),
            amount=50.0,
        )
        session = _session_with_results([item])
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_reporter.select",
                return_value=_chainable_query(),
            ),
        ):
            req = ReportRequest(entity="test_entity", format=ReportFormat.CSV)
            result = await reporter.get_preview(req, limit=5)

        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_preview_with_tenant(self):
        session = _session_with_results([])
        reporter = GenericReporter(session)
        config = _make_config()
        config.model.tenant_id = MagicMock()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_reporter.select",
                return_value=_chainable_query(),
            ),
        ):
            req = ReportRequest(
                entity="test_entity", format=ReportFormat.CSV, tenant_id=uuid4()
            )
            result = await reporter.get_preview(req)

        assert isinstance(result, list)


# ============================================================================
# get_summary – patch select() and func
# ============================================================================


class TestGetSummary:
    @pytest.mark.asyncio
    async def test_summary_total_records(self):
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = 42
        result_mock.all.return_value = []
        result_mock.one_or_none.return_value = None
        session.execute.return_value = result_mock
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_reporter.select",
                return_value=_chainable_query(),
            ),
            patch(
                "app.infrastructure.data_exchange.generic_reporter.func"
            ) as mock_func,
        ):
            mock_func.count.return_value = MagicMock()
            mock_func.min.return_value = MagicMock()
            mock_func.max.return_value = MagicMock()
            mock_func.avg.return_value = MagicMock()
            mock_func.sum.return_value = MagicMock()

            req = ReportRequest(entity="test_entity", format=ReportFormat.CSV)
            summary = await reporter.get_summary(req)

        assert summary.total_records == 42

    @pytest.mark.asyncio
    async def test_summary_with_group_by(self):
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = 10
        result_mock.all.return_value = [("active", 5), ("inactive", 5)]
        result_mock.one_or_none.return_value = None
        session.execute.return_value = result_mock
        reporter = GenericReporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_reporter.select",
                return_value=_chainable_query(),
            ),
            patch(
                "app.infrastructure.data_exchange.generic_reporter.func"
            ) as mock_func,
        ):
            mock_func.count.return_value = MagicMock()
            mock_func.min.return_value = MagicMock()
            mock_func.max.return_value = MagicMock()
            mock_func.avg.return_value = MagicMock()
            mock_func.sum.return_value = MagicMock()

            req = ReportRequest(
                entity="test_entity",
                format=ReportFormat.CSV,
                group_by=["is_active"],
            )
            summary = await reporter.get_summary(req)

        assert summary.total_records == 10
        assert len(summary.grouped_counts) > 0


# ============================================================================
# _apply_filters (takes ReportRequest with list of ReportFilter)
# ============================================================================


class TestApplyFilters:
    def test_eq_ne_operators(self):
        reporter = GenericReporter(AsyncMock())
        config = _make_config()

        for op in ["eq", "ne", "in", "contains"]:
            q = _chainable_query()
            req = ReportRequest(
                entity="test_entity",
                format=ReportFormat.CSV,
                filters=[ReportFilter(field="email", operator=op, value="test")],
            )
            result = reporter._apply_filters(q, config, req)
            assert result is q

    def test_comparison_operators(self):
        """Test gt, gte, lt, lte with a column mock that supports comparison."""
        reporter = GenericReporter(AsyncMock())
        config = _make_config()

        # Create a column mock that supports comparison operators
        col_mock = MagicMock()
        col_mock.__gt__ = MagicMock(return_value=MagicMock())
        col_mock.__ge__ = MagicMock(return_value=MagicMock())
        col_mock.__lt__ = MagicMock(return_value=MagicMock())
        col_mock.__le__ = MagicMock(return_value=MagicMock())
        config.model.amount = col_mock

        for op in ["gt", "gte", "lt", "lte"]:
            q = _chainable_query()
            req = ReportRequest(
                entity="test_entity",
                format=ReportFormat.CSV,
                filters=[ReportFilter(field="amount", operator=op, value=10)],
            )
            result = reporter._apply_filters(q, config, req)
            assert result is q

    def test_nonexistent_field_ignored(self):
        reporter = GenericReporter(AsyncMock())
        config = _make_config()
        config.model = MagicMock(spec=[])  # has no attributes
        q = MagicMock()

        req = ReportRequest(
            entity="test_entity",
            format=ReportFormat.CSV,
            filters=[ReportFilter(field="nonexistent", operator="eq", value="x")],
        )
        reporter._apply_filters(q, config, req)
        q.where.assert_not_called()


# ============================================================================
# _query_data – with date range, sorting
# ============================================================================


class TestQueryData:
    @pytest.mark.asyncio
    async def test_query_with_date_range(self):
        session = _session_with_results([])
        reporter = GenericReporter(session)
        config = _make_config()

        # Make date column support >= and <= comparisons
        date_col = MagicMock()
        date_col.__ge__ = MagicMock(return_value=MagicMock())
        date_col.__le__ = MagicMock(return_value=MagicMock())
        config.model.created_at = date_col

        req = ReportRequest(
            entity="test_entity",
            format=ReportFormat.CSV,
            date_range_field="created_at",
            date_from=datetime(2026, 1, 1),
            date_to=datetime(2026, 12, 31),
        )

        with patch(
            "app.infrastructure.data_exchange.generic_reporter.select",
            return_value=_chainable_query(),
        ):
            result = await reporter._query_data(config, req)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_query_with_sort(self):
        session = _session_with_results([])
        reporter = GenericReporter(session)
        config = _make_config()
        q = _chainable_query()

        req = ReportRequest(
            entity="test_entity", format=ReportFormat.CSV, sort_by="email"
        )
        with patch(
            "app.infrastructure.data_exchange.generic_reporter.select", return_value=q
        ):
            result = await reporter._query_data(config, req)
        assert isinstance(result, list)
        q.order_by.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_with_descending_sort(self):
        session = _session_with_results([])
        reporter = GenericReporter(session)
        config = _make_config()
        q = _chainable_query()

        req = ReportRequest(
            entity="test_entity", format=ReportFormat.CSV, sort_by="-email"
        )
        with patch(
            "app.infrastructure.data_exchange.generic_reporter.select", return_value=q
        ):
            result = await reporter._query_data(config, req)
        assert isinstance(result, list)
        q.order_by.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_with_tenant(self):
        session = _session_with_results([])
        reporter = GenericReporter(session)
        config = _make_config()
        config.model.tenant_id = MagicMock()
        q = _chainable_query()

        req = ReportRequest(
            entity="test_entity", format=ReportFormat.CSV, tenant_id=uuid4()
        )
        with patch(
            "app.infrastructure.data_exchange.generic_reporter.select", return_value=q
        ):
            result = await reporter._query_data(config, req)
        assert isinstance(result, list)
        q.where.assert_called()


# ============================================================================
# _format_cell_value / _format_html_value
# ============================================================================


class TestFormatHelpers:
    def test_format_cell_none(self):
        r = GenericReporter(AsyncMock())
        assert r._format_cell_value(None) == ""

    def test_format_cell_uuid(self):
        r = GenericReporter(AsyncMock())
        uid = uuid4()
        assert r._format_cell_value(uid) == str(uid)

    def test_format_cell_bool_true(self):
        r = GenericReporter(AsyncMock())
        assert r._format_cell_value(True) == "Sí"

    def test_format_cell_bool_false(self):
        r = GenericReporter(AsyncMock())
        assert r._format_cell_value(False) == "No"

    def test_format_cell_string(self):
        r = GenericReporter(AsyncMock())
        assert r._format_cell_value("hello") == "hello"

    def test_format_cell_int(self):
        r = GenericReporter(AsyncMock())
        assert r._format_cell_value(42) == 42

    def test_format_html_none(self):
        r = GenericReporter(AsyncMock())
        assert r._format_html_value(None) == "-"

    def test_format_html_datetime(self):
        r = GenericReporter(AsyncMock())
        dt = datetime(2026, 1, 15, 10, 30)
        assert "2026-01-15" in r._format_html_value(dt)

    def test_format_html_bool_true(self):
        r = GenericReporter(AsyncMock())
        assert r._format_html_value(True) == "✓"

    def test_format_html_bool_false(self):
        r = GenericReporter(AsyncMock())
        assert r._format_html_value(False) == "✗"

    def test_format_html_uuid(self):
        r = GenericReporter(AsyncMock())
        uid = uuid4()
        result = r._format_html_value(uid)
        assert "..." in result

    def test_format_html_string(self):
        r = GenericReporter(AsyncMock())
        assert r._format_html_value("hello") == "hello"

    def test_format_html_int(self):
        r = GenericReporter(AsyncMock())
        assert r._format_html_value(42) == "42"


# ============================================================================
# _html_to_pdf (fallback)
# ============================================================================


class TestHtmlToPdf:
    def test_fallback_without_weasyprint(self):
        reporter = GenericReporter(AsyncMock())
        html = b"<html><body>Test</body></html>"

        original_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )

        def mock_import(name, *args, **kwargs):
            if name == "weasyprint":
                raise ImportError("no weasyprint")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = reporter._html_to_pdf(html)

        assert b"weasyprint" in result
