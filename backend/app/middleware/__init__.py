# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Middleware package."""

from app.middleware.rate_limit import (
    InMemoryRateLimiter,
    RateLimitMiddleware,
    rate_limit,
)
from app.middleware.tenant import (
    TenantContextManager,
    TenantMiddleware,
    get_current_tenant_id,
    require_tenant_context,
    set_current_tenant_id,
)
from app.middleware.metrics import (
    MetricsMiddleware,
)

__all__ = [
    # Tenant
    "TenantMiddleware",
    "TenantContextManager",
    "get_current_tenant_id",
    "set_current_tenant_id",
    "require_tenant_context",
    # Rate Limit
    "RateLimitMiddleware",
    "InMemoryRateLimiter",
    "rate_limit",
    # Metrics
    "MetricsMiddleware",
]
