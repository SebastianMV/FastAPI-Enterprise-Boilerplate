# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Coverage tests for GenericImporter - targeting uncovered lines.

Patches select() to avoid SQLAlchemy ArgumentError with mock models.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.ports.data_exchange import (
    EntityConfig,
    EntityRegistry,
    FieldConfig,
    FieldType,
    ImportMode,
)
from app.domain.ports.import_export import ImportRequest
from app.infrastructure.data_exchange.generic_importer import (
    GenericImporter,
    get_importer,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_config(name="test_entity", fields=None, unique_fields=None, batch_size=100):
    if fields is None:
        fields = [
            FieldConfig(
                name="id",
                display_name="ID",
                field_type=FieldType.UUID,
                importable=False,
            ),
            FieldConfig(
                name="email",
                display_name="Email",
                field_type=FieldType.EMAIL,
                importable=True,
            ),
            FieldConfig(
                name="name",
                display_name="Name",
                field_type=FieldType.STRING,
                importable=True,
            ),
        ]
    mock_model = MagicMock()
    mock_model.__name__ = name
    return EntityConfig(
        name=name,
        display_name=name.title(),
        model=mock_model,
        fields=fields,
        permission_resource=name,
        unique_fields=unique_fields or [],
        batch_size=batch_size,
    )


def _csv_file(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode("utf-8"))


def _chainable_query():
    q = MagicMock()
    q.where.return_value = q
    return q


# ============================================================================
# Factory
# ============================================================================


class TestGetImporter:
    def test_returns_generic_importer(self):
        assert isinstance(get_importer(AsyncMock()), GenericImporter)


# ============================================================================
# get_template
# ============================================================================


class TestGetTemplate:
    def test_csv_template(self):
        config = _make_config()
        with patch.object(EntityRegistry, "get", return_value=config):
            importer = GenericImporter(AsyncMock())
            result = importer.get_template("test_entity", format="csv")
        assert isinstance(result, bytes)

    def test_excel_template_unavailable(self):
        config = _make_config()
        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_importer.is_excel_available",
                return_value=False,
            ),
        ):
            importer = GenericImporter(AsyncMock())
            with pytest.raises(ValueError, match="Excel support not available"):
                importer.get_template("test_entity", format="excel")

    def test_unsupported_format(self):
        config = _make_config()
        with patch.object(EntityRegistry, "get", return_value=config):
            importer = GenericImporter(AsyncMock())
            with pytest.raises(ValueError, match="Unsupported.*format"):
                importer.get_template("test_entity", format="xml")

    def test_entity_not_found(self):
        with patch.object(EntityRegistry, "get", return_value=None):
            importer = GenericImporter(AsyncMock())
            with pytest.raises(ValueError, match="not found"):
                importer.get_template("missing")


# ============================================================================
# validate (dry_run)
# ============================================================================


class TestValidate:
    @pytest.mark.asyncio
    async def test_validate_sets_dry_run(self):
        config = _make_config()
        session = AsyncMock()
        importer = GenericImporter(session)

        csv_data = "Email,Name\na@b.com,Alice\n"
        req = ImportRequest(
            entity="test_entity",
            file=_csv_file(csv_data),
            file_type="csv",
        )

        with patch.object(EntityRegistry, "get", return_value=config):
            result = await importer.validate(req)

        assert result.dry_run is True


# ============================================================================
# execute – INSERT mode
# ============================================================================


class TestExecuteInsert:
    @pytest.mark.asyncio
    async def test_insert_rows(self):
        config = _make_config()
        session = AsyncMock()
        importer = GenericImporter(session)

        csv_data = "Email,Name\na@b.com,Alice\nb@c.com,Bob\n"
        req = ImportRequest(
            entity="test_entity",
            file=_csv_file(csv_data),
            file_type="csv",
            mode=ImportMode.INSERT,
        )

        with patch.object(EntityRegistry, "get", return_value=config):
            result = await importer.execute(req)

        assert result.inserted == 2
        assert result.dry_run is False


# ============================================================================
# execute – UPSERT mode
# ============================================================================


class TestExecuteUpsert:
    @pytest.mark.asyncio
    async def test_upsert_inserts_new(self):
        config = _make_config(unique_fields=["email"])
        session = AsyncMock()
        # _find_existing returns None (not found) → insert
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        session.execute.return_value = exec_result
        importer = GenericImporter(session)

        csv_data = "Email,Name\na@b.com,Alice\n"
        req = ImportRequest(
            entity="test_entity",
            file=_csv_file(csv_data),
            file_type="csv",
            mode=ImportMode.UPSERT,
        )

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_importer.select",
                return_value=_chainable_query(),
            ),
        ):
            result = await importer.execute(req)

        assert result.inserted == 1

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self):
        config = _make_config(unique_fields=["email"])
        existing_obj = MagicMock()
        existing_obj.email = "a@b.com"
        existing_obj.name = "Old Name"

        session = AsyncMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = existing_obj
        session.execute.return_value = exec_result
        importer = GenericImporter(session)

        csv_data = "Email,Name\na@b.com,New Name\n"
        req = ImportRequest(
            entity="test_entity",
            file=_csv_file(csv_data),
            file_type="csv",
            mode=ImportMode.UPSERT,
        )

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_importer.select",
                return_value=_chainable_query(),
            ),
        ):
            result = await importer.execute(req)

        assert result.updated == 1


# ============================================================================
# execute – UPDATE_ONLY mode
# ============================================================================


class TestExecuteUpdateOnly:
    @pytest.mark.asyncio
    async def test_update_only_existing(self):
        config = _make_config(unique_fields=["email"])
        existing_obj = MagicMock()

        session = AsyncMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = existing_obj
        session.execute.return_value = exec_result
        importer = GenericImporter(session)

        csv_data = "Email,Name\na@b.com,Updated\n"
        req = ImportRequest(
            entity="test_entity",
            file=_csv_file(csv_data),
            file_type="csv",
            mode=ImportMode.UPDATE_ONLY,
        )

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_importer.select",
                return_value=_chainable_query(),
            ),
        ):
            result = await importer.execute(req)

        assert result.updated == 1

    @pytest.mark.asyncio
    async def test_update_only_not_found_skips(self):
        config = _make_config(unique_fields=["email"])

        session = AsyncMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        session.execute.return_value = exec_result
        importer = GenericImporter(session)

        csv_data = "Email,Name\na@b.com,Missing\n"
        req = ImportRequest(
            entity="test_entity",
            file=_csv_file(csv_data),
            file_type="csv",
            mode=ImportMode.UPDATE_ONLY,
        )

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_importer.select",
                return_value=_chainable_query(),
            ),
        ):
            result = await importer.execute(req)

        assert result.skipped == 1
        assert len(result.warnings) == 1


# ============================================================================
# execute – error paths
# ============================================================================


class TestExecuteErrors:
    @pytest.mark.asyncio
    async def test_unsupported_file_type(self):
        config = _make_config()
        importer = GenericImporter(AsyncMock())

        req = ImportRequest(
            entity="test_entity",
            file=_csv_file("data"),
            file_type="xml",
        )

        with patch.object(EntityRegistry, "get", return_value=config):
            result = await importer.execute(req)

        assert len(result.errors) == 1
        assert "Unsupported" in result.errors[0].error

    @pytest.mark.asyncio
    async def test_excel_unavailable(self):
        config = _make_config()
        importer = GenericImporter(AsyncMock())

        req = ImportRequest(
            entity="test_entity",
            file=_csv_file("data"),
            file_type="excel",
        )

        with (
            patch.object(EntityRegistry, "get", return_value=config),
            patch(
                "app.infrastructure.data_exchange.generic_importer.is_excel_available",
                return_value=False,
            ),
        ):
            result = await importer.execute(req)

        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        importer = GenericImporter(AsyncMock())
        req = ImportRequest(
            entity="missing",
            file=_csv_file("data"),
        )

        with patch.object(EntityRegistry, "get", return_value=None):
            result = await importer.execute(req)

        assert len(result.errors) == 1
        assert "not found" in result.errors[0].error

    @pytest.mark.asyncio
    async def test_flush_error(self):
        config = _make_config()
        session = AsyncMock()
        session.flush.side_effect = Exception("DB error")
        importer = GenericImporter(session)

        csv_data = "Email,Name\na@b.com,Alice\n"
        req = ImportRequest(
            entity="test_entity",
            file=_csv_file(csv_data),
            file_type="csv",
            mode=ImportMode.INSERT,
        )

        with patch.object(EntityRegistry, "get", return_value=config):
            result = await importer.execute(req)

        # Should still have inserted count but also a flush error
        assert result.inserted == 1
        assert any("Database error" in e.error for e in result.errors)

    @pytest.mark.asyncio
    async def test_with_tenant_id(self):
        config = _make_config()
        session = AsyncMock()
        importer = GenericImporter(session)

        csv_data = "Email,Name\na@b.com,Alice\n"
        tid = uuid4()
        req = ImportRequest(
            entity="test_entity",
            file=_csv_file(csv_data),
            file_type="csv",
            tenant_id=tid,
        )

        with patch.object(EntityRegistry, "get", return_value=config):
            result = await importer.execute(req)

        assert result.inserted == 1


# ============================================================================
# _find_existing
# ============================================================================


class TestFindExisting:
    @pytest.mark.asyncio
    async def test_no_unique_fields_returns_none(self):
        config = _make_config(unique_fields=[])
        importer = GenericImporter(AsyncMock())
        result = await importer._find_existing(config, {"email": "x"})
        assert result is None

    @pytest.mark.asyncio
    async def test_find_existing_match(self):
        config = _make_config(unique_fields=["email"])
        existing = MagicMock()

        session = AsyncMock()
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = existing
        session.execute.return_value = exec_result
        importer = GenericImporter(session)

        with patch(
            "app.infrastructure.data_exchange.generic_importer.select",
            return_value=_chainable_query(),
        ):
            result = await importer._find_existing(config, {"email": "a@b.com"})

        assert result is existing
