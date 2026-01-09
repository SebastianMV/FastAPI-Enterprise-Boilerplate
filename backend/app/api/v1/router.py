# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""API v1 router aggregation."""

from fastapi import APIRouter

from app.config import settings
from app.api.v1.endpoints import (
    api_keys,
    auth,
    chat,
    config,
    dashboard,
    health,
    mfa,
    notifications,
    oauth,
    roles,
    search,
    tenants,
    users,
)

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    mfa.router,
    tags=["Multi-Factor Authentication"],
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

api_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["Roles & ACL"],
)

api_router.include_router(
    tenants.router,
    prefix="",
    tags=["Tenants"],
)

api_router.include_router(
    api_keys.router,
    prefix="/api-keys",
    tags=["API Keys"],
)

api_router.include_router(
    health.router,
    prefix="",
    tags=["Health"],
)

# Dashboard endpoints
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)

# OAuth2/SSO endpoints
api_router.include_router(
    oauth.router,
    tags=["OAuth"],
)

# Full-Text Search endpoints
api_router.include_router(
    search.router,
    tags=["Search"],
)

# Configuration endpoints (feature flags, settings)
api_router.include_router(
    config.router,
    prefix="/config",
    tags=["Configuration"],
)

# WebSocket router (if enabled)
if settings.WEBSOCKET_ENABLED:
    from app.api.v1.endpoints import websocket
    
    api_router.include_router(
        websocket.router,
        tags=["WebSocket"],
    )

# Chat endpoints (if chat feature is enabled)
if settings.CHAT_ENABLED:
    api_router.include_router(
        chat.router,
        tags=["Chat"],
    )

# Notifications endpoints (if WebSocket notifications is enabled)
if settings.WEBSOCKET_ENABLED and settings.WEBSOCKET_NOTIFICATIONS:
    api_router.include_router(
        notifications.router,
        tags=["Notifications"],
    )
