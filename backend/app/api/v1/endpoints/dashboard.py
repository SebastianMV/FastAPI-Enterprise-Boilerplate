# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Dashboard statistics and analytics endpoints."""

from datetime import datetime, timedelta, UTC
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.models import (
    UserModel,
    RoleModel,
    APIKeyModel,
)

router = APIRouter(tags=["Dashboard"])


# ===========================================
# Response Schemas
# ===========================================

class StatItem(BaseModel):
    """Individual statistic item."""
    name: str
    value: int | str
    change: str
    change_type: str = Field(description="positive, negative, or neutral")


class ActivityItem(BaseModel):
    """Recent activity item."""
    id: str
    action: str
    description: str
    timestamp: datetime
    user_name: str | None = None
    user_email: str | None = None


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
    database_status: str
    cache_status: str
    avg_response_time_ms: float
    uptime_percentage: float
    active_sessions: int


# ===========================================
# Endpoints
# ===========================================

@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Get dashboard statistics",
    description="Get overview statistics for the dashboard.",
)
async def get_dashboard_stats(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardStatsResponse:
    """
    Get dashboard statistics including user counts, API keys, and trends.
    """
    now = datetime.now(UTC)
    last_30_days = now - timedelta(days=30)
    last_7_days = now - timedelta(days=7)
    last_month_start = now - timedelta(days=60)
    last_month_end = now - timedelta(days=30)
    
    # Total users
    total_users_result = await session.execute(
        select(func.count(UserModel.id)).where(UserModel.deleted_at.is_(None))
    )
    total_users = total_users_result.scalar() or 0
    
    # Active users
    active_users_result = await session.execute(
        select(func.count(UserModel.id)).where(
            UserModel.is_active == True,
            UserModel.deleted_at.is_(None),
        )
    )
    active_users = active_users_result.scalar() or 0
    
    # Inactive users
    inactive_users = total_users - active_users
    
    # Total roles
    total_roles_result = await session.execute(
        select(func.count(RoleModel.id))
    )
    total_roles = total_roles_result.scalar() or 0
    
    # Total API keys
    total_api_keys_result = await session.execute(
        select(func.count(APIKeyModel.id))
    )
    total_api_keys = total_api_keys_result.scalar() or 0
    
    # Active API keys
    active_api_keys_result = await session.execute(
        select(func.count(APIKeyModel.id)).where(APIKeyModel.is_active == True)
    )
    active_api_keys = active_api_keys_result.scalar() or 0
    
    # Users created in last 30 days
    users_30_days_result = await session.execute(
        select(func.count(UserModel.id)).where(
            UserModel.created_at >= last_30_days,
            UserModel.deleted_at.is_(None),
        )
    )
    users_created_last_30_days = users_30_days_result.scalar() or 0
    
    # Users created in last 7 days
    users_7_days_result = await session.execute(
        select(func.count(UserModel.id)).where(
            UserModel.created_at >= last_7_days,
            UserModel.deleted_at.is_(None),
        )
    )
    users_created_last_7_days = users_7_days_result.scalar() or 0
    
    # Users created in previous 30 days (for comparison)
    users_prev_30_days_result = await session.execute(
        select(func.count(UserModel.id)).where(
            UserModel.created_at >= last_month_start,
            UserModel.created_at < last_month_end,
            UserModel.deleted_at.is_(None),
        )
    )
    users_prev_30_days = users_prev_30_days_result.scalar() or 0
    
    # Calculate user growth percentage
    if users_prev_30_days > 0:
        user_growth = ((users_created_last_30_days - users_prev_30_days) / users_prev_30_days) * 100
        user_change = f"{'+' if user_growth >= 0 else ''}{user_growth:.0f}%"
        user_change_type = "positive" if user_growth > 0 else ("negative" if user_growth < 0 else "neutral")
    else:
        user_change = "+100%" if users_created_last_30_days > 0 else "0%"
        user_change_type = "positive" if users_created_last_30_days > 0 else "neutral"
    
    # Build stats array
    stats = [
        StatItem(
            name="Total Users",
            value=total_users,
            change=user_change,
            change_type=user_change_type,
        ),
        StatItem(
            name="Active Users",
            value=active_users,
            change=f"{(active_users / total_users * 100):.0f}%" if total_users > 0 else "0%",
            change_type="positive" if active_users > 0 else "neutral",
        ),
        StatItem(
            name="API Keys",
            value=active_api_keys,
            change=f"{active_api_keys}/{total_api_keys}",
            change_type="neutral",
        ),
        StatItem(
            name="Roles",
            value=total_roles,
            change="System",
            change_type="neutral",
        ),
    ]
    
    return DashboardStatsResponse(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        total_roles=total_roles,
        total_api_keys=total_api_keys,
        active_api_keys=active_api_keys,
        users_created_last_30_days=users_created_last_30_days,
        users_created_last_7_days=users_created_last_7_days,
        stats=stats,
    )


@router.get(
    "/activity",
    response_model=RecentActivityResponse,
    summary="Get recent activity",
    description="Get recent system activity for the dashboard.",
)
async def get_recent_activity(
    limit: int = 10,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> RecentActivityResponse:
    """
    Get recent activity including user registrations and API key creation.
    """
    activities: list[ActivityItem] = []
    
    # Get recent user registrations
    recent_users_result = await session.execute(
        select(UserModel)
        .where(UserModel.deleted_at.is_(None))
        .order_by(UserModel.created_at.desc())
        .limit(5)
    )
    recent_users = recent_users_result.scalars().all()
    
    for user in recent_users:
        activities.append(ActivityItem(
            id=str(user.id),
            action="user_registered",
            description=f"New user registered: {user.first_name} {user.last_name}",
            timestamp=user.created_at,
            user_name=f"{user.first_name} {user.last_name}",
            user_email=str(user.email),
        ))
    
    # Get recent API key creations
    recent_keys_result = await session.execute(
        select(APIKeyModel)
        .order_by(APIKeyModel.created_at.desc())
        .limit(5)
    )
    recent_keys = recent_keys_result.scalars().all()
    
    for key in recent_keys:
        activities.append(ActivityItem(
            id=str(key.id),
            action="api_key_created",
            description=f"API key created: {key.name}",
            timestamp=key.created_at,
        ))
    
    # Sort by timestamp and limit
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    activities = activities[:limit]
    
    return RecentActivityResponse(
        items=activities,
        total=len(activities),
    )


@router.get(
    "/health-metrics",
    response_model=SystemHealthResponse,
    summary="Get system health metrics",
    description="Get system health and performance metrics.",
)
async def get_system_health(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> SystemHealthResponse:
    """
    Get system health metrics including database status and response times.
    """
    from app.infrastructure.monitoring import get_metrics_service, get_uptime_tracker
    
    # Check database connectivity
    try:
        await session.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    # Check Redis health and get metrics
    metrics = get_metrics_service()
    redis_healthy, _redis_response_ms = await metrics.check_redis_health()
    cache_status = "healthy" if redis_healthy else "unhealthy"
    
    # Get response time metrics
    response_metrics = metrics.get_response_time_metrics()
    avg_response_time = response_metrics.avg_ms if response_metrics.sample_count > 0 else 0.0
    
    # Get uptime percentage
    uptime_tracker = get_uptime_tracker()
    uptime_percentage = await uptime_tracker.get_uptime_percentage()
    
    # Get active sessions (users with last_login in last 24 hours)
    last_24_hours = datetime.now(UTC) - timedelta(hours=24)
    active_sessions_result = await session.execute(
        select(func.count(UserModel.id)).where(
            UserModel.last_login >= last_24_hours,
            UserModel.deleted_at.is_(None),
        )
    )
    active_sessions = active_sessions_result.scalar() or 0
    
    return SystemHealthResponse(
        database_status=db_status,
        cache_status=cache_status,
        avg_response_time_ms=avg_response_time,
        uptime_percentage=uptime_percentage,
        active_sessions=active_sessions,
    )
