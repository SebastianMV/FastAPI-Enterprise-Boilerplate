# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Pydantic schemas for Dashboard endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class StatItem(BaseModel):
    """Individual statistic item."""

    name: str = Field(max_length=100)
    value: int | str
    change: str = Field(max_length=50)
    change_type: str = Field(
        max_length=20, description="positive, negative, or neutral"
    )


class ActivityItem(BaseModel):
    """Recent activity item."""

    id: str = Field(max_length=50)
    action: str = Field(max_length=100)
    description: str = Field(max_length=500)
    timestamp: datetime
    user_name: str | None = Field(default=None, max_length=200)
    user_email: str | None = Field(default=None, max_length=320)


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response."""

    total_users: int
    active_users: int
    inactive_users: int
    total_roles: int
    total_api_keys: int
    active_api_keys: int
    users_created_last_30_days: int
    users_created_last_7_days: int
    stats: list[StatItem]


class RecentActivityResponse(BaseModel):
    """Recent activity response."""

    items: list[ActivityItem]
    total: int


class SystemHealthResponse(BaseModel):
    """System health metrics."""

    database_status: str = Field(max_length=20)
    cache_status: str = Field(max_length=20)
    avg_response_time_ms: float
    uptime_percentage: float
    active_sessions: int
