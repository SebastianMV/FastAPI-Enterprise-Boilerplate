# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Audit Log endpoints.

Provides read-only access to audit log entries for compliance and security monitoring.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentTenantId, CurrentUserId
from app.api.v1.schemas.audit_logs import (
    AuditLogListResponse,
    AuditLogResponse,
    AuditLogStatsResponse,
)
from app.domain.entities.audit_log import AuditAction, AuditResourceType
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.audit_log_repository import (
    SQLAlchemyAuditLogRepository,
)

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def get_audit_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyAuditLogRepository:
    """Dependency to get audit log repository."""
    return SQLAlchemyAuditLogRepository(session)


def _to_response(log) -> AuditLogResponse:
    """Convert audit log entity to response schema."""
    return AuditLogResponse(
        id=log.id,
        timestamp=log.timestamp,
        action=log.action.value if hasattr(log.action, 'value') else log.action,
        resource_type=log.resource_type.value if hasattr(log.resource_type, 'value') else log.resource_type,
        resource_id=log.resource_id,
        resource_name=log.resource_name,
        actor_id=log.actor_id,
        actor_email=log.actor_email,
        actor_ip=log.actor_ip,
        actor_user_agent=log.actor_user_agent,
        tenant_id=log.tenant_id,
        old_value=log.old_value,
        new_value=log.new_value,
        metadata=log.metadata or {},
        reason=log.reason,
    )


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="List audit logs",
    description="List audit logs for the current tenant with optional filters.",
)
async def list_audit_logs(
    current_user_id: CurrentUserId,
    tenant_id: CurrentTenantId,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    action: Optional[str] = Query(default=None, description="Filter by action type"),
    resource_type: Optional[str] = Query(default=None, description="Filter by resource type"),
    start_date: Optional[datetime] = Query(default=None, description="Filter from this date"),
    end_date: Optional[datetime] = Query(default=None, description="Filter until this date"),
    repo: SQLAlchemyAuditLogRepository = Depends(get_audit_repository),
) -> AuditLogListResponse:
    """List audit logs for the current tenant."""
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_TENANT", "message": "Tenant context required"},
        )
    
    # Parse action if provided
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ACTION", "message": f"Invalid action: {action}"},
            )
    
    # Parse resource_type if provided
    resource_type_enum = None
    if resource_type:
        try:
            resource_type_enum = AuditResourceType(resource_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_RESOURCE_TYPE", "message": f"Invalid resource type: {resource_type}"},
            )
    
    logs = await repo.list_by_tenant(
        tenant_id=tenant_id,
        limit=limit,
        offset=skip,
        action=action_enum,
        resource_type=resource_type_enum,
        start_date=start_date,
        end_date=end_date,
    )
    
    total = await repo.count_by_tenant(
        tenant_id=tenant_id,
        action=action_enum,
        resource_type=resource_type_enum,
        start_date=start_date,
        end_date=end_date,
    )
    
    return AuditLogListResponse(
        items=[_to_response(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/my-activity",
    response_model=AuditLogListResponse,
    summary="Get my activity",
    description="Get audit logs for the current user's actions.",
)
async def get_my_activity(
    current_user_id: CurrentUserId,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    repo: SQLAlchemyAuditLogRepository = Depends(get_audit_repository),
) -> AuditLogListResponse:
    """Get audit logs for the current user."""
    logs = await repo.list_by_actor(
        actor_id=current_user_id,
        limit=limit,
        offset=skip,
        start_date=start_date,
        end_date=end_date,
    )
    
    return AuditLogListResponse(
        items=[_to_response(log) for log in logs],
        total=len(logs),  # Simplified - would need count method for accuracy
        skip=skip,
        limit=limit,
    )


@router.get(
    "/recent-logins",
    response_model=AuditLogListResponse,
    summary="Get recent logins",
    description="Get recent login attempts for the tenant.",
)
async def get_recent_logins(
    current_user_id: CurrentUserId,
    tenant_id: CurrentTenantId,
    limit: int = Query(default=50, ge=1, le=100),
    include_failed: bool = Query(default=True, description="Include failed login attempts"),
    repo: SQLAlchemyAuditLogRepository = Depends(get_audit_repository),
) -> AuditLogListResponse:
    """Get recent login attempts."""
    logs = await repo.list_recent_logins(
        tenant_id=tenant_id,
        limit=limit,
        include_failed=include_failed,
    )
    
    return AuditLogListResponse(
        items=[_to_response(log) for log in logs],
        total=len(logs),
        skip=0,
        limit=limit,
    )


@router.get(
    "/resource/{resource_type}/{resource_id}",
    response_model=AuditLogListResponse,
    summary="Get resource history",
    description="Get audit log history for a specific resource.",
)
async def get_resource_history(
    resource_type: str,
    resource_id: str,
    current_user_id: CurrentUserId,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    repo: SQLAlchemyAuditLogRepository = Depends(get_audit_repository),
) -> AuditLogListResponse:
    """Get audit log history for a specific resource."""
    try:
        resource_type_enum = AuditResourceType(resource_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RESOURCE_TYPE", "message": f"Invalid resource type: {resource_type}"},
        )
    
    logs = await repo.list_by_resource(
        resource_type=resource_type_enum,
        resource_id=resource_id,
        limit=limit,
        offset=skip,
    )
    
    return AuditLogListResponse(
        items=[_to_response(log) for log in logs],
        total=len(logs),
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{audit_id}",
    response_model=AuditLogResponse,
    summary="Get audit log by ID",
    description="Get a specific audit log entry by ID.",
)
async def get_audit_log(
    audit_id: UUID,
    current_user_id: CurrentUserId,
    repo: SQLAlchemyAuditLogRepository = Depends(get_audit_repository),
) -> AuditLogResponse:
    """Get a specific audit log entry."""
    log = await repo.get_by_id(audit_id)
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Audit log {audit_id} not found"},
        )
    
    return _to_response(log)


@router.get(
    "/actions/list",
    response_model=list[str],
    summary="List available actions",
    description="Get list of all available audit action types.",
)
async def list_actions(
    current_user_id: CurrentUserId,
) -> list[str]:
    """Get list of available audit actions."""
    return [action.value for action in AuditAction]


@router.get(
    "/resource-types/list",
    response_model=list[str],
    summary="List resource types",
    description="Get list of all available resource types.",
)
async def list_resource_types(
    current_user_id: CurrentUserId,
) -> list[str]:
    """Get list of available resource types."""
    return [rt.value for rt in AuditResourceType]
