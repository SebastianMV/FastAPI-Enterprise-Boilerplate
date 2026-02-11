# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Reports port interface.

Defines abstract interface for report generation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.ports.data_exchange import ReportFormat


@dataclass
class ReportFilter:
    """Filter to apply when generating a report."""

    field: str
    operator: str  # eq, ne, gt, gte, lt, lte, in, contains
    value: Any


@dataclass
class ReportGrouping:
    """Grouping configuration for reports."""

    field: str
    aggregate: str = "count"  # count, sum, avg, min, max


@dataclass
class ReportRequest:
    """
    Request to generate a report.

    Attributes:
        entity: Name of the registered entity
        title: Custom report title (uses entity default if None)
        filters: Filters to apply to the data
        columns: Specific columns to include (None = all exportable)
        group_by: Fields to group by
        sort_by: Field to sort by
        format: Output format (pdf, excel, csv, html)
        tenant_id: Tenant context for multi-tenant reports
        include_summary: Include summary statistics
        date_range_field: Field to use for date range filtering
        date_from: Start date for date range
        date_to: End date for date range
        header_text: Custom header text for PDF (default: report title)
        footer_text: Custom footer text for PDF (default: "Confidencial")
        show_page_numbers: Show page numbers in PDF header
        company_name: Company name to show in header
    """

    entity: str
    title: str | None = None
    filters: list[ReportFilter] = field(default_factory=list)
    columns: list[str] | None = None
    group_by: list[str] | None = None
    sort_by: str | None = None
    format: ReportFormat = ReportFormat.PDF
    tenant_id: UUID | None = None
    include_summary: bool = True
    date_range_field: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    header_text: str | None = None
    footer_text: str = "Confidencial"
    show_page_numbers: bool = True
    company_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity": self.entity,
            "title": self.title,
            "filters": [
                {"field": f.field, "operator": f.operator, "value": f.value}
                for f in self.filters
            ],
            "columns": self.columns,
            "group_by": self.group_by,
            "sort_by": self.sort_by,
            "format": self.format.value,
            "include_summary": self.include_summary,
        }


@dataclass
class ReportSummary:
    """Summary statistics for a report."""

    total_records: int
    grouped_counts: dict[str, int] = field(default_factory=dict)
    numeric_summaries: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class ReportResult:
    """
    Result of report generation.

    Attributes:
        content: The generated report content
        filename: Generated filename
        content_type: MIME type of the content
        generated_at: When the report was generated
        row_count: Number of data rows in report
        summary: Optional summary statistics
        duration_ms: Generation time in milliseconds
    """

    content: bytes
    filename: str
    content_type: str
    generated_at: datetime
    row_count: int
    summary: ReportSummary | None = None
    duration_ms: float = 0.0

    @staticmethod
    def get_content_type(format: ReportFormat) -> str:
        """Get MIME type for format."""
        return {
            ReportFormat.PDF: "application/pdf",
            ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ReportFormat.CSV: "text/csv",
            ReportFormat.HTML: "text/html",
        }.get(format, "application/octet-stream")


class ReportPort(ABC):
    """
    Abstract interface for report generation.

    Implementations should handle:
    - Querying data from the database
    - Formatting data according to field configurations
    - Generating PDF/Excel/CSV/HTML output
    - Including headers, footers, and styling
    """

    @abstractmethod
    async def generate(self, request: ReportRequest) -> ReportResult:
        """
        Generate a report according to the request.

        Args:
            request: Report request configuration

        Returns:
            ReportResult with file content and metadata
        """
        ...

    @abstractmethod
    async def get_preview(
        self,
        request: ReportRequest,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get a preview of data before generating report.

        Args:
            request: Report request
            limit: Maximum rows to return

        Returns:
            List of dictionaries representing rows
        """
        ...

    @abstractmethod
    async def get_summary(
        self,
        request: ReportRequest,
    ) -> ReportSummary:
        """
        Get summary statistics without generating full report.

        Args:
            request: Report request

        Returns:
            ReportSummary with statistics
        """
        ...
