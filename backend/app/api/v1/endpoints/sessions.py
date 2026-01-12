# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Session management endpoints."""

from datetime import datetime, UTC
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Request, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, CurrentUserId, DbSession
from app.infrastructure.database.repositories.session_repository import SQLAlchemySessionRepository


router = APIRouter()


# ===========================================
# Response Schemas
# ===========================================

class SessionResponse(BaseModel):
    """Single session information."""
    
    id: UUID
    device_name: str
    device_type: str
    browser: str
    os: str
    ip_address: str
    location: str
    last_activity: datetime
    is_current: bool
    created_at: datetime


class SessionListResponse(BaseModel):
    """List of user sessions."""
    
    sessions: list[SessionResponse]
    total: int


class RevokeSessionsResponse(BaseModel):
    """Response for revoke operations."""
    
    message: str
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
    session: DbSession,
    request: Request,
) -> SessionListResponse:
    """
    List all active sessions for the authenticated user.
    
    Shows device info, location, and last activity for each session.
    The current session is marked with is_current=true.
    """
    repo = SQLAlchemySessionRepository(session)
    user_sessions = await repo.get_user_sessions(user_id)
    
    # Get current session ID from request state if available
    current_session_id = getattr(request.state, "session_id", None)
    
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
            is_current=(str(s.id) == str(current_session_id)) if current_session_id else False,
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
    session: DbSession,
    request: Request,
) -> RevokeSessionsResponse:
    """
    Revoke a specific session.
    
    This will log out the user on that specific device.
    Cannot revoke the current session (use /auth/logout instead).
    """
    # Check if trying to revoke current session
    current_session_id = getattr(request.state, "session_id", None)
    if current_session_id and str(session_id) == str(current_session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CANNOT_REVOKE_CURRENT",
                "message": "Cannot revoke current session. Use /auth/logout instead.",
            },
        )
    
    repo = SQLAlchemySessionRepository(session)
    
    # Verify session belongs to user
    target_session = await repo.get_by_id(session_id)
    if not target_session or target_session.user_id != user_id:
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
    session: DbSession,
    request: Request,
) -> RevokeSessionsResponse:
    """
    Revoke all sessions except the current one.
    
    This will log out the user on all other devices.
    Useful when user suspects their account is compromised.
    """
    repo = SQLAlchemySessionRepository(session)
    
    # Get current session ID
    current_session_id = getattr(request.state, "session_id", None)
    
    if current_session_id:
        count = await repo.revoke_all_except(user_id, UUID(str(current_session_id)))
    else:
        count = await repo.revoke_all(user_id)
    
    await session.commit()
    
    return RevokeSessionsResponse(
        message=f"Successfully revoked {count} session(s)",
        revoked_count=count,
    )
