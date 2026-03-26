# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Data Exchange infrastructure package.

Provides implementations for import/export/reports functionality.
"""

from app.domain.ports.data_exchange import (
    EntityConfig,
    EntityRegistry,
    ExportFormat,
    FieldConfig,
    FieldType,
    ImportMode,
    ReportFormat,
)
from app.domain.ports.import_export import (
    DataImportError,
    DataImportWarning,
    ExportPort,
    ExportRequest,
    ExportResult,
    ImportPort,
    ImportRequest,
    ImportResult,
)
from app.domain.ports.reports import (
    ReportFilter,
    ReportGrouping,
    ReportPort,
    ReportRequest,
    ReportResult,
    ReportSummary,
)

__all__ = [
    # Data Exchange Core
    "EntityConfig",
    "EntityRegistry",
    "ExportFormat",
    "FieldConfig",
    "FieldType",
    "ImportMode",
    "ReportFormat",
    # Import/Export
    "ExportPort",
    "ExportRequest",
    "ExportResult",
    "DataImportError",
    "ImportPort",
    "ImportRequest",
    "ImportResult",
    "DataImportWarning",
    # Reports
    "ReportFilter",
    "ReportGrouping",
    "ReportPort",
    "ReportRequest",
    "ReportResult",
    "ReportSummary",
    # Entity Registration
    "register_entities",
    "register_entity",
]


# Import implementations for easy access
from app.infrastructure.data_exchange.advanced_excel_handler import (
    AdvancedExcelHandler,
    ConditionalFormatConfig,
    DataValidationConfig,
    ExcelChartConfig,
    ExcelSheetConfig,
    FormatRule,
    FormulaColumn,
    create_excel_report,
    create_multi_sheet_excel,
    is_advanced_excel_available,
)
from app.infrastructure.data_exchange.advanced_excel_handler import (
    ChartType as ExcelChartType,
)
from app.infrastructure.data_exchange.entities import register_entities, register_entity
from app.infrastructure.data_exchange.generic_exporter import (
    GenericExporter,
    get_exporter,
)
from app.infrastructure.data_exchange.generic_importer import (
    GenericImporter,
    get_importer,
)
from app.infrastructure.data_exchange.generic_reporter import (
    GenericReporter,
    get_reporter,
)
from app.infrastructure.data_exchange.pdf_handler import (
    ChartData as PDFChartData,
)
from app.infrastructure.data_exchange.pdf_handler import (
    ChartType as PDFChartType,
)

# Advanced handlers for enhanced PDF/Excel features
from app.infrastructure.data_exchange.pdf_handler import (
    PageOrientation,
    PageSize,
    PDFConfig,
    PDFHandler,
    generate_pdf_report,
    is_pdf_available,
)

__all__ += [
    "GenericImporter",
    "GenericExporter",
    "GenericReporter",
    "get_importer",
    "get_exporter",
    "get_reporter",
    # PDF Handler
    "PDFHandler",
    "PDFConfig",
    "PDFChartData",
    "PDFChartType",
    "PageOrientation",
    "PageSize",
    "is_pdf_available",
    "generate_pdf_report",
    # Advanced Excel Handler
    "AdvancedExcelHandler",
    "ExcelSheetConfig",
    "ExcelChartConfig",
    "FormulaColumn",
    "ConditionalFormatConfig",
    "DataValidationConfig",
    "ExcelChartType",
    "FormatRule",
    "is_advanced_excel_available",
    "create_excel_report",
    "create_multi_sheet_excel",
]
