# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Import/Export port interfaces.

Defines abstract interfaces for data import and export operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, BinaryIO
from uuid import UUID

from app.domain.ports.data_exchange import ExportFormat, ImportMode


@dataclass
class DataImportError:
    """Details of an import error."""

    row: int
    field: str | None
    value: Any
    error: str


@dataclass
class DataImportWarning:
    """Details of an import warning."""

    row: int
    field: str | None
    message: str


@dataclass
class ImportRequest:
    """
    Request to import data from a file.

    Attributes:
        entity: Name of the registered entity
        file: File-like object containing the data
        file_type: Type of file (csv, excel)
        mode: Import mode (insert, upsert, update_only)
        dry_run: If True, validate only without importing
        tenant_id: Tenant context for multi-tenant import
        skip_errors: Continue importing even if some rows fail
    """

    entity: str
    file: BinaryIO
    file_type: str = "csv"
    mode: ImportMode = ImportMode.INSERT
    dry_run: bool = False
    tenant_id: UUID | None = None
    skip_errors: bool = True


@dataclass
class ImportResult:
    """
    Result of an import operation.

    Attributes:
        total_rows: Total rows processed
        inserted: Number of rows inserted
        updated: Number of rows updated
        skipped: Number of rows skipped
        errors: List of errors encountered
        warnings: List of warnings
        dry_run: Whether this was a dry run
        duration_ms: Operation duration in milliseconds
    """

    total_rows: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[DataImportError] = field(default_factory=list)
    warnings: list[DataImportWarning] = field(default_factory=list)
    dry_run: bool = False
    duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        """Check if import was successful (no errors or all skipped)."""
        return len(self.errors) == 0 or self.inserted + self.updated > 0

    @property
    def error_count(self) -> int:
        """Get total error count."""
        return len(self.errors)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "total_rows": self.total_rows,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "error_count": self.error_count,
            "errors": [
                {
                    "row": e.row,
                    "field": e.field,
                    "value": str(e.value) if e.value is not None else None,
                    "error": e.error,
                }
                for e in self.errors[:100]  # Limit errors in response
            ],
            "warnings": [
                {"row": w.row, "field": w.field, "message": w.message}
                for w in self.warnings[:50]
            ],
            "dry_run": self.dry_run,
            "duration_ms": round(self.duration_ms, 2),
            "success": self.success,
        }


@dataclass
class ExportRequest:
    """
    Request to export data.

    Attributes:
        entity: Name of the registered entity
        filters: Filters to apply to the data
        columns: Specific columns to export (None = all exportable)
        format: Export format (csv, excel, json)
        tenant_id: Tenant context for multi-tenant export
        include_headers: Include column headers
        filename: Custom filename (auto-generated if None)
    """

    entity: str
    filters: dict[str, Any] | None = None
    columns: list[str] | None = None
    format: ExportFormat = ExportFormat.CSV
    tenant_id: UUID | None = None
    include_headers: bool = True
    filename: str | None = None


@dataclass
class ExportResult:
    """
    Result of an export operation.

    Attributes:
        content: The exported file content
        filename: Generated filename
        content_type: MIME type of the content
        row_count: Number of rows exported
        duration_ms: Operation duration in milliseconds
    """

    content: bytes
    filename: str
    content_type: str
    row_count: int
    duration_ms: float = 0.0


class ImportPort(ABC):
    """
    Abstract interface for data import operations.

    Implementations should handle:
    - Reading data from CSV/Excel files
    - Validating data against entity configuration
    - Inserting/updating records in the database
    - Handling errors gracefully
    """

    @abstractmethod
    async def validate(self, request: ImportRequest) -> ImportResult:
        """
        Validate import file without actually importing.

        This is used for dry-run operations to check data before import.

        Args:
            request: Import request with dry_run=True

        Returns:
            ImportResult with validation results
        """
        ...

    @abstractmethod
    async def execute(self, request: ImportRequest) -> ImportResult:
        """
        Execute the import operation.

        Args:
            request: Import request

        Returns:
            ImportResult with operation results
        """
        ...

    @abstractmethod
    def get_template(self, entity: str, format: str = "csv") -> bytes:
        """
        Generate an empty template file for import.

        The template includes all importable fields as headers
        with optional example row.

        Args:
            entity: Entity name
            format: Template format (csv, excel)

        Returns:
            Template file content as bytes
        """
        ...


class ExportPort(ABC):
    """
    Abstract interface for data export operations.

    Implementations should handle:
    - Querying data from the database
    - Formatting data according to field configurations
    - Generating CSV/Excel/JSON output
    """

    @abstractmethod
    async def export(self, request: ExportRequest) -> ExportResult:
        """
        Export data according to the request.

        Args:
            request: Export request configuration

        Returns:
            ExportResult with file content and metadata
        """
        ...

    @abstractmethod
    async def get_preview(
        self,
        entity: str,
        filters: dict[str, Any] | None = None,
        tenant_id: UUID | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get a preview of data to be exported.

        Args:
            entity: Entity name
            filters: Filters to apply
            tenant_id: Tenant context
            limit: Maximum rows to return

        Returns:
            List of dictionaries representing rows
        """
        ...
