# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Pydantic schemas for Report Template endpoints."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field


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
