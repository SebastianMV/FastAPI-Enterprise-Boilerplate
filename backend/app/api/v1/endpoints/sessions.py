# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Session management endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.api.deps import CurrentTenantId, CurrentUserId, DbSession
from app.infrastructure.auth.jwt_handler import validate_access_token
from app.infrastructure.database.repositories.session_repository import (
    SQLAlchemySessionRepository,
)

router = APIRouter()

# Security scheme
security = HTTPBearer(auto_error=False)


def get_current_token_jti(
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    """Extract JTI (session ID) from the current access token."""
    if not credentials:
        return None
    try:
        payload = validate_access_token(credentials.credentials)
        return payload.get("jti")
    except Exception:
        return None


# ===========================================
# Response Schemas
# ===========================================


class SessionResponse(BaseModel):
    """Single session information."""

    id: UUID
    device_name: str = Field(max_length=200)
    device_type: str = Field(max_length=50)
    browser: str = Field(max_length=100)
    os: str = Field(max_length=100)
    ip_address: str = Field(max_length=45)
    location: str = Field(max_length=200)
    last_activity: datetime
    is_current: bool
    created_at: datetime


class SessionListResponse(BaseModel):
    """List of user sessions."""

    sessions: list[SessionResponse]
    total: int


class RevokeSessionsResponse(BaseModel):
    """Response for revoke operations."""

    message: str = Field(max_length=500)
    revoked_count: int


# ===========================================
# Endpoints
# ===========================================


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List active sessions",
    description="Get all active sessions for the current user.",
)
async def list_sessions(
    user_id: CurrentUserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> SessionListResponse:
    """
    List all active sessions for the authenticated user.

    Shows device info, location, and last activity for each session.
    The current session is marked with is_current=true.
    """
    repo = SQLAlchemySessionRepository(session)
    user_sessions = await repo.get_user_sessions(user_id, tenant_id=tenant_id)

    # Get current session ID from JWT token's jti claim
    current_token_jti = get_current_token_jti(credentials)

    sessions = [
        SessionResponse(
            id=s.id,
            device_name=s.device_name,
            device_type=s.device_type,
            browser=s.browser,
            os=s.os,
            ip_address=s.ip_address,
            location=s.location,
            last_activity=s.last_activity,
            is_current=(str(s.id) == current_token_jti) if current_token_jti else False,
            created_at=s.created_at,
        )
        for s in user_sessions
    ]

    return SessionListResponse(
        sessions=sessions,
        total=len(sessions),
    )


@router.delete(
    "/{session_id}",
    response_model=RevokeSessionsResponse,
    summary="Revoke a session",
    description="Revoke a specific session, logging out that device.",
)
async def revoke_session(
    session_id: UUID,
    user_id: CurrentUserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> RevokeSessionsResponse:
    """
    Revoke a specific session.

    This will log out the user on that specific device.
    Cannot revoke the current session (use /auth/logout instead).
    """
    # Check if trying to revoke current session using JWT's jti
    current_token_jti = get_current_token_jti(credentials)
    if current_token_jti and str(session_id) == current_token_jti:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CANNOT_REVOKE_CURRENT",
                "message": "Cannot revoke current session. Use /auth/logout instead.",
            },
        )

    repo = SQLAlchemySessionRepository(session)

    # Verify session belongs to user and tenant
    target_session = await repo.get_by_id(session_id)
    if (
        not target_session
        or target_session.user_id != user_id
        or target_session.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": "Session not found",
            },
        )

    # Revoke the session
    success = await repo.revoke(session_id)
    await session.commit()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SESSION_NOT_FOUND",
                "message": "Session not found or already revoked",
            },
        )

    return RevokeSessionsResponse(
        message="Session revoked successfully",
        revoked_count=1,
    )


@router.delete(
    "",
    response_model=RevokeSessionsResponse,
    summary="Revoke all other sessions",
    description="Revoke all sessions except the current one.",
)
async def revoke_all_sessions(
    user_id: CurrentUserId,
    tenant_id: CurrentTenantId,
    session: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> RevokeSessionsResponse:
    """
    Revoke all sessions except the current one.

    This will log out the user on all other devices.
    Useful when user suspects their account is compromised.
    """
    repo = SQLAlchemySessionRepository(session)

    # Get current session ID from JWT's jti claim
    current_token_jti = get_current_token_jti(credentials)

    if current_token_jti:
        # Try to parse as UUID, otherwise use as string
        try:
            current_uuid = UUID(current_token_jti)
            count = await repo.revoke_all_except(user_id, current_uuid, tenant_id=tenant_id)
        except ValueError:
            # If jti is not a valid UUID, only skip it (don't revoke all blindly)
            count = await repo.revoke_all(user_id, tenant_id=tenant_id)
    else:
        count = await repo.revoke_all(user_id, tenant_id=tenant_id)

    await session.commit()

    return RevokeSessionsResponse(
        message=f"Successfully revoked {count} session(s)",
        revoked_count=count,
    )
