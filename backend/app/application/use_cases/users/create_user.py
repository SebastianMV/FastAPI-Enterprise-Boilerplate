# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Create user use case.

Handles user creation with validation.
"""

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.user import User
from app.domain.exceptions.base import ConflictError, ValidationError
from app.domain.ports.user_repository import UserRepositoryPort
from app.domain.value_objects.email import Email
from app.domain.value_objects.password import Password
from app.infrastructure.auth.jwt_handler import hash_password


@dataclass
class CreateUserRequest:
    """Create user request data."""

    email: str
    password: str
    first_name: str
    last_name: str
    tenant_id: UUID | None = None
    is_active: bool = True
    is_superuser: bool = False
    roles: list[UUID] | None = None
    created_by: UUID | None = None


@dataclass
class CreateUserResponse:
    """Create user response."""

    user: User


class CreateUserUseCase:
    """
    Use case for creating a new user.

    Validates input, checks for duplicates, and persists the user.
    """

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        """
        Initialize use case.

        Args:
            user_repository: Repository for user data access
        """
        self._user_repository = user_repository

    async def execute(self, request: CreateUserRequest) -> CreateUserResponse:
        """
        Execute create user flow.

        Args:
            request: User creation data

        Returns:
            CreateUserResponse with the created user

        Raises:
            ValidationError: If email or password is invalid
            ConflictError: If email already exists
        """
        # 1. Validate email
        try:
            email = Email(request.email)
        except (ValueError, ValidationError):
            raise ValidationError(
                message="Invalid email format",
                field="email",
                code="INVALID_EMAIL",
            ) from None

        # 2. Validate password
        try:
            password = Password(request.password)
        except (ValueError, ValidationError):
            raise ValidationError(
                message="Password does not meet security requirements",
                field="password",
                code="INVALID_PASSWORD",
            ) from None

        # 2b. Validate name lengths (defense-in-depth)
        if not request.first_name or len(request.first_name) > 200:
            raise ValidationError(
                message="First name must be between 1 and 200 characters",
                field="first_name",
                code="INVALID_FIRST_NAME",
            )
        if not request.last_name or len(request.last_name) > 200:
            raise ValidationError(
                message="Last name must be between 1 and 200 characters",
                field="last_name",
                code="INVALID_LAST_NAME",
            )

        # 3. Check for duplicate email
        if await self._user_repository.exists_by_email(email.value):
            raise ConflictError(
                message="A user with this email already exists",
                code="EMAIL_EXISTS",
            )

        # 4. Create user entity
        user = User.create(
            email=email.value,
            first_name=request.first_name,
            last_name=request.last_name,
            tenant_id=request.tenant_id,
        )

        # 5. Set password hash
        user.set_password(password, hash_password)

        # 6. Set active status
        if not request.is_active:
            user.deactivate()

        # 7. Set superuser flag
        if request.is_superuser:
            user.is_superuser = True

        # 8. Set roles
        if request.roles:
            user.roles = request.roles

        # 9. Set created_by
        if request.created_by:
            user.created_by = request.created_by

        # 10. Persist
        created_user = await self._user_repository.create(user)

        return CreateUserResponse(user=created_user)
