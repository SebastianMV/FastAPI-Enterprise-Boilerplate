# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Register user use case.

Handles user registration with validation.
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.entities.user import User
from app.domain.exceptions.base import ConflictError, ValidationError
from app.domain.ports.user_repository import UserRepositoryPort
from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password
from app.infrastructure.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    hash_password,
)


@dataclass
class RegisterRequest:
    """Registration request data."""
    
    email: str
    password: str
    first_name: str
    last_name: str
    tenant_id: UUID | None = None


@dataclass
class RegisterResponse:
    """Registration response with tokens and user."""
    
    access_token: str
    refresh_token: str
    user: User


class RegisterUseCase:
    """
    Use case for user registration.
    
    Validates input, creates user, and returns tokens.
    """
    
    def __init__(self, user_repository: UserRepositoryPort) -> None:
        """
        Initialize use case.
        
        Args:
            user_repository: Repository for user data access
        """
        self._user_repository = user_repository
    
    async def execute(self, request: RegisterRequest) -> RegisterResponse:
        """
        Execute registration flow.
        
        Args:
            request: Registration data
            
        Returns:
            RegisterResponse with tokens and user
            
        Raises:
            ValidationError: If email or password is invalid
            ConflictError: If email already exists
        """
        # 1. Validate email
        try:
            email = Email(request.email)
        except ValueError as e:
            raise ValidationError(
                message=str(e),
                field="email",
            )
        
        # 2. Validate password
        try:
            password = Password(request.password)
        except ValueError as e:
            raise ValidationError(
                message=str(e),
                field="password",
            )
        
        # 3. Check email uniqueness
        if await self._user_repository.exists_by_email(request.email):
            raise ConflictError(
                message=f"Email '{request.email}' is already registered",
                conflicting_field="email",
            )
        
        # 4. Create user entity
        tenant_id = request.tenant_id or uuid4()
        
        user = User(
            id=uuid4(),
            tenant_id=tenant_id,
            email=email,
            password_hash=hash_password(password.value),
            first_name=request.first_name,
            last_name=request.last_name,
            is_active=True,
            is_superuser=False,
        )
        
        # 5. Persist user
        created_user = await self._user_repository.create(user)
        
        # 6. Generate tokens
        access_token = create_access_token(
            user_id=created_user.id,
            tenant_id=tenant_id,
        )
        
        refresh_token = create_refresh_token(
            user_id=created_user.id,
            tenant_id=tenant_id,
        )
        
        return RegisterResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=created_user,
        )
