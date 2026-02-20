# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Report Templates API endpoints.

Provides CRUD for saved report templates and report scheduling.
"""

import asyncio
import html as _html
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentTenantId, CurrentUser, require_permission
from app.api.v1.schemas.common import ShortStr
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/report-templates", tags=["Report Templates"])

# Permission-based access
ReportsReader = Annotated[UUID, Depends(require_permission("reports", "read"))]
ReportsWriter = Annotated[UUID, Depends(require_permission("reports", "write"))]


# ============================================================================
# In-Memory Storage (DEMO ONLY — NOT FOR PRODUCTION)
# ============================================================================
# WARNING: Templates stored in-memory only — intended for development/demo mode.
# Production environments will return HTTP 501 via _check_demo_mode().
# - Data is lost on server restart.
# - Not safe for multi-worker deployments (each worker has its own copy).
# - Scheduled reports never actually execute (no background scheduler).
# For production, migrate to database-backed storage.

_report_templates: dict[str, dict[str, Any]] = {}
_scheduled_reports: dict[str, dict[str, Any]] = {}
_storage_lock = asyncio.Lock()


def _check_demo_mode() -> None:
    """Block in-memory report template endpoints in production."""
    from app.config import settings as _s

    if _s.ENVIRONMENT in ("production", "staging"):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "NOT_IMPLEMENTED",
                "message": "Report templates require database-backed storage in production.",
            },
        )


# Per-tenant limits to prevent unbounded memory growth (B5)
_MAX_TEMPLATES_PER_TENANT = 100
_MAX_SCHEDULES_PER_TENANT = 50


def _validate_webhook_url(url: str) -> None:
    """Validate webhook URL: enforce HTTPS, block SSRF targets.

    Rejects private networks (RFC 1918), link-local, loopback,
    and cloud metadata endpoints.
    """
    import ipaddress
    from urllib.parse import urlparse

    if not url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "WEBHOOK_HTTPS_REQUIRED",
                "message": "Webhook URL must use HTTPS",
            },
        )

    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    # Block known cloud metadata hostnames
    _BLOCKED_HOSTS = {
        "metadata.google.internal",
        "metadata.goog",
        "169.254.169.254",
        "fd00:ec2::254",
        "[fd00:ec2::254]",
    }
    if hostname.lower() in _BLOCKED_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "WEBHOOK_BLOCKED_HOST",
                "message": "Webhook URL points to a blocked host",
            },
        )

    # Block internal/private IPs
    try:
        addr = ipaddress.ip_address(hostname)
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "WEBHOOK_PRIVATE_IP",
                    "message": "Webhook URL must not point to a private/internal address",
                },
            )
    except ValueError:
        # hostname is a domain name, not an IP — allow (DNS resolution happens at call time)
        pass

    # Block localhost variants
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "WEBHOOK_LOCALHOST",
                "message": "Webhook URL must not point to localhost",
            },
        )


def _count_tenant_items(store: dict[str, dict[str, Any]], tenant: str | None) -> int:
    """Count items belonging to a tenant in an in-memory store."""
    if not tenant:
        return 0
    return sum(1 for item in store.values() if item.get("tenant_id") == tenant)


# ============================================================================
# Schemas
# TODO: Extract to app/api/v1/schemas/report_templates.py
# ============================================================================


class ReportFilterSchema(BaseModel):
    """Filter for report data."""

    field: str = Field(..., max_length=100)
    operator: str = Field(default="eq", pattern="^(eq|ne|gt|lt|gte|lte|contains|in)$")
    value: Any


class ReportTemplateCreate(BaseModel):
    """Request to create a report template."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    entity: str = Field(..., min_length=1, max_length=50)

    # Report configuration
    title: str = Field(..., min_length=1, max_length=200)
    format: str = Field(default="pdf", pattern="^(pdf|excel|csv|html)$")
    columns: list[Annotated[str, Field(max_length=100)]] | None = None
    filters: list[ReportFilterSchema] = Field(
        default_factory=lambda: list[ReportFilterSchema]()
    )
    group_by: list[Annotated[str, Field(max_length=100)]] | None = None
    sort_by: str | None = Field(default=None, max_length=100)
    include_summary: bool = True

    # Date range configuration
    date_range_field: str | None = Field(default=None, max_length=100)
    date_range_type: str | None = Field(
        default=None,
        pattern="^(today|yesterday|this_week|last_week|this_month|last_month|this_quarter|this_year|custom)$",
    )

    # PDF/Excel specific options
    page_orientation: str | None = Field(default=None, pattern="^(portrait|landscape)$")
    page_size: str | None = Field(default=None, pattern="^(A4|letter|legal|A3|A5)$")
    include_charts: bool = False
    watermark: str | None = Field(default=None, max_length=200)

    # Metadata
    is_public: bool = False
    tags: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list, max_length=50
    )


class ReportTemplateUpdate(BaseModel):
    """Request to update a report template."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    title: str | None = Field(None, min_length=1, max_length=200)
    format: str | None = Field(None, pattern="^(pdf|excel|csv|html)$")
    columns: list[Annotated[str, Field(max_length=100)]] | None = None
    filters: list[ReportFilterSchema] | None = None
    group_by: list[Annotated[str, Field(max_length=100)]] | None = None
    sort_by: str | None = Field(default=None, max_length=100)
    include_summary: bool | None = None
    date_range_field: str | None = Field(default=None, max_length=100)
    date_range_type: str | None = Field(
        default=None,
        pattern="^(today|yesterday|this_week|last_week|this_month|last_month|this_quarter|this_year|custom)$",
    )
    page_orientation: str | None = Field(default=None, pattern="^(portrait|landscape)$")
    page_size: str | None = Field(default=None, pattern="^(A4|letter|legal|A3|A5)$")
    include_charts: bool | None = None
    watermark: str | None = Field(default=None, max_length=200)
    is_public: bool | None = None
    tags: list[Annotated[str, Field(max_length=100)]] | None = Field(
        default=None, max_length=50
    )


class ReportTemplateResponse(BaseModel):
    """Response for a report template."""

    id: str = Field(max_length=50)
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    entity: str = Field(max_length=50)
    title: str = Field(max_length=200)
    format: str = Field(max_length=10)
    columns: list[Annotated[str, Field(max_length=100)]] | None = None
    filters: list[ReportFilterSchema]
    group_by: list[Annotated[str, Field(max_length=100)]] | None = None
    sort_by: str | None = Field(default=None, max_length=100)
    include_summary: bool
    date_range_field: str | None = Field(default=None, max_length=100)
    date_range_type: str | None = Field(default=None, max_length=20)
    page_orientation: str | None = Field(default=None, max_length=10)
    page_size: str | None = Field(default=None, max_length=10)
    include_charts: bool
    watermark: str | None = Field(default=None, max_length=200)
    is_public: bool
    tags: list[Annotated[str, Field(max_length=100)]]
    created_by: str = Field(max_length=50)
    created_at: datetime
    updated_at: datetime
    tenant_id: str | None = Field(default=None, max_length=50)


class ScheduleFrequency(BaseModel):
    """Schedule frequency configuration."""

    type: str = Field(..., pattern="^(once|daily|weekly|monthly|quarterly)$")
    day_of_week: int | None = Field(default=None, ge=0, le=6)  # 0=Monday
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    time: str = Field(default="09:00", pattern="^\\d{2}:\\d{2}$")  # HH:MM
    timezone: str = Field(
        default="UTC",
        max_length=50,
        pattern="^[A-Za-z_/+-]+$",
    )


class ScheduledReportCreate(BaseModel):
    """Request to schedule a report."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    # Schedule configuration
    frequency: ScheduleFrequency
    start_date: datetime | None = None
    end_date: datetime | None = None

    # Delivery options
    delivery_method: str = Field(default="email", pattern="^(email|storage|webhook)$")
    recipients: list[Annotated[str, Field(max_length=320)]] = Field(
        default_factory=list, max_length=100
    )  # Email addresses
    storage_path: str | None = Field(
        default=None, max_length=2048
    )  # For storage delivery
    webhook_url: str | None = Field(
        default=None, max_length=2048
    )  # For webhook delivery

    # Options
    enabled: bool = True
    notify_on_failure: bool = True


class ScheduledReportUpdate(BaseModel):
    """Request to update a scheduled report."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    frequency: ScheduleFrequency | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    delivery_method: str | None = Field(
        default=None, pattern="^(email|storage|webhook)$"
    )
    recipients: list[Annotated[str, Field(max_length=320)]] | None = Field(
        default=None, max_length=100
    )
    storage_path: str | None = Field(default=None, max_length=2048)
    webhook_url: str | None = Field(default=None, max_length=2048)
    enabled: bool | None = None
    notify_on_failure: bool | None = None


class ScheduledReportResponse(BaseModel):
    """Response for a scheduled report."""

    id: str = Field(max_length=50)
    template_id: str = Field(max_length=50)
    template_name: str = Field(max_length=100)
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    frequency: ScheduleFrequency
    start_date: datetime | None
    end_date: datetime | None
    delivery_method: str = Field(max_length=20)
    recipients: list[Annotated[str, Field(max_length=320)]]
    storage_path: str | None = Field(default=None, max_length=2048)
    webhook_url: str | None = Field(default=None, max_length=2048)
    enabled: bool
    notify_on_failure: bool
    last_run: datetime | None
    next_run: datetime | None
    run_count: int
    error_count: int
    created_by: str = Field(max_length=50)
    created_at: datetime


class ScheduleExecutionHistory(BaseModel):
    """History entry for scheduled report execution."""

    id: str = Field(max_length=50)
    schedule_id: str = Field(max_length=50)
    executed_at: datetime
    status: str = Field(max_length=20)  # success, failed, cancelled
    duration_seconds: float
    error_message: str | None = Field(default=None, max_length=2000)
    file_size_bytes: int | None
    recipients_notified: int


# ============================================================================
# Report Template Endpoints
# ============================================================================


@router.post(
    "",
    response_model=ReportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create report template",
    description="Create a new saved report template.",
)
async def create_template(
    request: ReportTemplateCreate,
    current_user: CurrentUser,
    current_user_id: ReportsWriter,
    tenant_id: CurrentTenantId = None,
) -> ReportTemplateResponse:
    """Create a new report template."""
    _check_demo_mode()

    template_id = str(uuid4())
    now = datetime.now(UTC)

    # Enforce per-tenant template limit (B5 — prevent unbounded memory growth)
    current_tenant = str(tenant_id) if tenant_id else None
    if (
        _count_tenant_items(_report_templates, current_tenant)
        >= _MAX_TEMPLATES_PER_TENANT
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TEMPLATE_LIMIT_REACHED",
                "message": f"Maximum of {_MAX_TEMPLATES_PER_TENANT} templates per tenant reached",
            },
        )

    template: dict[str, Any] = {
        "id": template_id,
        "name": _html.escape(request.name),
        "description": _html.escape(request.description)
        if request.description
        else None,
        "entity": request.entity,
        "title": _html.escape(request.title),
        "format": request.format,
        "columns": request.columns,
        "filters": [f.model_dump() for f in request.filters],
        "group_by": request.group_by,
        "sort_by": request.sort_by,
        "include_summary": request.include_summary,
        "date_range_field": request.date_range_field,
        "date_range_type": request.date_range_type,
        "page_orientation": request.page_orientation,
        "page_size": request.page_size,
        "include_charts": request.include_charts,
        "watermark": _html.escape(request.watermark) if request.watermark else None,
        "is_public": request.is_public,
        "tags": [_html.escape(t) for t in request.tags],
        "created_by": str(current_user.id),
        "created_at": now,
        "updated_at": now,
        "tenant_id": str(tenant_id) if tenant_id else None,
    }

    async with _storage_lock:
        _report_templates[template_id] = template

    logger.info(
        "report_template_created",
        template_id=str(template_id),
        name=request.name,
        user_id=str(current_user.id),
    )

    return ReportTemplateResponse(**template)


@router.get(
    "",
    response_model=list[ReportTemplateResponse],
    summary="List report templates",
    description="List all report templates accessible to the user.",
)
async def list_templates(
    current_user: CurrentUser,
    current_user_id: ReportsReader,
    tenant_id: CurrentTenantId = None,
    entity: str | None = Query(None, description="Filter by entity", max_length=100),
    format: str | None = Query(None, description="Filter by format", max_length=50),
    tag: str | None = Query(None, description="Filter by tag", max_length=100),
    include_public: bool = Query(True, description="Include public templates"),
) -> list[ReportTemplateResponse]:
    """List report templates."""

    user_id = str(current_user.id)
    tenant = str(tenant_id) if tenant_id else None

    results: list[ReportTemplateResponse] = []
    for template in _report_templates.values():
        # Filter by tenant — public templates are only visible within the same tenant
        if tenant:
            if template.get("tenant_id") and template.get("tenant_id") != tenant:
                continue
        else:
            # No tenant context: only show templates without tenant_id or owned by user
            if template.get("tenant_id"):
                continue

        # Filter by ownership or public
        if template.get("created_by") != user_id and not template.get("is_public"):
            if not current_user.is_superuser:
                continue

        # Apply filters
        if entity and template.get("entity") != entity:
            continue
        if format and template.get("format") != format:
            continue
        if tag and tag not in template.get("tags", []):
            continue

        results.append(ReportTemplateResponse(**template))

    return sorted(results, key=lambda x: x.name)


@router.get(
    "/{template_id}",
    response_model=ReportTemplateResponse,
    summary="Get report template",
    description="Get a specific report template by ID.",
)
async def get_template(
    template_id: str = Path(..., max_length=50),
    *,
    current_user: CurrentUser,
    current_user_id: ReportsReader,
    tenant_id: CurrentTenantId = None,
) -> ReportTemplateResponse:
    """Get a report template."""

    template = _report_templates.get(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TEMPLATE_NOT_FOUND",
                "message": "Report template not found",
            },
        )

    # Tenant isolation: ensure template belongs to the current tenant
    template_tenant = template.get("tenant_id")
    current_tenant = str(tenant_id) if tenant_id else None
    if template_tenant and current_tenant and template_tenant != current_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TEMPLATE_NOT_FOUND",
                "message": "Report template not found",
            },
        )

    # Check access
    user_id = str(current_user.id)
    if template.get("created_by") != user_id and not template.get("is_public"):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCESS_DENIED", "message": "Access denied"},
            )

    return ReportTemplateResponse(**template)


@router.patch(
    "/{template_id}",
    response_model=ReportTemplateResponse,
    summary="Update report template",
    description="Update an existing report template.",
)
async def update_template(
    template_id: str = Path(..., max_length=50),
    *,
    request: ReportTemplateUpdate,
    current_user: CurrentUser,
    current_user_id: ReportsWriter,
    tenant_id: CurrentTenantId = None,
) -> ReportTemplateResponse:
    """Update a report template."""
    _check_demo_mode()

    async with _storage_lock:
        template = _report_templates.get(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TEMPLATE_NOT_FOUND",
                    "message": "Report template not found",
                },
            )

        # Tenant isolation
        template_tenant = template.get("tenant_id")
        current_tenant = str(tenant_id) if tenant_id else None
        if template_tenant and current_tenant and template_tenant != current_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TEMPLATE_NOT_FOUND",
                    "message": "Report template not found",
                },
            )

        # Check ownership
        if template.get("created_by") != str(current_user.id):
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "FORBIDDEN",
                        "message": "Only the owner can update this template",
                    },
                )

        # Update fields (exclude_unset preserves intentional None assignments)
        update_data = request.model_dump(exclude_unset=True)
        if "filters" in update_data:
            update_data["filters"] = (
                [f.model_dump() for f in request.filters] if request.filters else []
            )

        # Escape HTML-sensitive fields to prevent stored XSS (matches create_template)
        _escape_fields = {"name", "description", "title", "watermark"}
        for key, value in update_data.items():
            if key in _escape_fields and isinstance(value, str):
                template[key] = _html.escape(value)
            elif key == "tags" and isinstance(value, list):
                tags_list: list[str] = value
                template[key] = [_html.escape(str(t)) for t in tags_list]
            else:
                template[key] = value

        template["updated_at"] = datetime.now(UTC)

    logger.info(
        "report_template_updated",
        template_id=str(template_id),
        user_id=str(current_user.id),
    )

    return ReportTemplateResponse(**template)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete report template",
    description="Delete a report template.",
)
async def delete_template(
    template_id: str = Path(..., max_length=50),
    *,
    current_user: CurrentUser,
    current_user_id: ReportsWriter,
    tenant_id: CurrentTenantId = None,
) -> None:
    """Delete a report template."""
    _check_demo_mode()

    async with _storage_lock:
        template = _report_templates.get(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TEMPLATE_NOT_FOUND",
                    "message": "Report template not found",
                },
            )

        # Tenant isolation
        template_tenant = template.get("tenant_id")
        current_tenant = str(tenant_id) if tenant_id else None
        if template_tenant and current_tenant and template_tenant != current_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TEMPLATE_NOT_FOUND",
                    "message": "Report template not found",
                },
            )

        # Check ownership
        if template.get("created_by") != str(current_user.id):
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "FORBIDDEN",
                        "message": "Only the owner can delete this template",
                    },
                )

        # Check for scheduled reports using this template
        for schedule in _scheduled_reports.values():
            if schedule.get("template_id") == template_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "TEMPLATE_HAS_SCHEDULES",
                        "message": "Cannot delete template with active schedules",
                    },
                )

        del _report_templates[template_id]

    logger.info(
        "report_template_deleted",
        template_id=str(template_id),
        user_id=str(current_user.id),
    )


@router.post(
    "/{template_id}/duplicate",
    response_model=ReportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate report template",
    description="Create a copy of an existing report template.",
)
async def duplicate_template(
    template_id: str = Path(..., max_length=50),
    *,
    current_user: CurrentUser,
    current_user_id: ReportsWriter,
    tenant_id: CurrentTenantId = None,
    name: str = Query(
        ..., description="Name for the duplicated template", max_length=200
    ),
) -> ReportTemplateResponse:
    """Duplicate a report template."""
    _check_demo_mode()

    async with _storage_lock:
        template = _report_templates.get(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TEMPLATE_NOT_FOUND",
                    "message": "Report template not found",
                },
            )

        # Tenant isolation
        template_tenant = template.get("tenant_id")
        current_tenant = str(tenant_id) if tenant_id else None
        if template_tenant and current_tenant and template_tenant != current_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TEMPLATE_NOT_FOUND",
                    "message": "Report template not found",
                },
            )

        # Check per-tenant template limit
        current_tenant = str(tenant_id) if tenant_id else None
        if (
            _count_tenant_items(_report_templates, current_tenant)
            >= _MAX_TEMPLATES_PER_TENANT
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "TEMPLATE_LIMIT_REACHED",
                    "message": f"Maximum of {_MAX_TEMPLATES_PER_TENANT} templates per tenant reached",
                },
            )

        # Create copy
        new_id = str(uuid4())
        now = datetime.now(UTC)

        new_template = dict(template)
        new_template.update(
            {
                "id": new_id,
                "name": _html.escape(name),
                "is_public": False,
                "created_by": str(current_user.id),
                "created_at": now,
                "updated_at": now,
                "tenant_id": str(tenant_id) if tenant_id else None,
            }
        )

        _report_templates[new_id] = new_template

    logger.info(
        "report_template_duplicated",
        source_id=str(template_id),
        new_id=str(new_id),
        user_id=str(current_user.id),
    )

    return ReportTemplateResponse(**new_template)


# ============================================================================
# Report Scheduling Endpoints
# ============================================================================


@router.post(
    "/{template_id}/schedule",
    response_model=ScheduledReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule report",
    description="Create a scheduled report from a template.",
)
async def create_schedule(
    template_id: str = Path(..., max_length=50),
    *,
    request: ScheduledReportCreate,
    current_user: CurrentUser,
    current_user_id: ReportsWriter,
    tenant_id: CurrentTenantId = None,
) -> ScheduledReportResponse:
    """Create a scheduled report."""
    _check_demo_mode()

    # Verify template exists
    template = _report_templates.get(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TEMPLATE_NOT_FOUND",
                "message": "Report template not found",
            },
        )

    # Tenant isolation: verify template belongs to current tenant
    template_tenant = template.get("tenant_id")
    current_tenant = str(tenant_id) if tenant_id else None
    if template_tenant and current_tenant and template_tenant != current_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TEMPLATE_NOT_FOUND",
                "message": "Report template not found",
            },
        )

    # Validate delivery method requirements
    if request.delivery_method == "email" and not request.recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "RECIPIENTS_REQUIRED",
                "message": "Email delivery requires at least one recipient",
            },
        )
    if request.delivery_method == "webhook" and not request.webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "WEBHOOK_URL_REQUIRED",
                "message": "Webhook delivery requires a webhook URL",
            },
        )
    if request.webhook_url:
        _validate_webhook_url(request.webhook_url)

    # Enforce per-tenant schedule limit (B5 — prevent unbounded memory growth)
    current_tenant_str = str(tenant_id) if tenant_id else None
    if (
        _count_tenant_items(_scheduled_reports, current_tenant_str)
        >= _MAX_SCHEDULES_PER_TENANT
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SCHEDULE_LIMIT_REACHED",
                "message": f"Maximum of {_MAX_SCHEDULES_PER_TENANT} schedules per tenant reached",
            },
        )

    # Validate recipient email addresses
    import re as _re

    _email_re = _re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    for email in request.recipients:
        if not _email_re.match(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_RECIPIENT_EMAIL",
                    "message": "Invalid email address in recipients",
                },
            )

    # Validate storage_path (prevent path traversal)
    if request.storage_path:
        import posixpath

        normalized = posixpath.normpath(request.storage_path)
        if ".." in normalized.split("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_STORAGE_PATH",
                    "message": "Invalid storage path",
                },
            )

    schedule_id = str(uuid4())
    now = datetime.now(UTC)

    # Calculate next run
    next_run = _calculate_next_run(request.frequency, request.start_date)

    schedule: dict[str, Any] = {
        "id": schedule_id,
        "template_id": template_id,
        "template_name": template.get("name"),
        "name": _html.escape(request.name),
        "description": _html.escape(request.description) if request.description else None,
        "frequency": request.frequency.model_dump(),
        "start_date": request.start_date,
        "end_date": request.end_date,
        "delivery_method": request.delivery_method,
        "recipients": request.recipients,
        "storage_path": request.storage_path,
        "webhook_url": request.webhook_url,
        "enabled": request.enabled,
        "notify_on_failure": request.notify_on_failure,
        "last_run": None,
        "next_run": next_run,
        "run_count": 0,
        "error_count": 0,
        "created_by": str(current_user.id),
        "created_at": now,
        "tenant_id": str(tenant_id) if tenant_id else None,
    }

    async with _storage_lock:
        _scheduled_reports[schedule_id] = schedule

    logger.info(
        "report_schedule_created",
        schedule_id=str(schedule_id),
        template_id=str(template_id),
        user_id=str(current_user.id),
    )

    return ScheduledReportResponse(**schedule)


@router.get(
    "/schedules",
    response_model=list[ScheduledReportResponse],
    summary="List scheduled reports",
    description="List all scheduled reports for the user.",
)
async def list_schedules(
    current_user: CurrentUser,
    current_user_id: ReportsReader,
    tenant_id: CurrentTenantId = None,
    enabled_only: bool = Query(False, description="Only show enabled schedules"),
) -> list[ScheduledReportResponse]:
    """List scheduled reports."""

    user_id = str(current_user.id)
    tenant = str(tenant_id) if tenant_id else None

    results: list[ScheduledReportResponse] = []
    for schedule in _scheduled_reports.values():
        # Filter by tenant
        if tenant and schedule.get("tenant_id") != tenant:
            continue

        # Filter by ownership
        if schedule.get("created_by") != user_id and not current_user.is_superuser:
            continue

        # Filter by enabled status
        if enabled_only and not schedule.get("enabled"):
            continue

        results.append(ScheduledReportResponse(**schedule))

    return sorted(results, key=lambda x: x.name)


@router.get(
    "/schedules/{schedule_id}",
    response_model=ScheduledReportResponse,
    summary="Get scheduled report",
    description="Get details of a scheduled report.",
)
async def get_schedule(
    schedule_id: ShortStr,
    current_user: CurrentUser,
    current_user_id: ReportsReader,
    tenant_id: CurrentTenantId = None,
) -> ScheduledReportResponse:
    """Get a scheduled report."""

    schedule = _scheduled_reports.get(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SCHEDULE_NOT_FOUND",
                "message": "Scheduled report not found",
            },
        )

    # Tenant isolation
    schedule_tenant = schedule.get("tenant_id")
    current_tenant = str(tenant_id) if tenant_id else None
    if schedule_tenant and current_tenant and schedule_tenant != current_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SCHEDULE_NOT_FOUND",
                "message": "Scheduled report not found",
            },
        )

    # Check access
    if schedule.get("created_by") != str(current_user.id):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCESS_DENIED", "message": "Access denied"},
            )

    return ScheduledReportResponse(**schedule)


@router.patch(
    "/schedules/{schedule_id}",
    response_model=ScheduledReportResponse,
    summary="Update scheduled report",
    description="Update a scheduled report configuration.",
)
async def update_schedule(
    schedule_id: ShortStr,
    request: ScheduledReportUpdate,
    current_user: CurrentUser,
    current_user_id: ReportsWriter,
    tenant_id: CurrentTenantId = None,
) -> ScheduledReportResponse:
    """Update a scheduled report."""
    _check_demo_mode()

    # Validate webhook URL if being updated
    if request.webhook_url:
        _validate_webhook_url(request.webhook_url)

    # Validate recipient emails if being updated
    if request.recipients:
        import re as _re

        _email_re = _re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        for email in request.recipients:
            if not _email_re.match(email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_RECIPIENT_EMAIL",
                        "message": "Invalid email address in recipients",
                    },
                )

    # Validate storage_path (prevent path traversal)
    if request.storage_path:
        import posixpath

        normalized = posixpath.normpath(request.storage_path)
        if ".." in normalized.split("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_STORAGE_PATH",
                    "message": "Invalid storage path",
                },
            )

    # All checks and updates inside lock to prevent TOCTOU race condition
    update_data = request.model_dump(exclude_unset=True)

    async with _storage_lock:
        schedule = _scheduled_reports.get(schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": "Scheduled report not found",
                },
            )

        # Tenant isolation
        schedule_tenant = schedule.get("tenant_id")
        current_tenant = str(tenant_id) if tenant_id else None
        if schedule_tenant and current_tenant and schedule_tenant != current_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": "Scheduled report not found",
                },
            )

        # Check ownership
        if schedule.get("created_by") != str(current_user.id):
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "FORBIDDEN",
                        "message": "Only the owner can update this schedule",
                    },
                )

        if "frequency" in update_data and request.frequency:
            update_data["frequency"] = request.frequency.model_dump()
            schedule["next_run"] = _calculate_next_run(
                request.frequency, schedule.get("start_date")
            )

        # Escape HTML-sensitive string fields to prevent stored XSS
        _schedule_escape_fields = {"name", "description"}
        for key, value in update_data.items():
            if key in _schedule_escape_fields and isinstance(value, str):
                schedule[key] = _html.escape(value)
            else:
                schedule[key] = value

    logger.info(
        "report_schedule_updated",
        schedule_id=str(schedule_id),
        user_id=str(current_user.id),
    )

    return ScheduledReportResponse(**schedule)


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete scheduled report",
    description="Delete a scheduled report.",
)
async def delete_schedule(
    schedule_id: ShortStr,
    current_user: CurrentUser,
    current_user_id: ReportsWriter,
    tenant_id: CurrentTenantId = None,
) -> None:
    """Delete a scheduled report."""
    _check_demo_mode()

    async with _storage_lock:
        schedule = _scheduled_reports.get(schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": "Scheduled report not found",
                },
            )

        # Tenant isolation
        schedule_tenant = schedule.get("tenant_id")
        current_tenant = str(tenant_id) if tenant_id else None
        if schedule_tenant and current_tenant and schedule_tenant != current_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": "Scheduled report not found",
                },
            )

        # Check ownership
        if schedule.get("created_by") != str(current_user.id):
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "FORBIDDEN",
                        "message": "Only the owner can delete this schedule",
                    },
                )

        del _scheduled_reports[schedule_id]

    logger.info(
        "report_schedule_deleted",
        schedule_id=str(schedule_id),
        user_id=str(current_user.id),
    )


@router.post(
    "/schedules/{schedule_id}/run",
    summary="Run scheduled report now",
    description="Manually trigger a scheduled report execution.",
)
async def run_schedule_now(
    schedule_id: ShortStr,
    current_user: CurrentUser,
    current_user_id: ReportsWriter,
    tenant_id: CurrentTenantId = None,
) -> dict[str, str]:
    """Manually run a scheduled report."""
    _check_demo_mode()

    async with _storage_lock:
        schedule = _scheduled_reports.get(schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": "Scheduled report not found",
                },
            )

        # Tenant isolation
        schedule_tenant = schedule.get("tenant_id")
        current_tenant = str(tenant_id) if tenant_id else None
        if schedule_tenant and current_tenant and schedule_tenant != current_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": "Scheduled report not found",
                },
            )

        # Check access
        if schedule.get("created_by") != str(current_user.id):
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "ACCESS_DENIED", "message": "Access denied"},
                )

        # In production, this would queue a background job
        # For now, we just update the last_run timestamp
        schedule["last_run"] = datetime.now(UTC)
        schedule["run_count"] = schedule.get("run_count", 0) + 1

    logger.info(
        "report_schedule_triggered",
        schedule_id=str(schedule_id),
        user_id=str(current_user.id),
    )

    return {
        "status": "queued",
        "message": "Report generation has been queued",
        "schedule_id": schedule_id,
    }


@router.post(
    "/schedules/{schedule_id}/toggle",
    response_model=ScheduledReportResponse,
    summary="Toggle schedule enabled status",
    description="Enable or disable a scheduled report.",
)
async def toggle_schedule(
    schedule_id: ShortStr,
    current_user: CurrentUser,
    current_user_id: ReportsWriter,
    tenant_id: CurrentTenantId = None,
) -> ScheduledReportResponse:
    """Toggle schedule enabled status."""
    _check_demo_mode()

    async with _storage_lock:
        schedule = _scheduled_reports.get(schedule_id)
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": "Scheduled report not found",
                },
            )

        # Tenant isolation
        schedule_tenant = schedule.get("tenant_id")
        current_tenant = str(tenant_id) if tenant_id else None
        if schedule_tenant and current_tenant and schedule_tenant != current_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SCHEDULE_NOT_FOUND",
                    "message": "Scheduled report not found",
                },
            )

        # Check ownership
        if schedule.get("created_by") != str(current_user.id):
            if not current_user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "FORBIDDEN",
                        "message": "Only the owner can toggle this schedule",
                    },
                )

        schedule["enabled"] = not schedule.get("enabled", True)

    logger.info(
        "report_schedule_toggled",
        schedule_id=str(schedule_id),
        enabled=schedule["enabled"],
        user_id=str(current_user.id),
    )

    return ScheduledReportResponse(**schedule)


# ============================================================================
# Helper Functions
# ============================================================================


def _calculate_next_run(
    frequency: ScheduleFrequency,
    start_date: datetime | None = None,
) -> datetime:
    """Calculate the next run time for a schedule."""
    from datetime import timedelta

    now = datetime.now(UTC)
    base = start_date if start_date and start_date > now else now

    # Parse time
    hour, minute = map(int, frequency.time.split(":"))

    if frequency.type == "once":
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if frequency.type == "daily":
        next_run = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run

    if frequency.type == "weekly":
        next_run = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        target_day = frequency.day_of_week or 0
        days_ahead = target_day - next_run.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_run += timedelta(days=days_ahead)
        return next_run

    if frequency.type == "monthly":
        target_day = frequency.day_of_month or 1
        next_run = base.replace(
            day=min(target_day, 28),  # Safe for all months
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )
        if next_run <= now:
            if next_run.month == 12:
                next_run = next_run.replace(year=next_run.year + 1, month=1)
            else:
                next_run = next_run.replace(month=next_run.month + 1)
        return next_run

    if frequency.type == "quarterly":
        quarter_months = [1, 4, 7, 10]
        current_month = base.month
        next_quarter_month = next(
            (m for m in quarter_months if m > current_month),
            quarter_months[0],
        )
        year = base.year if next_quarter_month > current_month else base.year + 1
        return datetime(
            year=year,
            month=next_quarter_month,
            day=1,
            hour=hour,
            minute=minute,
            tzinfo=UTC,
        )

    return now
