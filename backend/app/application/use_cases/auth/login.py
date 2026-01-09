# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Login use case.

Handles user authentication and token generation.
"""

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.user import User
from app.domain.exceptions.base import AuthenticationError
from app.domain.ports.user_repository import UserRepositoryPort
from app.infrastructure.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_password,
)


@dataclass
class LoginRequest:
    """Login request data."""
    
    email: str
    password: str


@dataclass
class LoginResponse:
    """Login response with tokens."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID | None = None
    tenant_id: UUID | None = None


class LoginUseCase:
    """
    Use case for user login.
    
    Validates credentials and returns authentication tokens.
    """
    
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        """
        Initialize use case.
        
        Args:
            user_repository: Repository for user data access
        """
        self._user_repository = user_repository
    
    async def execute(self, request: LoginRequest) -> LoginResponse:
        """
        Execute login flow.
        
        Args:
            request: Login credentials
            
        Returns:
            LoginResponse with tokens
            
        Raises:
            AuthenticationError: If credentials are invalid
        """
        # 1. Get user by email
        user = await self._user_repository.get_by_email(request.email)
        
        if not user:
            raise AuthenticationError(
                message="Invalid email or password",
                code="INVALID_CREDENTIALS",
            )
        
        # 2. Check if user is active
        if not user.is_active:
            raise AuthenticationError(
                message="Account is deactivated",
                code="ACCOUNT_INACTIVE",
            )
        
        # 3. Verify password
        if not verify_password(request.password, user.password_hash):
            raise AuthenticationError(
                message="Invalid email or password",
                code="INVALID_CREDENTIALS",
            )
        
        # 4. Generate tokens
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            extra_claims={
                "is_superuser": user.is_superuser,
            },
        )
        
        refresh_token = create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
        )
        
        # 5. Record login
        user.record_login()
        await self._user_repository.update(user)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            tenant_id=user.tenant_id,
        )
