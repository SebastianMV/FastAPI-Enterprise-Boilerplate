# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Tenant context middleware for multi-tenant isolation.

This middleware:
1. Extracts tenant_id from JWT token
2. Sets PostgreSQL session variable for RLS
3. Provides tenant context to request state
"""

from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.infrastructure.auth.jwt_handler import decode_token

# Context variable for current tenant (thread-safe)
_current_tenant_id: ContextVar[Optional[UUID]] = ContextVar(
    "current_tenant_id",
    default=None,
)


def get_current_tenant_id() -> Optional[UUID]:
    """
    Get current tenant ID from context.
    
    Returns:
        Current tenant UUID or None if not in tenant context
    """
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id: Optional[UUID]) -> None:
    """
    Set current tenant ID in context.
    
    Args:
        tenant_id: Tenant UUID to set
    """
    _current_tenant_id.set(tenant_id)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts tenant context from JWT and sets RLS variable.
    
    Usage:
        app.add_middleware(TenantMiddleware)
    
    The middleware:
    1. Checks for Authorization header with Bearer token
    2. Decodes JWT and extracts tenant_id claim
    3. Sets context variable for application code
    4. Request.state.tenant_id is also set for convenience
    
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
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request and set tenant context."""
        
        # Skip exempt paths
        if self._is_exempt_path(request.url.path):
            return await call_next(request)
        
        # Extract tenant from token
        tenant_id = self._extract_tenant_id(request)
        
        # Set context variable
        token = _current_tenant_id.set(tenant_id)
        
        try:
            # Also set on request.state for convenience
            request.state.tenant_id = tenant_id
            
            # Process request
            response = await call_next(request)
            return response
        finally:
            # Reset context variable
            _current_tenant_id.reset(token)
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from tenant context."""
        # Exact match
        if path in self.EXEMPT_PATHS:
            return True
        
        # Prefix match for static files and docs
        exempt_prefixes = ("/static/", "/docs/", "/redoc/")
        return any(path.startswith(prefix) for prefix in exempt_prefixes)
    
    def _extract_tenant_id(self, request: Request) -> Optional[UUID]:
        """Extract tenant_id from JWT token in Authorization header."""
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
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
