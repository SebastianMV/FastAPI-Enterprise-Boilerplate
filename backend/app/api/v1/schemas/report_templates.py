# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Pydantic schemas for Report Template endpoints."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.api.v1.schemas.common import (
    NameStr,
    RoleNameStr,
    ShortStr,
    TextStr,
    UrlStr,
)


class ReportFilterSchema(BaseModel):
    """Filter for report data."""

    field: RoleNameStr
    operator: ShortStr = Field(
        default="eq", pattern="^(eq|ne|gt|lt|gte|lte|contains|in)$"
    )
    value: Any


class ReportTemplateCreate(BaseModel):
    """Request to create a report template."""

    name: RoleNameStr
    description: TextStr | None = None
    entity: ShortStr

    # Report configuration
    title: NameStr
    format: ShortStr = Field(default="pdf", pattern="^(pdf|excel|csv|html)$")
    columns: list[RoleNameStr] | None = None
    filters: list[ReportFilterSchema] = Field(
        default_factory=lambda: list[ReportFilterSchema]()
    )
    group_by: list[RoleNameStr] | None = None
    sort_by: RoleNameStr | None = None
    include_summary: bool = True

    # Date range configuration
    date_range_field: RoleNameStr | None = None
    date_range_type: ShortStr | None = Field(
        default=None,
        pattern="^(today|yesterday|this_week|last_week|this_month|last_month|this_quarter|this_year|custom)$",
    )

    # PDF/Excel specific options
    page_orientation: ShortStr | None = Field(
        default=None, pattern="^(portrait|landscape)$"
    )
    page_size: ShortStr | None = Field(
        default=None, pattern="^(A4|letter|legal|A3|A5)$"
    )
    include_charts: bool = False
    watermark: NameStr | None = None

    # Metadata
    is_public: bool = False
    tags: list[RoleNameStr] = Field(default_factory=list, max_length=50)


class ReportTemplateUpdate(BaseModel):
    """Request to update a report template."""

    name: RoleNameStr | None = None
    description: TextStr | None = None
    title: NameStr | None = None
    format: ShortStr | None = Field(None, pattern="^(pdf|excel|csv|html)$")
    columns: list[RoleNameStr] | None = None
    filters: list[ReportFilterSchema] | None = None
    group_by: list[RoleNameStr] | None = None
    sort_by: RoleNameStr | None = None
    include_summary: bool | None = None
    date_range_field: RoleNameStr | None = None
    date_range_type: ShortStr | None = Field(
        default=None,
        pattern="^(today|yesterday|this_week|last_week|this_month|last_month|this_quarter|this_year|custom)$",
    )
    page_orientation: ShortStr | None = Field(
        default=None, pattern="^(portrait|landscape)$"
    )
    page_size: ShortStr | None = Field(
        default=None, pattern="^(A4|letter|legal|A3|A5)$"
    )
    include_charts: bool | None = None
    watermark: NameStr | None = None
    is_public: bool | None = None
    tags: list[RoleNameStr] | None = Field(default=None, max_length=50)


class ReportTemplateResponse(BaseModel):
    """Response for a report template."""

    id: ShortStr
    name: RoleNameStr
    description: TextStr | None = None
    entity: ShortStr
    title: NameStr
    format: ShortStr
    columns: list[RoleNameStr] | None = None
    filters: list[ReportFilterSchema]
    group_by: list[RoleNameStr] | None = None
    sort_by: RoleNameStr | None = None
    include_summary: bool
    date_range_field: RoleNameStr | None = None
    date_range_type: ShortStr | None = None
    page_orientation: ShortStr | None = None
    page_size: ShortStr | None = None
    include_charts: bool
    watermark: NameStr | None = None
    is_public: bool
    tags: list[RoleNameStr]
    created_by: ShortStr
    created_at: datetime
    updated_at: datetime
    tenant_id: ShortStr | None = None


class ScheduleFrequency(BaseModel):
    """Schedule frequency configuration."""

    type: ShortStr = Field(..., pattern="^(once|daily|weekly|monthly|quarterly)$")
    day_of_week: int | None = Field(default=None, ge=0, le=6)  # 0=Monday
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    time: ShortStr = Field(default="09:00", pattern="^\\d{2}:\\d{2}$")  # HH:MM
    timezone: ShortStr = Field(
        default="UTC",
        pattern="^[A-Za-z_/+-]+$",
    )


class ScheduledReportCreate(BaseModel):
    """Request to schedule a report."""

    name: RoleNameStr
    description: TextStr | None = None

    # Schedule configuration
    frequency: ScheduleFrequency
    start_date: datetime | None = None
    end_date: datetime | None = None

    # Delivery options
    delivery_method: ShortStr = Field(
        default="email", pattern="^(email|storage|webhook)$"
    )
    recipients: list[Annotated[str, Field(max_length=320)]] = Field(
        default_factory=list, max_length=100
    )  # Email addresses
    storage_path: UrlStr | None = None  # For storage delivery
    webhook_url: UrlStr | None = None  # For webhook delivery

    # Options
    enabled: bool = True
    notify_on_failure: bool = True


class ScheduledReportUpdate(BaseModel):
    """Request to update a scheduled report."""

    name: RoleNameStr | None = None
    description: TextStr | None = None
    frequency: ScheduleFrequency | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    delivery_method: ShortStr | None = Field(
        default=None, pattern="^(email|storage|webhook)$"
    )
    recipients: list[Annotated[str, Field(max_length=320)]] | None = Field(
        default=None, max_length=100
    )
    storage_path: UrlStr | None = None
    webhook_url: UrlStr | None = None
    enabled: bool | None = None
    notify_on_failure: bool | None = None


class ScheduledReportResponse(BaseModel):
    """Response for a scheduled report."""

    id: ShortStr
    template_id: ShortStr
    template_name: RoleNameStr
    name: RoleNameStr
    description: TextStr | None = None
    frequency: ScheduleFrequency
    start_date: datetime | None
    end_date: datetime | None
    delivery_method: ShortStr
    recipients: list[Annotated[str, Field(max_length=320)]]
    storage_path: UrlStr | None = None
    webhook_url: UrlStr | None = None
    enabled: bool
    notify_on_failure: bool
    last_run: datetime | None
    next_run: datetime | None
    run_count: int
    error_count: int
    created_by: ShortStr
    created_at: datetime


class ScheduleExecutionHistory(BaseModel):
    """History entry for scheduled report execution."""

    id: ShortStr
    schedule_id: ShortStr
    executed_at: datetime
    status: ShortStr  # success, failed, cancelled
    duration_seconds: float
    error_message: TextStr | None = None
    file_size_bytes: int | None
    recipients_notified: int
