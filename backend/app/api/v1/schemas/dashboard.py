# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Pydantic schemas for Dashboard endpoints."""

from datetime import datetime

from pydantic import BaseModel

from app.api.v1.schemas.common import (
    DescriptionStr,
    NameStr,
    ShortStr,
)


class StatItem(BaseModel):
    """Individual statistic item."""

    name: NameStr
    value: int | ShortStr
    change: ShortStr
    change_type: ShortStr


class ActivityItem(BaseModel):
    """Recent activity item."""

    id: ShortStr
    action: NameStr
    description: DescriptionStr
    timestamp: datetime
    user_name: NameStr | None = None
    user_email: NameStr | None = None


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

    database_status: ShortStr
    cache_status: ShortStr
    avg_response_time_ms: float
    uptime_percentage: float
    active_sessions: int
