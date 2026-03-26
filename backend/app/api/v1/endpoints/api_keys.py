# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
API Key management endpoints.

Allows users to create and manage their API keys for
programmatic access to the API.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentTenantId, require_permission
from app.api.v1.schemas.api_keys import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from app.infrastructure.auth.api_key_handler import (
    create_api_key,
    list_user_api_keys,
    revoke_api_key,
)
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.observability.logging import get_logger
from app.middleware.tenant import require_tenant_context

logger = get_logger(__name__)

router = APIRouter(tags=["api-keys"])


@router.get(
    "",
    response_model=APIKeyListResponse,
    summary="List my API keys",
    description="List all API keys owned by the current user.",
)
async def list_my_api_keys(
    include_revoked: bool = Query(default=False),
    current_user_id: UUID = Depends(require_permission("api_keys", "read")),
    _tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> APIKeyListResponse:
    """List API keys for current user."""
    keys = await list_user_api_keys(
        session,
        user_id=current_user_id,
        include_revoked=include_revoked,
        tenant_id=_tenant_id,
    )

    return APIKeyListResponse(
        items=[
            APIKeyResponse(
                id=k.id,
                name=k.name,
                prefix=k.prefix,
                scopes=k.scopes,
                is_active=k.is_active,
                expires_at=k.expires_at,
                last_used_at=k.last_used_at,
                usage_count=k.usage_count,
                created_at=k.created_at,
            )
            for k in keys
        ],
        total=len(keys),
    )


@router.post(
    "",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="Create a new API key. The key is only shown once.",
)
async def create_my_api_key(
    data: APIKeyCreate,
    current_user_id: UUID = Depends(require_permission("api_keys", "write")),
    tenant_id: UUID = Depends(require_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> APIKeyCreatedResponse:
    """Create a new API key."""
    plain_key, api_key = await create_api_key(
        session,
        tenant_id=tenant_id,
        user_id=current_user_id,
        name=data.name,
        scopes=data.scopes,
        expires_in_days=data.expires_in_days,
    )

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        key=plain_key,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
    description="Revoke an API key. This action cannot be undone.",
)
async def revoke_my_api_key(
    key_id: UUID,
    current_user_id: UUID = Depends(require_permission("api_keys", "write")),
    _tenant_id: CurrentTenantId = None,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Revoke an API key."""
    revoked = await revoke_api_key(
        session,
        key_id=key_id,
        user_id=current_user_id,
        tenant_id=_tenant_id,
    )

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "API_KEY_NOT_FOUND", "message": "API key not found"},
        )
