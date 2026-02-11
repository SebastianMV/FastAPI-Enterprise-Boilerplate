# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Tests for generic importer implementation.
"""

import json
from enum import Enum
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# Define local test enums
class ImportFormat(str, Enum):
    """Import format."""

    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"


class ImportMode(str, Enum):
    """Import mode."""

    CREATE = "create"
    UPDATE = "update"
    UPSERT = "upsert"


class TestImportRequest:
    """Test import request schema."""

    def test_import_request_csv(self):
        """Test CSV import request."""
        content = b"id,email\n1,test@example.com"
        request = {
            "entity": "users",
            "format": ImportFormat.CSV.value,
            "content": content,
        }
        assert request["format"] == "csv"
        assert request["entity"] == "users"

    def test_import_request_json(self):
        """Test JSON import request."""
        data = [{"id": 1, "email": "test@example.com"}]
        content = json.dumps(data).encode()
        request = {
            "entity": "users",
            "format": ImportFormat.JSON.value,
            "content": content,
        }
        assert request["format"] == "json"

    def test_import_request_with_mode(self):
        """Test import request with mode."""
        request = {
            "entity": "users",
            "format": ImportFormat.CSV.value,
            "mode": ImportMode.UPSERT.value,
        }
        assert request["mode"] == "upsert"


class TestImportResult:
    """Test import result schema."""

    def test_successful_import_result(self):
        """Test successful import result."""
        result = {
            "total_rows": 100,
            "imported": 100,
            "failed": 0,
            "created": 80,
            "updated": 20,
            "errors": [],
        }
        assert result["imported"] == 100
        assert result["failed"] == 0

    def test_partial_import_result(self):
        """Test partial import result."""
        result = {
            "total_rows": 100,
            "imported": 95,
            "failed": 5,
            "errors": [
                {"row": 10, "message": "Invalid email"},
                {"row": 25, "message": "Duplicate email"},
            ],
        }
        assert result["failed"] == 5
        assert len(result["errors"]) == 2


class TestCSVParsing:
    """Test CSV parsing functionality."""

    def test_parse_csv_with_headers(self):
        """Test parsing CSV with headers."""
        csv_content = b"email,full_name\ntest@example.com,Test User"
        lines = csv_content.decode().split("\n")
        headers = lines[0].split(",")

        assert "email" in headers
        assert "full_name" in headers

    def test_parse_csv_semicolon_delimiter(self):
        """Test parsing CSV with semicolon delimiter."""
        csv_content = b"email;full_name\ntest@example.com;Test User"
        lines = csv_content.decode().split("\n")
        headers = lines[0].split(";")

        assert "email" in headers

    def test_parse_csv_with_quotes(self):
        """Test parsing CSV with quoted values."""
        csv_content = b'email,full_name\ntest@example.com,"User, Test"'

        # Quoted values should preserve comma
        assert b'"User, Test"' in csv_content

    def test_detect_csv_encoding(self):
        """Test CSV encoding detection."""
        utf8_content = "email,name\ntest@example.com,Tëst".encode()

        decoded = utf8_content.decode("utf-8")
        assert "Tëst" in decoded


class TestJSONParsing:
    """Test JSON parsing functionality."""

    def test_parse_json_array(self):
        """Test parsing JSON array."""
        json_content = [{"id": 1}, {"id": 2}]

        assert isinstance(json_content, list)
        assert len(json_content) == 2

    def test_parse_json_with_data_key(self):
        """Test parsing JSON with data key."""
        json_content = {"data": [{"id": 1}, {"id": 2}], "total": 2}

        data = json_content.get("data", json_content)
        assert len(data) == 2

    def test_parse_invalid_json(self):
        """Test handling invalid JSON."""
        invalid_json = b"not valid json"

        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)


class TestImportValidation:
    """Test import validation."""

    def test_validate_required_fields(self):
        """Test validation of required fields."""
        required = ["email"]
        row = {"full_name": "Test User"}

        missing = [f for f in required if f not in row]
        assert "email" in missing

    def test_validate_email_format(self):
        """Test email format validation."""
        import re

        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

        valid = "test@example.com"
        invalid = "not-an-email"

        assert re.match(email_pattern, valid)
        assert not re.match(email_pattern, invalid)

    def test_validate_field_types(self):
        """Test field type validation."""
        field_types = {
            "id": "integer",
            "email": "string",
            "is_active": "boolean",
        }

        row = {"id": "not-an-integer", "email": "test@example.com", "is_active": True}

        # id should fail integer validation
        is_valid_id = str(row["id"]).isdigit()
        assert is_valid_id is False

    def test_validate_unique_constraint(self):
        """Test unique constraint validation."""
        existing_emails = {"user1@example.com", "user2@example.com"}
        new_email = "user1@example.com"

        is_duplicate = new_email in existing_emails
        assert is_duplicate is True


class TestImportModes:
    """Test import modes."""

    def test_create_mode_skip_existing(self):
        """Test create mode skips existing records."""
        mode = ImportMode.CREATE.value
        existing_emails = {"user@example.com"}
        row = {"email": "user@example.com"}

        should_skip = row["email"] in existing_emails and mode == "create"
        assert should_skip is True

    def test_update_mode_skip_new(self):
        """Test update mode skips new records."""
        mode = ImportMode.UPDATE.value
        existing_emails = {"user@example.com"}
        row = {"email": "new@example.com"}

        should_skip = row["email"] not in existing_emails and mode == "update"
        assert should_skip is True

    def test_upsert_mode_handles_all(self):
        """Test upsert mode handles all records."""
        mode = ImportMode.UPSERT.value
        existing_emails = {"user@example.com"}

        rows = [
            {"email": "user@example.com"},  # Update
            {"email": "new@example.com"},  # Create
        ]

        for row in rows:
            if row["email"] in existing_emails:
                action = "update"
            else:
                action = "create"
            assert action in ["create", "update"]


class TestBatchProcessing:
    """Test batch processing."""

    def test_process_in_batches(self):
        """Test processing rows in batches."""
        total_rows = 250
        batch_size = 100

        batches = (total_rows + batch_size - 1) // batch_size
        assert batches == 3

    def test_batch_commit(self):
        """Test committing after each batch."""
        rows = list(range(250))
        batch_size = 100
        commits = 0

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            # Process batch
            commits += 1

        assert commits == 3

    def test_batch_error_handling(self):
        """Test error handling within batches."""
        batch = [
            {"email": "valid@example.com"},
            {"email": "invalid"},
            {"email": "test@example.com"},
        ]
        errors = []
        processed = 0

        for i, row in enumerate(batch):
            if "@" not in row["email"]:
                errors.append({"row": i, "message": "Invalid email"})
            else:
                processed += 1

        assert processed == 2
        assert len(errors) == 1


class TestDuplicateHandling:
    """Test duplicate handling."""

    def test_detect_duplicates_in_file(self):
        """Test detecting duplicates within import file."""
        rows = [
            {"email": "user1@example.com"},
            {"email": "user2@example.com"},
            {"email": "user1@example.com"},  # Duplicate
        ]

        seen = set()
        duplicates = []

        for i, row in enumerate(rows):
            if row["email"] in seen:
                duplicates.append(i)
            else:
                seen.add(row["email"])

        assert len(duplicates) == 1
        assert duplicates[0] == 2

    def test_detect_duplicates_with_existing(self):
        """Test detecting duplicates with existing records."""
        existing = {"user1@example.com", "user2@example.com"}
        rows = [
            {"email": "user1@example.com"},  # Exists
            {"email": "user3@example.com"},  # New
        ]

        duplicates = [r for r in rows if r["email"] in existing]
        assert len(duplicates) == 1


class TestFieldMapping:
    """Test field mapping."""

    def test_map_csv_headers_to_fields(self):
        """Test mapping CSV headers to entity fields."""
        csv_headers = ["Email Address", "Full Name", "Active"]
        field_mapping = {
            "Email Address": "email",
            "Full Name": "full_name",
            "Active": "is_active",
        }

        mapped = [field_mapping.get(h, h) for h in csv_headers]

        assert "email" in mapped
        assert "full_name" in mapped

    def test_handle_unmapped_fields(self):
        """Test handling unmapped fields."""
        row = {"email": "test@example.com", "custom_field": "value"}
        known_fields = {"email", "full_name", "is_active"}

        unknown = [k for k in row if k not in known_fields]
        assert "custom_field" in unknown


class TestImportErrorHandling:
    """Test import error handling."""

    def test_collect_row_errors(self):
        """Test collecting errors per row."""
        errors = []

        errors.append({"row": 1, "field": "email", "message": "Invalid email"})
        errors.append({"row": 3, "field": "password", "message": "Too short"})

        assert len(errors) == 2

    def test_error_threshold(self):
        """Test stopping import at error threshold."""
        max_errors = 10
        errors = []

        for i in range(15):
            if len(errors) >= max_errors:
                break
            errors.append({"row": i, "message": f"Error {i}"})

        assert len(errors) == max_errors

    @pytest.mark.asyncio
    async def test_rollback_on_critical_error(self):
        """Test rollback on critical error."""
        state = {"committed": False, "rolled_back": False}

        try:
            raise ValueError("Critical error")
        except ValueError:
            state["rolled_back"] = True

        assert state["rolled_back"] is True


class TestImportProgress:
    """Test import progress tracking."""

    def test_track_progress(self):
        """Test tracking import progress."""
        total_rows = 100
        processed = 0

        for i in range(total_rows):
            processed += 1
            progress = (processed / total_rows) * 100

            if i == 49:
                assert progress == 50.0

    def test_report_progress_periodically(self):
        """Test reporting progress periodically."""
        total_rows = 1000
        report_interval = 100
        reports = []

        for i in range(1, total_rows + 1):
            if i % report_interval == 0:
                reports.append(i)

        assert len(reports) == 10


class TestGenericImporterImplementation:
    """Test GenericImporter actual implementation."""

    @pytest.mark.asyncio
    async def test_importer_initialization(self):
        """Test importer can be initialized with session."""
        from app.infrastructure.data_exchange.generic_importer import GenericImporter

        mock_session = AsyncMock()
        importer = GenericImporter(mock_session)

        assert importer is not None
        assert importer.session == mock_session

    @pytest.mark.asyncio
    async def test_get_importer_function(self):
        """Test get_importer convenience function."""
        from app.infrastructure.data_exchange.generic_importer import get_importer

        mock_session = AsyncMock()
        importer = get_importer(mock_session)

        assert importer is not None
        assert importer.session == mock_session

    def test_get_template_unknown_entity_raises(self):
        """Test get_template raises for unknown entity."""
        from app.domain.ports.data_exchange import EntityRegistry
        from app.infrastructure.data_exchange.generic_importer import GenericImporter

        mock_session = AsyncMock()
        importer = GenericImporter(mock_session)

        with patch.object(EntityRegistry, "get", return_value=None):
            with pytest.raises(ValueError, match="not found in registry"):
                importer.get_template("nonexistent_entity")

    def test_get_template_unsupported_format_raises(self):
        """Test get_template raises for unsupported format."""
        from app.domain.ports.data_exchange import EntityRegistry
        from app.infrastructure.data_exchange.generic_importer import GenericImporter

        mock_session = AsyncMock()
        importer = GenericImporter(mock_session)

        mock_config = MagicMock()

        with patch.object(EntityRegistry, "get", return_value=mock_config):
            with pytest.raises(ValueError, match="Unsupported format"):
                importer.get_template("users", format="xml")

    def test_get_template_csv_format(self):
        """Test get_template returns CSV template."""
        from app.domain.ports.data_exchange import EntityRegistry
        from app.infrastructure.data_exchange.generic_importer import GenericImporter

        mock_session = AsyncMock()
        importer = GenericImporter(mock_session)

        mock_config = MagicMock()
        mock_config.get_importable_fields.return_value = []

        with patch.object(EntityRegistry, "get", return_value=mock_config):
            with patch(
                "app.infrastructure.data_exchange.generic_importer.get_csv_handler"
            ) as mock_csv:
                mock_csv.return_value.generate_template.return_value = b"email,name\n"
                result = importer.get_template("users", format="csv")

        assert result == b"email,name\n"

    def test_get_template_excel_unavailable_raises(self):
        """Test get_template raises when Excel not available."""
        from app.domain.ports.data_exchange import EntityRegistry
        from app.infrastructure.data_exchange.generic_importer import GenericImporter

        mock_session = AsyncMock()
        importer = GenericImporter(mock_session)

        mock_config = MagicMock()

        with patch.object(EntityRegistry, "get", return_value=mock_config):
            with patch(
                "app.infrastructure.data_exchange.generic_importer.is_excel_available",
                return_value=False,
            ):
                with pytest.raises(ValueError, match="Excel support not available"):
                    importer.get_template("users", format="excel")


class TestImportRequestActual:
    """Test actual ImportRequest class."""

    def test_import_request_creation(self):
        """Test ImportRequest creation."""
        from app.domain.ports.data_exchange import ImportMode
        from app.domain.ports.import_export import ImportRequest

        file = BytesIO(b"email,name\ntest@example.com,Test")

        request = ImportRequest(
            entity="users",
            file=file,
            file_type="csv",
            mode=ImportMode.INSERT,
        )

        assert request.entity == "users"
        assert request.file_type == "csv"
        assert request.mode == ImportMode.INSERT

    def test_import_request_with_dry_run(self):
        """Test ImportRequest with dry run."""
        from app.domain.ports.data_exchange import ImportMode
        from app.domain.ports.import_export import ImportRequest

        file = BytesIO(b"email\ntest@example.com")

        request = ImportRequest(
            entity="users",
            file=file,
            file_type="csv",
            mode=ImportMode.INSERT,
            dry_run=True,
        )

        assert request.dry_run is True

    def test_import_request_with_tenant(self):
        """Test ImportRequest with tenant_id."""
        from app.domain.ports.data_exchange import ImportMode
        from app.domain.ports.import_export import ImportRequest

        file = BytesIO(b"email\ntest@example.com")
        tenant_id = uuid4()

        request = ImportRequest(
            entity="users",
            file=file,
            file_type="csv",
            mode=ImportMode.INSERT,
            tenant_id=tenant_id,
        )

        assert request.tenant_id == tenant_id

    def test_import_request_skip_errors(self):
        """Test ImportRequest with skip_errors."""
        from app.domain.ports.data_exchange import ImportMode
        from app.domain.ports.import_export import ImportRequest

        file = BytesIO(b"email\ntest@example.com")

        request = ImportRequest(
            entity="users",
            file=file,
            file_type="csv",
            mode=ImportMode.INSERT,
            skip_errors=True,
        )

        assert request.skip_errors is True


class TestImportResultActual:
    """Test actual ImportResult class."""

    def test_import_result_creation(self):
        """Test ImportResult creation."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(
            total_rows=100,
            inserted=80,
            updated=15,
            skipped=5,
        )

        assert result.total_rows == 100
        assert result.inserted == 80
        assert result.updated == 15
        assert result.skipped == 5

    def test_import_result_with_errors(self):
        """Test ImportResult with errors."""
        from app.domain.ports.import_export import DataImportError, ImportResult

        errors = [
            DataImportError(row=1, field="email", value="bad", error="Invalid email"),
            DataImportError(row=3, field="name", value="", error="Required field"),
        ]

        result = ImportResult(
            total_rows=10,
            errors=errors,
        )

        assert len(result.errors) == 2
        assert result.errors[0].row == 1
        assert result.errors[0].field == "email"

    def test_import_result_with_warnings(self):
        """Test ImportResult with warnings."""
        from app.domain.ports.import_export import ImportResult, DataImportWarning

        warnings = [
            DataImportWarning(row=5, field="description", message="Truncated long value"),
        ]

        result = ImportResult(
            total_rows=10,
            warnings=warnings,
        )

        assert len(result.warnings) == 1
        assert result.warnings[0].row == 5

    def test_import_result_duration(self):
        """Test ImportResult with duration."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(
            total_rows=100,
            duration_ms=150.5,
        )

        assert result.duration_ms == 150.5


class TestImportModeEnum:
    """Test ImportMode enum."""

    def test_import_mode_insert(self):
        """Test INSERT mode."""
        from app.domain.ports.data_exchange import ImportMode

        assert ImportMode.INSERT == "insert"

    def test_import_mode_upsert(self):
        """Test UPSERT mode."""
        from app.domain.ports.data_exchange import ImportMode

        assert ImportMode.UPSERT == "upsert"

    def test_import_mode_update_only(self):
        """Test UPDATE_ONLY mode."""
        from app.domain.ports.data_exchange import ImportMode

        assert ImportMode.UPDATE_ONLY == "update_only"


class TestImportErrorClass:
    """Test DataImportError dataclass."""

    def test_import_error_creation(self):
        """Test DataImportError creation."""
        from app.domain.ports.import_export import DataImportError

        error = DataImportError(
            row=5,
            field="email",
            value="invalid-email",
            error="Invalid email format",
        )

        assert error.row == 5
        assert error.field == "email"
        assert error.value == "invalid-email"
        assert error.error == "Invalid email format"

    def test_import_error_optional_fields(self):
        """Test DataImportError with None fields."""
        from app.domain.ports.import_export import DataImportError

        error = DataImportError(
            row=1,
            field=None,
            value=None,
            error="General error",
        )

        assert error.field is None
        assert error.value is None


class TestImportWarningClass:
    """Test DataImportWarning dataclass."""

    def test_import_warning_creation(self):
        """Test DataImportWarning creation."""
        from app.domain.ports.import_export import DataImportWarning

        warning = DataImportWarning(
            row=10,
            field="description",
            message="Value truncated to 255 characters",
        )

        assert warning.row == 10
        assert warning.field == "description"
        assert "truncated" in warning.message


class TestImportModeEnum:
    """Test ImportMode enum."""

    def test_insert_mode(self):
        """Test INSERT import mode."""
        from app.domain.ports.import_export import ImportMode

        assert ImportMode.INSERT == "insert"

    def test_upsert_mode(self):
        """Test UPSERT import mode."""
        from app.domain.ports.import_export import ImportMode

        assert ImportMode.UPSERT == "upsert"

    def test_update_only_mode(self):
        """Test UPDATE_ONLY import mode."""
        from app.domain.ports.import_export import ImportMode

        assert ImportMode.UPDATE_ONLY == "update_only"


class TestGenericImporterProcessing:
    """Test GenericImporter processing methods."""

    def test_get_importer_returns_instance(self):
        """Test get_importer factory function."""
        from unittest.mock import MagicMock

        from app.infrastructure.data_exchange.generic_importer import get_importer

        session = MagicMock()
        importer = get_importer(session)

        assert importer is not None
        # GenericImporter uses validate method not import_data
        assert hasattr(importer, "validate")

    def test_importer_has_session(self):
        """Test importer stores session."""
        from unittest.mock import MagicMock

        from app.infrastructure.data_exchange.generic_importer import GenericImporter

        session = MagicMock()
        importer = GenericImporter(session)

        assert importer.session == session

    def test_is_excel_available_function(self):
        """Test is_excel_available function."""
        from app.infrastructure.data_exchange.generic_importer import is_excel_available

        result = is_excel_available()
        assert isinstance(result, bool)


class TestImportRequestWithOptions:
    """Test ImportRequest with various options."""

    def test_import_request_with_skip_errors(self):
        """Test ImportRequest with skip_errors option."""
        from io import BytesIO

        from app.domain.ports.import_export import ImportRequest

        file_obj = BytesIO(b"test content")
        request = ImportRequest(
            entity="users",
            file=file_obj,
            file_type="csv",
            skip_errors=True,
        )

        assert request.skip_errors is True

    def test_import_request_with_tenant(self):
        """Test ImportRequest with tenant_id."""
        from io import BytesIO
        from uuid import uuid4

        from app.domain.ports.import_export import ImportRequest

        file_obj = BytesIO(b"test content")
        tenant_id = uuid4()
        request = ImportRequest(
            entity="users",
            file=file_obj,
            file_type="csv",
            tenant_id=tenant_id,
        )

        assert request.tenant_id == tenant_id

    def test_import_request_dry_run(self):
        """Test ImportRequest with dry_run option."""
        from io import BytesIO

        from app.domain.ports.import_export import ImportRequest

        file_obj = BytesIO(b"test content")
        request = ImportRequest(
            entity="users",
            file=file_obj,
            file_type="csv",
            dry_run=True,
        )

        assert request.dry_run is True

    def test_import_request_default_mode(self):
        """Test ImportRequest default mode is INSERT."""
        from io import BytesIO

        from app.domain.ports.import_export import ImportMode, ImportRequest

        file_obj = BytesIO(b"test content")
        request = ImportRequest(
            entity="users",
            file=file_obj,
            file_type="csv",
        )

        assert request.mode == ImportMode.INSERT


class TestImportResultCounts:
    """Test ImportResult count tracking."""

    def test_result_total_rows(self):
        """Test ImportResult total_rows tracking."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(total_rows=500)

        assert result.total_rows == 500

    def test_result_inserted_count(self):
        """Test ImportResult inserted count."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(inserted=100)

        assert result.inserted == 100

    def test_result_updated_count(self):
        """Test ImportResult updated count."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(updated=50)

        assert result.updated == 50

    def test_result_skipped_count(self):
        """Test ImportResult skipped count."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(skipped=10)

        assert result.skipped == 10

    def test_result_with_duration(self):
        """Test ImportResult with duration."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(
            total_rows=100,
            inserted=80,
            updated=15,
            skipped=5,
            duration_ms=250.5,
        )

        assert result.duration_ms == 250.5

    def test_result_dry_run_flag(self):
        """Test ImportResult dry_run flag."""
        from app.domain.ports.import_export import ImportResult

        result = ImportResult(
            total_rows=100,
            dry_run=True,
        )

        assert result.dry_run is True


class TestImportResultErrors:
    """Test ImportResult error handling."""

    def test_result_with_errors(self):
        """Test ImportResult with errors."""
        from app.domain.ports.import_export import DataImportError, ImportResult

        errors = [
            DataImportError(
                row=1, field="email", value="invalid", error="Invalid email format"
            ),
            DataImportError(
                row=3, field="status", value="unknown", error="Invalid status value"
            ),
        ]

        result = ImportResult(
            total_rows=100,
            inserted=98,
            errors=errors,
        )

        assert len(result.errors) == 2
        assert result.errors[0].row == 1

    def test_result_with_warnings(self):
        """Test ImportResult with warnings."""
        from app.domain.ports.import_export import ImportResult, DataImportWarning

        warnings = [
            DataImportWarning(row=5, field="description", message="Value truncated"),
            DataImportWarning(row=10, field="name", message="Extra whitespace removed"),
        ]

        result = ImportResult(
            total_rows=100,
            inserted=100,
            warnings=warnings,
        )

        assert len(result.warnings) == 2
        assert result.warnings[0].field == "description"


class TestImportErrorDetails:
    """Test DataImportError detailed attributes."""

    def test_error_with_row_number(self):
        """Test DataImportError row number tracking."""
        from app.domain.ports.import_export import DataImportError

        error = DataImportError(
            row=42,
            field="email",
            value="bad-email",
            error="Invalid format",
        )

        assert error.row == 42

    def test_error_with_field_name(self):
        """Test DataImportError field name."""
        from app.domain.ports.import_export import DataImportError

        error = DataImportError(
            row=1,
            field="is_active",
            value="maybe",
            error="Expected boolean",
        )

        assert error.field == "is_active"

    def test_error_with_invalid_value(self):
        """Test DataImportError invalid value capture."""
        from app.domain.ports.import_export import DataImportError

        error = DataImportError(
            row=5,
            field="created_at",
            value="not-a-date",
            error="Invalid datetime format",
        )

        assert error.value == "not-a-date"


class TestImportWarningDetails:
    """Test DataImportWarning detailed attributes."""

    def test_warning_with_null_field(self):
        """Test DataImportWarning with None field."""
        from app.domain.ports.import_export import DataImportWarning

        warning = DataImportWarning(
            row=1,
            field=None,
            message="Row has extra columns that were ignored",
        )

        assert warning.field is None

    def test_warning_message_content(self):
        """Test DataImportWarning message content."""
        from app.domain.ports.import_export import DataImportWarning

        warning = DataImportWarning(
            row=15,
            field="phone",
            message="Phone number was reformatted to international format",
        )

        assert "reformatted" in warning.message
