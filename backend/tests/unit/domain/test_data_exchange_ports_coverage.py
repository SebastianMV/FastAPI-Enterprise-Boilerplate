# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Coverage tests for FieldConfig._validate_type and FieldConfig.transform
in app.domain.ports.data_exchange – targeting uncovered type-specific branches.
"""

from datetime import date, datetime

import pytest

from app.domain.ports.data_exchange import (
    EntityConfig,
    EntityRegistry,
    FieldConfig,
    FieldType,
)

# ============================================================================
# FieldConfig._validate_type – all type branches
# ============================================================================


class TestValidateTypeFloat:
    """Test FLOAT validation branch."""

    def test_valid_float_number(self):
        field = FieldConfig(
            name="price", display_name="Price", field_type=FieldType.FLOAT
        )
        is_valid, error = field.validate(3.14)
        assert is_valid

    def test_valid_float_string(self):
        field = FieldConfig(
            name="price", display_name="Price", field_type=FieldType.FLOAT
        )
        is_valid, error = field.validate("3.14")
        assert is_valid

    def test_invalid_float(self):
        field = FieldConfig(
            name="price", display_name="Price", field_type=FieldType.FLOAT
        )
        is_valid, error = field.validate("not-a-number")
        assert not is_valid


class TestValidateTypeDate:
    """Test DATE validation branch."""

    def test_valid_date_object(self):
        field = FieldConfig(name="dob", display_name="DOB", field_type=FieldType.DATE)
        is_valid, error = field.validate(date(2026, 1, 15))
        assert is_valid

    def test_valid_date_iso_string(self):
        field = FieldConfig(name="dob", display_name="DOB", field_type=FieldType.DATE)
        is_valid, error = field.validate("2026-01-15")
        assert is_valid

    def test_valid_date_european_format(self):
        field = FieldConfig(name="dob", display_name="DOB", field_type=FieldType.DATE)
        is_valid, error = field.validate("15/01/2026")
        assert is_valid

    def test_valid_date_us_format(self):
        field = FieldConfig(name="dob", display_name="DOB", field_type=FieldType.DATE)
        is_valid, error = field.validate("01/15/2026")
        assert is_valid

    def test_invalid_date(self):
        field = FieldConfig(name="dob", display_name="DOB", field_type=FieldType.DATE)
        is_valid, error = field.validate("not-a-date")
        assert not is_valid


class TestValidateTypeDatetime:
    """Test DATETIME validation branch."""

    def test_valid_datetime_object(self):
        field = FieldConfig(
            name="ts", display_name="Timestamp", field_type=FieldType.DATETIME
        )
        is_valid, error = field.validate(datetime(2026, 1, 15, 10, 30))
        assert is_valid

    def test_valid_datetime_iso_string(self):
        field = FieldConfig(
            name="ts", display_name="Timestamp", field_type=FieldType.DATETIME
        )
        is_valid, error = field.validate("2026-01-15 10:30:00")
        assert is_valid

    def test_valid_datetime_t_format(self):
        field = FieldConfig(
            name="ts", display_name="Timestamp", field_type=FieldType.DATETIME
        )
        is_valid, error = field.validate("2026-01-15T10:30:00")
        assert is_valid

    def test_valid_datetime_short_format(self):
        field = FieldConfig(
            name="ts", display_name="Timestamp", field_type=FieldType.DATETIME
        )
        is_valid, error = field.validate("2026-01-15 10:30")
        assert is_valid

    def test_invalid_datetime(self):
        field = FieldConfig(
            name="ts", display_name="Timestamp", field_type=FieldType.DATETIME
        )
        is_valid, error = field.validate("not-a-datetime")
        assert not is_valid


class TestValidateTypeJSON:
    """Test JSON validation (if applicable)."""

    def test_json_field_accepts_string(self):
        field = FieldConfig(
            name="meta", display_name="Metadata", field_type=FieldType.JSON
        )
        is_valid, error = field.validate('{"key": "value"}')
        assert is_valid


# ============================================================================
# FieldConfig.transform – all type branches
# ============================================================================


class TestTransformFloat:
    def test_transform_float_from_string(self):
        field = FieldConfig(
            name="price", display_name="Price", field_type=FieldType.FLOAT
        )
        assert field.transform("3.14") == pytest.approx(3.14)

    def test_transform_float_from_int(self):
        field = FieldConfig(
            name="price", display_name="Price", field_type=FieldType.FLOAT
        )
        assert field.transform(42) == 42.0


class TestTransformDate:
    def test_transform_date_object(self):
        field = FieldConfig(name="dob", display_name="DOB", field_type=FieldType.DATE)
        d = date(2026, 1, 15)
        assert field.transform(d) == d

    def test_transform_date_iso_string(self):
        field = FieldConfig(name="dob", display_name="DOB", field_type=FieldType.DATE)
        result = field.transform("2026-01-15")
        assert isinstance(result, date)
        assert result == date(2026, 1, 15)

    def test_transform_date_european_format(self):
        field = FieldConfig(name="dob", display_name="DOB", field_type=FieldType.DATE)
        result = field.transform("15/01/2026")
        assert isinstance(result, date)

    def test_transform_date_unparseable_returns_original(self):
        field = FieldConfig(name="dob", display_name="DOB", field_type=FieldType.DATE)
        result = field.transform("weird-date")
        assert result == "weird-date"


class TestTransformDatetime:
    def test_transform_datetime_object(self):
        field = FieldConfig(
            name="ts", display_name="Timestamp", field_type=FieldType.DATETIME
        )
        dt = datetime(2026, 1, 15, 10, 30)
        assert field.transform(dt) == dt

    def test_transform_datetime_iso_string(self):
        field = FieldConfig(
            name="ts", display_name="Timestamp", field_type=FieldType.DATETIME
        )
        result = field.transform("2026-01-15 10:30:00")
        assert isinstance(result, datetime)

    def test_transform_datetime_t_format(self):
        field = FieldConfig(
            name="ts", display_name="Timestamp", field_type=FieldType.DATETIME
        )
        result = field.transform("2026-01-15T10:30:00")
        assert isinstance(result, datetime)

    def test_transform_datetime_unparseable_returns_original(self):
        field = FieldConfig(
            name="ts", display_name="Timestamp", field_type=FieldType.DATETIME
        )
        result = field.transform("weird-datetime")
        assert result == "weird-datetime"


class TestTransformOther:
    def test_transform_string_passthrough(self):
        field = FieldConfig(
            name="note", display_name="Note", field_type=FieldType.STRING
        )
        assert field.transform("hello") == "hello"

    def test_transform_none_returns_default(self):
        field = FieldConfig(
            name="status",
            display_name="Status",
            field_type=FieldType.STRING,
            default="active",
        )
        assert field.transform(None) == "active"

    def test_transform_empty_returns_default(self):
        field = FieldConfig(
            name="status",
            display_name="Status",
            field_type=FieldType.STRING,
            default="pending",
        )
        assert field.transform("") == "pending"


# ============================================================================
# EntityConfig additional methods
# ============================================================================


class TestEntityConfigMethods:
    def test_get_required_fields(self):
        config = EntityConfig(
            name="test",
            display_name="Test",
            model=object,
            fields=[
                FieldConfig(name="a", display_name="A", required=True, importable=True),
                FieldConfig(
                    name="b", display_name="B", required=False, importable=True
                ),
                FieldConfig(
                    name="c", display_name="C", required=True, importable=False
                ),
            ],
            permission_resource="test",
        )
        required = config.get_required_fields()
        assert len(required) == 1
        assert required[0].name == "a"

    def test_get_field_existing(self):
        config = EntityConfig(
            name="test",
            display_name="Test",
            model=object,
            fields=[
                FieldConfig(name="email", display_name="Email"),
            ],
            permission_resource="test",
        )
        field = config.get_field("email")
        assert field is not None
        assert field.name == "email"

    def test_get_field_not_found(self):
        config = EntityConfig(
            name="test",
            display_name="Test",
            model=object,
            fields=[],
            permission_resource="test",
        )
        assert config.get_field("missing") is None

    def test_report_title_default(self):
        config = EntityConfig(
            name="users",
            display_name="Usuarios",
            model=object,
            fields=[],
            permission_resource="users",
        )
        assert "Usuarios" in config.report_title


# ============================================================================
# EntityRegistry – additional methods
# ============================================================================


class TestEntityRegistryExtended:
    def setup_method(self):
        EntityRegistry.clear()

    def teardown_method(self):
        EntityRegistry.clear()

    def test_list_exportable(self):
        EntityRegistry.register(
            EntityConfig(
                name="e1",
                display_name="E1",
                model=object,
                fields=[FieldConfig(name="a", display_name="A", exportable=True)],
                permission_resource="e1",
            )
        )
        EntityRegistry.register(
            EntityConfig(
                name="e2",
                display_name="E2",
                model=object,
                fields=[FieldConfig(name="a", display_name="A", exportable=False)],
                permission_resource="e2",
            )
        )
        result = EntityRegistry.list_exportable()
        assert len(result) == 1
        assert result[0].name == "e1"

    def test_list_importable(self):
        EntityRegistry.register(
            EntityConfig(
                name="i1",
                display_name="I1",
                model=object,
                fields=[FieldConfig(name="a", display_name="A", importable=True)],
                permission_resource="i1",
            )
        )
        EntityRegistry.register(
            EntityConfig(
                name="i2",
                display_name="I2",
                model=object,
                fields=[FieldConfig(name="a", display_name="A", importable=False)],
                permission_resource="i2",
            )
        )
        result = EntityRegistry.list_importable()
        assert len(result) == 1
        assert result[0].name == "i1"

    def test_list_all(self):
        EntityRegistry.register(
            EntityConfig(
                name="x1",
                display_name="X1",
                model=object,
                fields=[],
                permission_resource="x1",
            )
        )
        EntityRegistry.register(
            EntityConfig(
                name="x2",
                display_name="X2",
                model=object,
                fields=[],
                permission_resource="x2",
            )
        )
        result = EntityRegistry.list_all()
        assert len(result) == 2

    def test_unregister(self):
        EntityRegistry.register(
            EntityConfig(
                name="tmp",
                display_name="Tmp",
                model=object,
                fields=[],
                permission_resource="tmp",
            )
        )
        assert EntityRegistry.get("tmp") is not None
        EntityRegistry.unregister("tmp")
        assert EntityRegistry.get("tmp") is None

    def test_clear(self):
        EntityRegistry.register(
            EntityConfig(
                name="c1",
                display_name="C1",
                model=object,
                fields=[],
                permission_resource="c1",
            )
        )
        EntityRegistry.clear()
        assert EntityRegistry.get("c1") is None
        assert len(EntityRegistry.list_all()) == 0
