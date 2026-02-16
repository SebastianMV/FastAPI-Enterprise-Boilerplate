# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.domain.exceptions.base import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolationError,
    ConflictError,
    DomainException,
    EntityNotFoundError,
    RateLimitExceededError,
    ServiceUnavailableError,
    ValidationError,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan handler.

    Startup: Initialize database, Redis, telemetry.
    Shutdown: Close connections gracefully.
    """
    # Startup
    from app.infrastructure.database.connection import init_database

    logger.info(
        "starting_application", app_name=settings.APP_NAME, version=settings.APP_VERSION
    )
    logger.info("environment_info", environment=settings.ENVIRONMENT)

    # Setup logging
    from app.infrastructure.observability.logging import setup_logging

    setup_logging()
    logger.info("logging_configured")

    # Setup telemetry (if enabled)
    if settings.OTEL_ENABLED:
        from app.infrastructure.observability.telemetry import setup_telemetry

        setup_telemetry()
        logger.info("opentelemetry_initialized")

    # Initialize database (runs Alembic migrations automatically)
    try:
        await init_database()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error_type=type(e).__name__)
        raise  # Fatal: do not start app without database

    # Initialize uptime tracker
    try:
        from app.infrastructure.monitoring import get_uptime_tracker

        uptime_tracker = get_uptime_tracker()
        await uptime_tracker.initialize()
        logger.info("uptime_tracker_initialized")
    except Exception as e:
        logger.warning("uptime_tracker_init_failed", error_type=type(e).__name__)

    yield

    # Shutdown
    from app.infrastructure.cache import close_cache
    from app.infrastructure.database.connection import close_database

    await close_cache()
    await close_database()
    logger.info("all_connections_closed")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## FastAPI Enterprise Boilerplate

Production-ready starter kit with:

- 🔐 **JWT Authentication** with refresh tokens
- 🛡️ **Granular ACL** - Permission-based access control
- 🏢 **Multi-Tenant (RLS)** - Data isolation at database level
- 🏗️ **Hexagonal Architecture** - Clean separation of concerns
- 📊 **OpenTelemetry** - Traces, metrics, structured logs
- ⚡ **Rate Limiting** - Redis-based API protection
- 🚀 **Background Jobs** - Async task processing

[GitHub Repository](https://github.com/SebastianMV/fastapi-enterprise-boilerplate)
    """,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ===========================================
# Middleware (order matters: last added = first executed)
# ===========================================

# CORS (outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-CSRF-Token",
        "X-Request-ID",
    ],
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Content-Language",
    ],
)

# Security Headers (second outermost - add security headers to all responses)
from app.middleware.security_headers import SecurityHeadersMiddleware

app.add_middleware(
    SecurityHeadersMiddleware,
    hsts_enabled=settings.is_production,  # Only enable HSTS in production
    hsts_max_age=31536000,  # 1 year
)

# Request ID (trace every request with a UUID)
from app.middleware.request_id import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)

# Metrics (track response times)
from app.middleware.metrics import MetricsMiddleware

app.add_middleware(MetricsMiddleware)

# CSRF Protection (double-submit cookie)
from app.middleware.csrf import CSRFMiddleware

app.add_middleware(CSRFMiddleware)

# Rate Limiting (if enabled)
if settings.RATE_LIMIT_ENABLED:
    from app.middleware.rate_limit import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware)

# Tenant Context
from app.middleware.tenant import TenantMiddleware

app.add_middleware(TenantMiddleware)

# i18n (locale detection from Accept-Language / X-Locale header)
from app.middleware.i18n import I18nMiddleware

app.add_middleware(I18nMiddleware)


# ===========================================
# Routers
# ===========================================

# Include API v1 router
app.include_router(api_router, prefix="/api/v1")


# ===========================================
# Global Exception Handlers
# ===========================================
# Maps domain exceptions to proper HTTP responses so that
# endpoints can raise domain exceptions without importing
# HTTPException, keeping the hexagonal boundary clean.


@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(
    _request: Request, exc: EntityNotFoundError
) -> JSONResponse:
    """404 — entity not found."""
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(
    _request: Request, exc: AuthenticationError
) -> JSONResponse:
    """401 — authentication failed."""
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(
    _request: Request, exc: AuthorizationError
) -> JSONResponse:
    """403 — access denied."""
    return JSONResponse(
        status_code=403,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(ConflictError)
async def conflict_error_handler(_request: Request, exc: ConflictError) -> JSONResponse:
    """409 — resource conflict / duplicate."""
    return JSONResponse(
        status_code=409,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(
    _request: Request, exc: ValidationError
) -> JSONResponse:
    """422 — domain validation failure."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.message, "code": exc.code, "field": exc.field},
    )


@app.exception_handler(BusinessRuleViolationError)
async def business_rule_error_handler(
    _request: Request, exc: BusinessRuleViolationError
) -> JSONResponse:
    """400 — business rule violated."""
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "code": exc.code, "rule": exc.rule},
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_error_handler(
    _request: Request, exc: RateLimitExceededError
) -> JSONResponse:
    """429 — rate limit exceeded."""
    return JSONResponse(
        status_code=429,
        content={"detail": exc.message, "code": exc.code},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_error_handler(
    _request: Request, exc: ServiceUnavailableError
) -> JSONResponse:
    """503 — required service unavailable."""
    return JSONResponse(
        status_code=503,
        content={"detail": exc.message, "code": exc.code},
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(
    _request: Request, exc: DomainException
) -> JSONResponse:
    """500 — catch-all for any unhandled domain exception."""
    logger.error(
        "unhandled_domain_exception",
        exception_type=type(exc).__name__,
        code=exc.code,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": exc.code},
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """500 — catch-all for completely unexpected exceptions."""
    logger.error(
        "unexpected_exception", exception_type=type(exc).__name__, exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )


# ===========================================
# Root endpoint
# ===========================================


@app.get("/", tags=["Root"])
async def root() -> dict[str, str | None]:
    """Root endpoint with API info."""
    response: dict[str, str | None] = {
        "name": settings.APP_NAME,
        "health": "/api/v1/health",
    }
    # Only expose version, environment and docs link in non-production
    if not settings.is_production:
        response["version"] = settings.APP_VERSION
        response["environment"] = settings.ENVIRONMENT
        response["docs"] = "/docs"
    return response
