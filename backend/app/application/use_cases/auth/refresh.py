# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Refresh token use case.

Handles token refresh flow.
"""

from dataclasses import dataclass
from uuid import UUID

from app.domain.exceptions.base import AuthenticationError
from app.domain.ports.user_repository import UserRepositoryPort
from app.infrastructure.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    validate_refresh_token,
)


@dataclass
class RefreshRequest:
    """Refresh token request."""
    
    refresh_token: str


@dataclass
class RefreshResponse:
    """Refresh token response."""
    
    access_token: str
    refresh_token: str


class RefreshTokenUseCase:
    """
    Use case for refreshing access tokens.
    
    Validates refresh token and issues new tokens.
    """
    
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        """
        Initialize use case.
        
        Args:
            user_repository: Repository for user data access
        """
        self._user_repository = user_repository
    
    async def execute(self, request: RefreshRequest) -> RefreshResponse:
        """
        Execute token refresh flow.
        
        Args:
            request: Refresh token request
            
        Returns:
            RefreshResponse with new tokens
            
        Raises:
            AuthenticationError: If refresh token is invalid or user is inactive
        """
        # 1. Validate refresh token
        try:
            payload = validate_refresh_token(request.refresh_token)
        except AuthenticationError:
            raise AuthenticationError(
                message="Invalid or expired refresh token",
                code="INVALID_REFRESH_TOKEN",
            )
        
        # 2. Extract user info from token
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"]) if payload.get("tenant_id") else None
        
        # 3. Verify user still exists and is active
        user = await self._user_repository.get_by_id(user_id)
        
        if not user:
            raise AuthenticationError(
                message="User not found",
                code="USER_NOT_FOUND",
            )
        
        if not user.is_active:
            raise AuthenticationError(
                message="User account is deactivated",
                code="ACCOUNT_INACTIVE",
            )
        
        # 4. Generate new tokens
        new_access_token = create_access_token(
            user_id=user_id,
            tenant_id=tenant_id or user.tenant_id,
            extra_claims={"is_superuser": user.is_superuser},
        )
        
        # Rotate refresh token
        new_refresh_token = create_refresh_token(
            user_id=user_id,
            tenant_id=tenant_id or user.tenant_id,
        )
        
        return RefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )
