# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Tenant context middleware for multi-tenant isolation (Pure ASGI).

This middleware:
1. Extracts tenant_id from JWT token
2. Sets PostgreSQL session variable for RLS
3. Provides tenant context to request state
"""

from contextvars import ContextVar
from uuid import UUID

from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.infrastructure.auth.jwt_handler import decode_token

# Context variable for current tenant (thread-safe)
_current_tenant_id: ContextVar[UUID | None] = ContextVar(
    "current_tenant_id",
    default=None,
)


def get_current_tenant_id() -> UUID | None:
    """
    Get current tenant ID from context.

    Returns:
        Current tenant UUID or None if not in tenant context
    """
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id: UUID | None) -> None:
    """
    Set current tenant ID in context.

    Args:
        tenant_id: Tenant UUID to set
    """
    _current_tenant_id.set(tenant_id)


class TenantMiddleware:
    """
    Pure ASGI Middleware that extracts tenant context from JWT and sets RLS variable.

    The middleware:
    1. Checks for Authorization header with Bearer token
    2. Decodes JWT and extracts tenant_id claim
    3. Sets context variable for application code

    Note: The actual PostgreSQL RLS variable is set in the database
    session factory (connection.py) using the context variable.
    """

    # Paths that don't require tenant context
    EXEMPT_PATHS = {
        "/",
        "/health",
        "/health/live",
        "/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    }

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI interface - set tenant context for HTTP requests."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip exempt paths
        if self._is_exempt_path(path):
            await self.app(scope, receive, send)
            return

        # Extract tenant from token
        tenant_id = self._extract_tenant_id(scope)

        # Set context variable
        token = _current_tenant_id.set(tenant_id)

        try:
            await self.app(scope, receive, send)
        finally:
            _current_tenant_id.reset(token)

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from tenant context."""
        # Exact match
        if path in self.EXEMPT_PATHS:
            return True

        # Prefix match for static files and docs
        exempt_prefixes = ("/static/", "/docs/", "/redoc/")
        return any(path.startswith(prefix) for prefix in exempt_prefixes)

    def _extract_tenant_id(self, scope: Scope) -> UUID | None:
        """Extract tenant_id from JWT token in Authorization header or cookie."""
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()

        token: str | None = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
        else:
            # Fallback: read access_token from HttpOnly cookie
            cookie_header = headers.get(b"cookie", b"").decode()
            if cookie_header:
                for part in cookie_header.split(";"):
                    part = part.strip()
                    if part.startswith("access_token="):
                        token = part[len("access_token=") :]
                        break

        if not token:
            return None

        try:
            payload = decode_token(token)
            tenant_id_str = payload.get("tenant_id")

            if tenant_id_str:
                return UUID(tenant_id_str)

            return None
        except Exception:
            # Token invalid or expired - let auth middleware handle it
            return None


class TenantContextManager:
    """
    Context manager for setting tenant context programmatically.

    Useful for background tasks, CLI commands, or tests.

    Usage:
        async with TenantContextManager(tenant_id):
            # All database operations will be scoped to tenant
            await some_repository.get_all()
    """

    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self._token = None

    async def __aenter__(self):
        """Set tenant context on enter."""
        self._token = _current_tenant_id.set(self.tenant_id)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Reset tenant context on exit."""
        if self._token is not None:
            _current_tenant_id.reset(self._token)
        return False


def require_tenant_context(request: Request) -> UUID:
    """
    FastAPI dependency that requires tenant context.

    Usage:
        @router.get("/items")
        async def get_items(tenant_id: UUID = Depends(require_tenant_context)):
            ...

    Raises:
        HTTPException: 400 if no tenant context
    """
    from fastapi import HTTPException

    tenant_id = get_current_tenant_id()

    if tenant_id is None:
        # Try request.state as fallback
        tenant_id = getattr(request.state, "tenant_id", None)

    if tenant_id is None:
        raise HTTPException(
            status_code=400,
            detail="Tenant context required",
        )

    return tenant_id
