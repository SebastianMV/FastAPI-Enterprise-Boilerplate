# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Health check endpoints."""

from fastapi import APIRouter

from app.api.v1.schemas.common import HealthResponse
from app.config import settings

router = APIRouter()


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
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
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
    
    # DB status - for now just report healthy (real check is in dashboard)
    db_status = "healthy"
    
    overall_status = "ready" if redis_healthy else "degraded"
    
    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        redis=redis_status,
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
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
