# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Coverage tests for GenericExporter - targeting uncovered lines.

Patches select() to avoid SQLAlchemy ArgumentError with mock models.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.ports.data_exchange import (
    EntityConfig,
    EntityRegistry,
    ExportFormat,
    FieldConfig,
    FieldType,
)
from app.domain.ports.import_export import ExportRequest
from app.infrastructure.data_exchange.generic_exporter import (
    GenericExporter,
    get_exporter,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_config(
    name: str = "test_entity",
    fields: list | None = None,
    default_sort: str | None = "-created_at",
):
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
                name="secret",
                display_name="Secret",
                field_type=FieldType.STRING,
                exportable=False,
            ),
        ]
    # Use spec to control which attributes hasattr() finds on the model.
    # This prevents MagicMock from auto-creating tenant_id, which would
    # trigger the tenant-aware validation in _apply_tenant_filter().
    field_names = [f.name for f in fields]
    mock_model = MagicMock(spec=field_names + ["__name__"])
    mock_model.__name__ = name
    kwargs: dict = dict(
        name=name,
        display_name=name.title(),
        model=mock_model,
        fields=fields,
        permission_resource=name,
    )
    if default_sort is not None:
        kwargs["default_sort"] = default_sort
    else:
        kwargs["default_sort"] = ""
    return EntityConfig(**kwargs)


def _make_model_instance(**kwargs):
    obj = MagicMock()
    for k, v in kwargs.items():
        setattr(obj, k, v)
    obj.__class__ = type("MockModel", (), kwargs)  # type: ignore[assignment]
    return obj


def _session_with_results(items):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalar.return_value = len(items)
    session.execute.return_value = result
    return session


def _chainable_query():
    q = MagicMock()
    q.where.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.select_from.return_value = q
    return q


# ============================================================================
# Factory
# ============================================================================


class TestGetExporter:
    def test_returns_generic_exporter(self):
        assert isinstance(get_exporter(AsyncMock()), GenericExporter)


# ============================================================================
# export() – CSV
# ============================================================================


class TestExportCSV:
    @pytest.mark.asyncio
    async def test_export_csv_produces_bytes(self):
        item = _make_model_instance(
            id=uuid4(),
            email="a@b.com",
            name="Alice",
            is_active=True,
            created_at=datetime.now(UTC),
            secret="x",
        )
        exporter = GenericExporter(AsyncMock())
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(exporter, "_query_data", return_value=[item]),
        ):
            result = await exporter.export(
                ExportRequest(entity="test_entity", format=ExportFormat.CSV)
            )

        assert result.content_type.startswith("text/csv")
        assert result.row_count == 1
        assert result.filename.endswith(".csv")

    @pytest.mark.asyncio
    async def test_export_csv_custom_filename(self):
        exporter = GenericExporter(AsyncMock())
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(exporter, "_query_data", return_value=[]),
        ):
            result = await exporter.export(
                ExportRequest(
                    entity="test_entity", format=ExportFormat.CSV, filename="custom.csv"
                )
            )

        assert result.filename == "custom.csv"


# ============================================================================
# export() – JSON
# ============================================================================


class TestExportJSON:
    @pytest.mark.asyncio
    async def test_export_json_produces_valid_json(self):
        item = _make_model_instance(
            id=uuid4(),
            email="b@c.com",
            name="Bob",
            is_active=False,
            created_at=datetime.now(UTC),
            secret="y",
        )
        exporter = GenericExporter(AsyncMock())
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(exporter, "_query_data", return_value=[item]),
        ):
            result = await exporter.export(
                ExportRequest(entity="test_entity", format=ExportFormat.JSON)
            )

        assert result.content_type.startswith("application/json")
        data = json.loads(result.content.decode("utf-8"))
        assert isinstance(data, list)
        assert len(data) == 1

    def test_json_serializer_datetime(self):
        exporter = GenericExporter(AsyncMock())
        dt = datetime(2026, 1, 15, 10, 30, 0)
        assert exporter._json_serializer(dt) == dt.isoformat()

    def test_json_serializer_uuid(self):
        exporter = GenericExporter(AsyncMock())
        uid = uuid4()
        assert exporter._json_serializer(uid) == str(uid)

    def test_json_serializer_object(self):
        exporter = GenericExporter(AsyncMock())

        class Obj:
            x = 1

        result = exporter._json_serializer(Obj())
        assert isinstance(result, dict)

    def test_json_serializer_unsupported_raises(self):
        exporter = GenericExporter(AsyncMock())
        with pytest.raises(TypeError):
            exporter._json_serializer(set())


# ============================================================================
# export() – Excel
# ============================================================================


class TestExportExcel:
    @pytest.mark.asyncio
    async def test_export_excel_produces_bytes(self):
        from app.infrastructure.data_exchange.excel_handler import is_excel_available

        if not is_excel_available():
            pytest.skip("openpyxl not installed")

        item = _make_model_instance(
            id=uuid4(),
            email="c@d.com",
            name="Carol",
            is_active=True,
            created_at=datetime.now(UTC),
            secret="z",
        )
        exporter = GenericExporter(AsyncMock())
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(exporter, "_query_data", return_value=[item]),
        ):
            result = await exporter.export(
                ExportRequest(entity="test_entity", format=ExportFormat.EXCEL)
            )

        assert "spreadsheetml" in result.content_type

    @pytest.mark.asyncio
    async def test_export_excel_unavailable_raises(self):
        exporter = GenericExporter(AsyncMock())
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(exporter, "_query_data", return_value=[]),
            patch(
                "app.infrastructure.data_exchange.generic_exporter.is_excel_available",
                return_value=False,
            ),
            pytest.raises(ValueError, match="Excel support not available"),
        ):
            await exporter.export(
                ExportRequest(entity="test_entity", format=ExportFormat.EXCEL)
            )


# ============================================================================
# export() – unsupported / entity not found
# ============================================================================


class TestExportEdgeCases:
    @pytest.mark.asyncio
    async def test_unsupported_format_raises(self):
        exporter = GenericExporter(AsyncMock())
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch.object(exporter, "_query_data", return_value=[]),
        ):
            with pytest.raises(ValueError, match="Unsupported format"):
                await exporter.export(
                    ExportRequest(entity="test_entity", format="xml")  # type: ignore
                )

    @pytest.mark.asyncio
    async def test_entity_not_found_raises(self):
        exporter = GenericExporter(AsyncMock())
        with patch.object(EntityRegistry, "get", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await exporter.export(
                    ExportRequest(entity="missing", format=ExportFormat.CSV)
                )


# ============================================================================
# get_preview – patch select()
# ============================================================================


class TestGetPreview:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        item = _make_model_instance(
            id=uuid4(),
            email="d@e.com",
            name="Dave",
            is_active=True,
            created_at=datetime.now(UTC),
            secret="w",
        )
        session = _session_with_results([item])
        exporter = GenericExporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_exporter.select",
                return_value=_chainable_query(),
            ),
        ):
            result = await exporter.get_preview("test_entity", limit=5)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_with_tenant(self):
        session = _session_with_results([])
        exporter = GenericExporter(session)
        config = _make_config()
        config.model.tenant_id = MagicMock()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_exporter.select",
                return_value=_chainable_query(),
            ),
        ):
            result = await exporter.get_preview("test_entity", tenant_id=uuid4())
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_with_filters(self):
        session = _session_with_results([])
        exporter = GenericExporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_exporter.select",
                return_value=_chainable_query(),
            ),
        ):
            result = await exporter.get_preview(
                "test_entity", filters={"email": "a@b.com"}
            )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        exporter = GenericExporter(AsyncMock())
        with patch.object(EntityRegistry, "get", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await exporter.get_preview("missing")


# ============================================================================
# get_count – patch select() and func
# ============================================================================


class TestGetCount:
    @pytest.mark.asyncio
    async def test_returns_int(self):
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = 42
        session.execute.return_value = result_mock
        exporter = GenericExporter(session)
        config = _make_config()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_exporter.select",
                return_value=_chainable_query(),
            ),
        ):
            count = await exporter.get_count("test_entity")
        assert count == 42

    @pytest.mark.asyncio
    async def test_with_tenant(self):
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = 10
        session.execute.return_value = result_mock
        exporter = GenericExporter(session)
        config = _make_config()
        config.model.tenant_id = MagicMock()

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_exporter.select",
                return_value=_chainable_query(),
            ),
        ):
            count = await exporter.get_count("test_entity", tenant_id=uuid4())
        assert count == 10

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        exporter = GenericExporter(AsyncMock())
        with patch.object(EntityRegistry, "get", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await exporter.get_count("missing")


# ============================================================================
# _apply_filters
# ============================================================================


class TestApplyFilters:
    def test_simple_equality(self):
        exporter = GenericExporter(AsyncMock())
        config = _make_config()
        q = _chainable_query()
        result = exporter._apply_filters(q, config, {"email": "a@b.com"})
        assert result is q

    def test_eq_ne_in_contains_operators(self):
        exporter = GenericExporter(AsyncMock())
        config = _make_config()
        for op in ["eq", "ne", "in", "contains"]:
            q = _chainable_query()
            result = exporter._apply_filters(
                q, config, {"email": {"operator": op, "value": "test"}}
            )
            assert result is q

    def test_comparison_operators(self):
        """Test gt, gte, lt, lte with a column mock that supports comparison."""
        exporter = GenericExporter(AsyncMock())
        config = _make_config()
        col_mock = MagicMock()
        col_mock.__gt__ = MagicMock(return_value=MagicMock())
        col_mock.__ge__ = MagicMock(return_value=MagicMock())
        col_mock.__lt__ = MagicMock(return_value=MagicMock())
        col_mock.__le__ = MagicMock(return_value=MagicMock())
        config.model.amount = col_mock

        for op in ["gt", "gte", "lt", "lte"]:
            q = _chainable_query()
            result = exporter._apply_filters(
                q, config, {"amount": {"operator": op, "value": 10}}
            )
            assert result is q

    def test_nonexistent_field_ignored(self):
        exporter = GenericExporter(AsyncMock())
        config = _make_config()
        config.model = MagicMock(spec=[])
        q = MagicMock()
        exporter._apply_filters(q, config, {"nonexistent": "val"})
        q.where.assert_not_called()


# ============================================================================
# _model_to_dict
# ============================================================================


class TestModelToDict:
    def test_only_exportable_fields(self):
        exporter = GenericExporter(AsyncMock())
        config = _make_config()
        item = _make_model_instance(
            id=uuid4(),
            email="e@f.com",
            name="Eve",
            is_active=True,
            created_at=datetime.now(UTC),
            secret="nope",
        )
        result = exporter._model_to_dict(item, config)
        assert "email" in result
        assert "secret" not in result

    def test_missing_attribute_skipped(self):
        exporter = GenericExporter(AsyncMock())
        fields = [
            FieldConfig(name="email", display_name="Email", exportable=True),
            FieldConfig(name="phone", display_name="Phone", exportable=True),
        ]
        config = _make_config(fields=fields)
        item = MagicMock(spec=["email"])
        item.email = "f@g.com"
        result = exporter._model_to_dict(item, config)
        assert result.get("email") == "f@g.com"


# ============================================================================
# _query_data – sorting and tenant
# ============================================================================


class TestQueryData:
    @pytest.mark.asyncio
    async def test_descending_sort(self):
        session = _session_with_results([])
        exporter = GenericExporter(session)
        config = _make_config(default_sort="-created_at")
        q = _chainable_query()

        req = ExportRequest(entity="test_entity", format=ExportFormat.CSV)
        with patch(
            "app.infrastructure.data_exchange.generic_exporter.select", return_value=q
        ):
            result = await exporter._query_data(config, req)
        assert isinstance(result, list)
        q.order_by.assert_called_once()

    @pytest.mark.asyncio
    async def test_ascending_sort(self):
        session = _session_with_results([])
        exporter = GenericExporter(session)
        config = _make_config(default_sort="email")
        q = _chainable_query()

        req = ExportRequest(entity="test_entity", format=ExportFormat.CSV)
        with patch(
            "app.infrastructure.data_exchange.generic_exporter.select", return_value=q
        ):
            result = await exporter._query_data(config, req)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_with_tenant(self):
        session = _session_with_results([])
        exporter = GenericExporter(session)
        config = _make_config()
        config.model.tenant_id = MagicMock()
        q = _chainable_query()

        req = ExportRequest(
            entity="test_entity", format=ExportFormat.CSV, tenant_id=uuid4()
        )
        with patch(
            "app.infrastructure.data_exchange.generic_exporter.select", return_value=q
        ):
            result = await exporter._query_data(config, req)
        assert isinstance(result, list)
        q.where.assert_called()

    @pytest.mark.asyncio
    async def test_with_filters(self):
        session = _session_with_results([])
        exporter = GenericExporter(session)
        config = _make_config()
        q = _chainable_query()

        req = ExportRequest(
            entity="test_entity",
            format=ExportFormat.CSV,
            filters={"email": "test@example.com"},
        )
        with patch(
            "app.infrastructure.data_exchange.generic_exporter.select", return_value=q
        ):
            result = await exporter._query_data(config, req)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_no_sort(self):
        session = _session_with_results([])
        exporter = GenericExporter(session)
        config = _make_config(default_sort=None)
        q = _chainable_query()

        req = ExportRequest(entity="test_entity", format=ExportFormat.CSV)
        with patch(
            "app.infrastructure.data_exchange.generic_exporter.select", return_value=q
        ):
            result = await exporter._query_data(config, req)
        assert isinstance(result, list)
        q.order_by.assert_not_called()
