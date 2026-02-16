# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Dashboard statistics and analytics endpoints."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentTenantId, require_permission
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.models import (
    APIKeyModel,
    RoleModel,
    UserModel,
    UserSessionModel,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

# TODO: Migrate queries to repository layer for hexagonal architecture compliance.

router = APIRouter(tags=["Dashboard"])


# ===========================================
# Response Schemas
# TODO: Extract to app/api/v1/schemas/dashboard.py
# ===========================================


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
    current_user_id: UUID = Depends(require_permission("dashboard", "read")),
    tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> DashboardStatsResponse:
    """
    Get dashboard statistics including user counts, API keys, and trends.
    All queries are scoped to the current tenant.
    """
    now = datetime.now(UTC)
    last_30_days = now - timedelta(days=30)
    last_7_days = now - timedelta(days=7)

    # Use actual calendar month boundaries for accurate growth comparison
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if current_month_start.month == 1:
        prev_month_start = current_month_start.replace(
            year=current_month_start.year - 1, month=12
        )
    else:
        prev_month_start = current_month_start.replace(
            month=current_month_start.month - 1
        )
    prev_month_end = current_month_start
    last_month_start = prev_month_start
    last_month_end = prev_month_end

    # Base tenant filter for UserModel
    tenant_filter_user = (UserModel.tenant_id == tenant_id,) if tenant_id else ()

    # All user counts in a single query using conditional aggregation (5 queries → 1)
    user_stats_result = await session.execute(
        select(
            func.count(UserModel.id),
            func.sum(case((UserModel.is_active.is_(True), 1), else_=0)),
            func.sum(case((UserModel.created_at >= last_30_days, 1), else_=0)),
            func.sum(case((UserModel.created_at >= last_7_days, 1), else_=0)),
            func.sum(
                case(
                    (
                        and_(
                            UserModel.created_at >= last_month_start,
                            UserModel.created_at < last_month_end,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
        ).where(UserModel.deleted_at.is_(None), *tenant_filter_user)
    )
    user_row = user_stats_result.one()
    total_users = user_row[0] or 0
    active_users = int(user_row[1] or 0)
    inactive_users = total_users - active_users
    users_created_last_30_days = int(user_row[2] or 0)
    users_created_last_7_days = int(user_row[3] or 0)
    users_prev_30_days = int(user_row[4] or 0)

    # Total roles (scoped to tenant)
    role_tenant_filter = (RoleModel.tenant_id == tenant_id,) if tenant_id else ()
    total_roles_result = await session.execute(
        select(func.count(RoleModel.id)).where(*role_tenant_filter)
    )
    total_roles = total_roles_result.scalar() or 0

    # API key counts in a single query (2 queries → 1)
    api_key_tenant_filter = (
        (
            APIKeyModel.user_id.in_(
                select(UserModel.id).where(UserModel.tenant_id == tenant_id)
            ),
        )
        if tenant_id
        else ()
    )
    api_key_stats_result = await session.execute(
        select(
            func.count(APIKeyModel.id),
            func.sum(case((APIKeyModel.is_active.is_(True), 1), else_=0)),
        ).where(*api_key_tenant_filter)
    )
    api_key_row = api_key_stats_result.one()
    total_api_keys = api_key_row[0] or 0
    active_api_keys = int(api_key_row[1] or 0)

    # Calculate user growth percentage
    if users_prev_30_days > 0:
        user_growth = (
            (users_created_last_30_days - users_prev_30_days) / users_prev_30_days
        ) * 100
        user_change = f"{'+' if user_growth >= 0 else ''}{user_growth:.0f}%"
        user_change_type = (
            "positive"
            if user_growth > 0
            else ("negative" if user_growth < 0 else "neutral")
        )
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
            change=f"{(active_users / total_users * 100):.0f}%"
            if total_users > 0
            else "0%",
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
    limit: int = Query(default=10, ge=1, le=100),
    current_user_id: UUID = Depends(require_permission("dashboard", "read")),
    tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> RecentActivityResponse:
    """
    Get recent activity including user registrations and API key creation.
    All queries are scoped to the current tenant. PII is redacted.
    """
    activities: list[ActivityItem] = []

    # Get recent user registrations (tenant-scoped)
    user_filters = [UserModel.deleted_at.is_(None)]
    if tenant_id:
        user_filters.append(UserModel.tenant_id == tenant_id)

    recent_users_result = await session.execute(
        select(UserModel)
        .where(*user_filters)
        .order_by(UserModel.created_at.desc())
        .limit(5)
    )
    recent_users = recent_users_result.scalars().all()

    for user in recent_users:
        # Redact PII: use initials only, not full name/email
        initials = f"{(user.first_name or '?')[0]}.{(user.last_name or '?')[0]}."
        activities.append(
            ActivityItem(
                id=str(user.id),
                action="user_registered",
                description=f"New user registered: {initials}",
                timestamp=user.created_at,
                user_name=initials,
                user_email=None,  # Redacted for privacy
            )
        )

    # Get recent API key creations (tenant-scoped)
    key_query = select(APIKeyModel).order_by(APIKeyModel.created_at.desc()).limit(5)
    if tenant_id:
        key_query = key_query.where(
            APIKeyModel.user_id.in_(
                select(UserModel.id).where(UserModel.tenant_id == tenant_id)
            )
        )
    recent_keys_result = await session.execute(key_query)
    recent_keys = recent_keys_result.scalars().all()

    for key in recent_keys:
        activities.append(
            ActivityItem(
                id=str(key.id),
                action="api_key_created",
                description="New API key created",
                timestamp=key.created_at,
            )
        )

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
    current_user_id: UUID = Depends(require_permission("dashboard", "read")),
    tenant_id: CurrentTenantId = None,
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
        logger.warning("database_health_check_failed")
        db_status = "unhealthy"

    # Check Redis health and get metrics
    metrics = get_metrics_service()
    redis_healthy, _redis_response_ms = await metrics.check_redis_health()
    cache_status = "healthy" if redis_healthy else "unhealthy"

    # Get response time metrics
    response_metrics = metrics.get_response_time_metrics()
    avg_response_time = (
        response_metrics.avg_ms if response_metrics.sample_count > 0 else 0.0
    )

    # Get uptime percentage
    uptime_tracker = get_uptime_tracker()
    uptime_percentage = await uptime_tracker.get_uptime_percentage()

    # Get active sessions (count non-revoked sessions, tenant-scoped)
    session_filters = [UserSessionModel.is_revoked.is_(False)]
    if tenant_id:
        session_filters.append(
            UserSessionModel.user_id.in_(
                select(UserModel.id).where(UserModel.tenant_id == tenant_id)
            )
        )
    active_sessions_result = await session.execute(
        select(func.count(UserSessionModel.id)).where(*session_filters)
    )
    active_sessions = active_sessions_result.scalar() or 0

    return SystemHealthResponse(
        database_status=db_status,
        cache_status=cache_status,
        avg_response_time_ms=avg_response_time,
        uptime_percentage=uptime_percentage,
        active_sessions=active_sessions,
    )
