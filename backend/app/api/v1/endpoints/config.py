# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""Configuration endpoints for feature flags and settings."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from uuid import UUID

from app.api.deps import CurrentTenantId, get_current_user, require_permission
from app.config import settings
from app.domain.entities.user import User

router = APIRouter()


class FeatureConfigResponse(BaseModel):
    """Feature configuration response."""

    websocket_enabled: bool
    websocket_notifications: bool


@router.get("/features", response_model=FeatureConfigResponse)
async def get_feature_config(
    current_user: User = Depends(get_current_user),
    _user_id: UUID = Depends(require_permission("config", "read")),
    tenant_id: CurrentTenantId = None,
) -> FeatureConfigResponse:
    """
    Get current feature configuration.

    Returns the status of optional features like chat, websocket, etc.
    """
    return FeatureConfigResponse(
        websocket_enabled=settings.WEBSOCKET_ENABLED,
        websocket_notifications=settings.WEBSOCKET_NOTIFICATIONS,
    )
