# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Configuration endpoints for feature flags and settings."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.api.deps import get_current_user

router = APIRouter()


class FeatureConfigResponse(BaseModel):
    """Feature configuration response."""
    
    websocket_enabled: bool
    websocket_notifications: bool


@router.get("/features", response_model=FeatureConfigResponse)
async def get_feature_config(
    current_user: Any = Depends(get_current_user)
) -> FeatureConfigResponse:
    """
    Get current feature configuration.
    
    Returns the status of optional features like chat, websocket, etc.
    """
    return FeatureConfigResponse(
        websocket_enabled=settings.WEBSOCKET_ENABLED,
        websocket_notifications=settings.WEBSOCKET_NOTIFICATIONS,
    )
