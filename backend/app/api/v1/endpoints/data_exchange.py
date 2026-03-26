# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Data Exchange API endpoints.

Provides REST endpoints for import, export, and report generation.
"""

import io
from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentTenantId,
    require_permission,
)
from app.domain.ports.data_exchange import (
    EntityRegistry,
    ExportFormat,
    ImportMode,
    ReportFormat,
)
from app.domain.ports.reports import ReportFilter
from app.infrastructure.data_exchange.generic_exporter import get_exporter
from app.infrastructure.data_exchange.generic_importer import get_importer
from app.infrastructure.data_exchange.generic_reporter import get_reporter
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/data", tags=["Data Exchange"])

# Server-side file size limit for imports
MAX_IMPORT_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Type aliases
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
DataReader = Annotated[UUID, Depends(require_permission("data", "read"))]
DataWriter = Annotated[UUID, Depends(require_permission("data", "write"))]


# ============================================================================
# Schemas
# ============================================================================


class EntityFieldResponse(BaseModel):
    """Field information for an entity."""

    name: str = Field(max_length=100)
    display_name: str = Field(max_length=200)
    field_type: str = Field(max_length=50)
    required: bool
    exportable: bool
    importable: bool


class EntityResponse(BaseModel):
    """Entity information for data exchange."""

    name: str = Field(max_length=100)
    display_name: str = Field(max_length=200)
    exportable: bool
    importable: bool
    fields: list[EntityFieldResponse]


class ImportResultResponse(BaseModel):
    """Import operation result."""

    total_rows: int
    inserted: int
    updated: int
    skipped: int
    error_count: int
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    dry_run: bool
    duration_ms: float
    success: bool


class ExportPreviewResponse(BaseModel):
    """Preview of data to be exported."""

    rows: list[dict[str, Any]]
    total_count: int


class ReportFilterRequest(BaseModel):
    """Filter for report generation."""

    field: str = Field(..., max_length=100)
    operator: str = Field(default="eq", max_length=20)
    value: Any


class ReportRequest(BaseModel):
    """Request to generate a report."""

    title: str | None = Field(default=None, max_length=200)
    filters: list[ReportFilterRequest] = Field(default_factory=list, max_length=50)
    columns: list[str] | None = Field(default=None, max_length=100)
    group_by: list[str] | None = Field(default=None, max_length=20)
    sort_by: str | None = Field(default=None, max_length=100)
    format: str = Field(default="pdf", max_length=20)
    include_summary: bool = True
    date_range_field: str | None = Field(default=None, max_length=100)
    date_from: str | None = Field(default=None, max_length=50)
    date_to: str | None = Field(default=None, max_length=50)


class ReportSummaryResponse(BaseModel):
    """Summary statistics for a report."""

    total_records: int
    grouped_counts: dict[str, int]
    numeric_summaries: dict[str, dict[str, float]]


# ============================================================================
# Entity Discovery Endpoints
# ============================================================================


@router.get(
    "/entities",
    response_model=list[EntityResponse],
    summary="List available entities",
    description="Get list of entities available for import/export/reports.",
)
async def list_entities(
    current_user_id: DataReader,
    tenant_id: CurrentTenantId = None,
) -> list[EntityResponse]:
    """
    List all registered entities with their field information.

    Returns entities that the current user has permission to access.
    """
    entities = []

    for config in EntityRegistry.list_all():
        # Build field list
        fields = [
            EntityFieldResponse(
                name=f.name,
                display_name=f.display_name,
                field_type=f.field_type.value,
                required=f.required,
                exportable=f.exportable,
                importable=f.importable,
            )
            for f in config.fields
        ]

        entities.append(
            EntityResponse(
                name=config.name,
                display_name=config.display_name,
                exportable=any(f.exportable for f in config.fields),
                importable=any(f.importable for f in config.fields),
                fields=fields,
            )
        )

    return entities


@router.get(
    "/entities/{entity}",
    response_model=EntityResponse,
    summary="Get entity details",
    description="Get detailed information about a specific entity.",
)
async def get_entity(
    current_user_id: DataReader,
    tenant_id: CurrentTenantId = None,
    entity: str = Path(..., max_length=50),
) -> EntityResponse:
    """Get detailed information about a specific entity."""
    config = EntityRegistry.get(entity)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"},
        )

    fields = [
        EntityFieldResponse(
            name=f.name,
            display_name=f.display_name,
            field_type=f.field_type.value,
            required=f.required,
            exportable=f.exportable,
            importable=f.importable,
        )
        for f in config.fields
    ]

    return EntityResponse(
        name=config.name,
        display_name=config.display_name,
        exportable=any(f.exportable for f in config.fields),
        importable=any(f.importable for f in config.fields),
        fields=fields,
    )


# ============================================================================
# Export Endpoints
# ============================================================================


@router.get(
    "/export/{entity}",
    summary="Export entity data",
    description="Export data from an entity to CSV, Excel, or JSON.",
)
async def export_data(
    session: DbSession,
    current_user_id: DataReader,
    entity: str = Path(..., max_length=50),
    tenant_id: CurrentTenantId = None,
    format: str = Query("csv", enum=["csv", "excel", "json"]),
    columns: str | None = Query(
        None, description="Comma-separated column names", max_length=500
    ),
) -> StreamingResponse:
    """
    Export entity data to a file.

    Args:
        entity: Entity name to export
        format: Export format (csv, excel, json)
        columns: Optional comma-separated list of columns to include
    """
    config = EntityRegistry.get(entity)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"},
        )

    # Parse columns
    column_list = None
    if columns:
        column_list = [c.strip() for c in columns.split(",")]

    # Get exporter
    exporter = get_exporter(session)

    from app.domain.ports.import_export import ExportRequest

    result = await exporter.export(
        ExportRequest(
            entity=entity,
            format=ExportFormat(format),
            columns=column_list,
            tenant_id=tenant_id,
        )
    )

    return StreamingResponse(
        io.BytesIO(result.content),
        media_type=result.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Row-Count": str(result.row_count),
        },
    )


@router.get(
    "/export/{entity}/preview",
    response_model=ExportPreviewResponse,
    summary="Preview export data",
    description="Get a preview of data to be exported.",
)
async def preview_export(
    session: DbSession,
    current_user_id: DataReader,
    entity: str = Path(..., max_length=50),
    tenant_id: CurrentTenantId = None,
    limit: int = Query(10, ge=1, le=100),
) -> ExportPreviewResponse:
    """Get a preview of data that would be exported."""
    config = EntityRegistry.get(entity)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"},
        )

    exporter = get_exporter(session)

    rows = await exporter.get_preview(
        entity=entity,
        tenant_id=tenant_id,
        limit=limit,
    )

    total = await exporter.get_count(entity=entity, tenant_id=tenant_id)

    return ExportPreviewResponse(rows=rows, total_count=total)


# ============================================================================
# Import Endpoints
# ============================================================================


@router.get(
    "/import/{entity}/template",
    summary="Download import template",
    description="Download an empty template file for importing data.",
)
async def download_template(
    current_user_id: DataReader,
    session: DbSession,
    tenant_id: CurrentTenantId = None,
    entity: str = Path(..., max_length=50),
    format: str = Query("csv", enum=["csv", "excel"]),
) -> StreamingResponse:
    """
    Download an empty template for importing data.

    The template includes all importable fields with example values.
    """
    config = EntityRegistry.get(entity)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"},
        )

    importer = get_importer(session)

    try:
        template = importer.get_template(entity, format)
    except ValueError as e:
        logger.warning(
            "template_generation_failed", entity=entity, error=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TEMPLATE_GENERATION_FAILED",
                "message": "Failed to generate import template",
            },
        ) from e

    filename = f"{entity}_template.{format if format == 'csv' else 'xlsx'}"
    content_type = (
        "text/csv"
        if format == "csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    return StreamingResponse(
        io.BytesIO(template),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/import/{entity}",
    response_model=ImportResultResponse,
    summary="Import data",
    description="Import data from a CSV or Excel file.",
)
async def import_data(
    session: DbSession,
    current_user_id: DataWriter,
    entity: str = Path(..., max_length=50),
    tenant_id: CurrentTenantId = None,
    file: UploadFile = File(...),
    mode: str = Query("insert", enum=["insert", "upsert", "update_only"]),
    dry_run: bool = Query(False, description="Validate without importing"),
    skip_errors: bool = Query(True, description="Continue on errors"),
) -> ImportResultResponse:
    """
    Import data from a file.

    Args:
        entity: Entity name to import into
        file: CSV or Excel file
        mode: Import mode (insert, upsert, update_only)
        dry_run: If True, only validate without importing
        skip_errors: If True, continue importing even if some rows fail
    """
    config = EntityRegistry.get(entity)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"},
        )

    # Server-side file size validation
    # Check reported size first (if available) to fail fast
    if hasattr(file, "size") and file.size and file.size > MAX_IMPORT_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": "File too large. Maximum size is 50 MB.",
            },
        )

    # Stream-check actual size to avoid loading entire file into memory
    file_size = 0
    while chunk := await file.read(8192):
        file_size += len(chunk)
        if file_size > MAX_IMPORT_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "code": "FILE_TOO_LARGE",
                    "message": "File too large. Maximum size is 50 MB.",
                },
            )
    await file.seek(0)

    # Detect file type — validate via magic bytes AND extension to prevent
    # extension-spoofing attacks (CWE-434).
    # XLSX magic: PK\x03\x04 (ZIP container)
    # XLS magic:  \xD0\xCF\x11\xE0 (Compound Document)
    # CSV: no magic bytes, rely on extension.
    magic = await file.read(8)
    await file.seek(0)

    _XLSX_MAGIC = b"PK\x03\x04"
    _XLS_MAGIC = b"\xD0\xCF\x11\xE0"

    filename = file.filename or ""
    if filename.lower().endswith(".csv"):
        # CSV has no magic bytes; accept only if not a binary format
        if magic.startswith(_XLSX_MAGIC) or magic.startswith(_XLS_MAGIC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "FILE_TYPE_MISMATCH",
                    "message": "File content does not match the declared extension (.csv).",
                },
            )
        file_type = "csv"
    elif filename.lower().endswith((".xlsx", ".xls")):
        # Accept XLSX (ZIP-based) or legacy XLS (OLE2)
        if not (magic.startswith(_XLSX_MAGIC) or magic.startswith(_XLS_MAGIC)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "FILE_TYPE_MISMATCH",
                    "message": "File content does not match the declared extension (.xlsx/.xls).",
                },
            )
        file_type = "excel"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": "Unsupported file type. Use CSV or Excel (.xlsx).",
            },
        )

    from app.domain.ports.import_export import ImportRequest

    importer = get_importer(session)

    request = ImportRequest(
        entity=entity,
        file=file.file,
        file_type=file_type,
        mode=ImportMode(mode),
        dry_run=dry_run,
        tenant_id=tenant_id,
        skip_errors=skip_errors,
    )

    if dry_run:
        result = await importer.validate(request)
    else:
        result = await importer.execute(request)
        if result.success and not result.dry_run:
            await session.commit()

    return ImportResultResponse(**result.to_dict())


# ============================================================================
# Report Endpoints
# ============================================================================


@router.post(
    "/reports/{entity}",
    summary="Generate report",
    description="Generate a report for an entity.",
)
async def generate_report(
    session: DbSession,
    current_user_id: DataReader,
    entity: str = Path(..., max_length=50),
    request: ReportRequest = Body(...),
    tenant_id: CurrentTenantId = None,
) -> StreamingResponse:
    """
    Generate a report for an entity.

    Supports PDF, Excel, CSV, and HTML formats.
    """
    config = EntityRegistry.get(entity)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"},
        )

    from datetime import datetime

    from app.domain.ports.reports import ReportRequest as ReportReq

    # Build filters
    filters = [
        ReportFilter(field=f.field, operator=f.operator, value=f.value)
        for f in request.filters
    ]

    # Parse dates
    date_from = None
    date_to = None
    if request.date_from:
        try:
            date_from = datetime.fromisoformat(request.date_from)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_DATE",
                    "message": "Invalid date_from format. Use ISO 8601.",
                },
            ) from None
    if request.date_to:
        try:
            date_to = datetime.fromisoformat(request.date_to)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_DATE",
                    "message": "Invalid date_to format. Use ISO 8601.",
                },
            ) from None

    reporter = get_reporter(session)

    result = await reporter.generate(
        ReportReq(
            entity=entity,
            title=request.title,
            filters=filters,
            columns=request.columns,
            group_by=request.group_by,
            sort_by=request.sort_by,
            format=ReportFormat(request.format),
            tenant_id=tenant_id,
            include_summary=request.include_summary,
            date_range_field=request.date_range_field,
            date_from=date_from,
            date_to=date_to,
        )
    )

    return StreamingResponse(
        io.BytesIO(result.content),
        media_type=result.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Row-Count": str(result.row_count),
            "X-Generated-At": result.generated_at.isoformat(),
        },
    )


@router.get(
    "/reports/{entity}/preview",
    summary="Preview report data",
    description="Get a preview of data for a report.",
)
async def preview_report(
    session: DbSession,
    current_user_id: DataReader,
    entity: str = Path(..., max_length=50),
    tenant_id: CurrentTenantId = None,
    limit: int = Query(10, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Get a preview of data that would appear in a report."""
    config = EntityRegistry.get(entity)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"},
        )

    from app.domain.ports.reports import ReportRequest as ReportReq

    reporter = get_reporter(session)

    return await reporter.get_preview(
        ReportReq(entity=entity, tenant_id=tenant_id),
        limit=limit,
    )


@router.get(
    "/reports/{entity}/summary",
    response_model=ReportSummaryResponse,
    summary="Get report summary",
    description="Get summary statistics for a report without generating it.",
)
async def get_report_summary(
    session: DbSession,
    current_user_id: DataReader,
    entity: str = Path(..., max_length=50),
    tenant_id: CurrentTenantId = None,
    group_by: str | None = Query(
        None, description="Comma-separated fields to group by", max_length=500
    ),
) -> ReportSummaryResponse:
    """Get summary statistics without generating the full report."""
    config = EntityRegistry.get(entity)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ENTITY_NOT_FOUND", "message": "Entity not found"},
        )

    from app.domain.ports.reports import ReportRequest as ReportReq

    group_by_list = None
    if group_by:
        group_by_list = [g.strip() for g in group_by.split(",")]

    reporter = get_reporter(session)

    summary = await reporter.get_summary(
        ReportReq(
            entity=entity,
            tenant_id=tenant_id,
            group_by=group_by_list,
        )
    )

    return ReportSummaryResponse(
        total_records=summary.total_records,
        grouped_counts=summary.grouped_counts,
        numeric_summaries=summary.numeric_summaries,
    )
