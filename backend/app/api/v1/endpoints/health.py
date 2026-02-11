# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Health check endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app.api.v1.schemas.common import HealthResponse
from app.config import settings

router = APIRouter()


def _health_base_fields() -> dict[str, str]:
    """Return version and environment only in non-production."""
    if settings.is_production:
        return {}
    return {
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check application health status.",
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """
    Basic health check for load balancers.

    Returns application status and version.
    """
    return HealthResponse(
        status="healthy",
        **_health_base_fields(),
    )


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    summary="Readiness check",
    description="Check if application is ready to receive traffic.",
    tags=["Health"],
)
async def readiness_check() -> HealthResponse:
    """
    Kubernetes readiness probe.

    Checks:
    - Database connection
    - Redis connection
    """
    from app.infrastructure.monitoring import get_metrics_service, get_uptime_tracker

    # Check Redis health
    metrics = get_metrics_service()
    redis_healthy, redis_response_ms = await metrics.check_redis_health()
    redis_status = "healthy" if redis_healthy else "unhealthy"

    # Record health ping for uptime tracking
    uptime_tracker = get_uptime_tracker()
    await uptime_tracker.record_ping(redis_healthy)

    # Check database health with a real query
    db_healthy = True
    try:
        from app.infrastructure.database.connection import async_session_maker

        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_healthy = False
        db_status = "unhealthy"

    overall_status = "ready" if (redis_healthy and db_healthy) else "degraded"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        redis=redis_status,
        **_health_base_fields(),
    )


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="Liveness check",
    description="Check if application is alive.",
    tags=["Health"],
)
async def liveness_check() -> HealthResponse:
    """
    Kubernetes liveness probe.

    Simple check that application process is running.
    """
    return HealthResponse(
        status="alive",
        **_health_base_fields(),
    )
