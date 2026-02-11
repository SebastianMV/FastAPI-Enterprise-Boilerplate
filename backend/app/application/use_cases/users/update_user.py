# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Update user use case.

Handles updating an existing user's profile data.
"""

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.user import User
from app.domain.exceptions.base import (
    ConflictError,
    EntityNotFoundError,
    ValidationError,
)
from app.domain.ports.user_repository import UserRepositoryPort
from app.domain.value_objects.email import Email


@dataclass
class UpdateUserRequest:
    """Update user request data."""

    user_id: UUID
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None
    roles: list[UUID] | None = None
    updated_by: UUID | None = None


@dataclass
class UpdateUserResponse:
    """Update user response."""

    user: User


class UpdateUserUseCase:
    """
    Use case for updating an existing user.

    Validates input, checks for conflicts, and persists changes.
    """

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        """
        Initialize use case.

        Args:
            user_repository: Repository for user data access
        """
        self._user_repository = user_repository

    async def execute(self, request: UpdateUserRequest) -> UpdateUserResponse:
        """
        Execute update user flow.

        Args:
            request: User update data (only non-None fields are updated)

        Returns:
            UpdateUserResponse with the updated user

        Raises:
            EntityNotFoundError: If user does not exist
            ValidationError: If new email is invalid
            ConflictError: If new email already belongs to another user
        """
        # 1. Fetch existing user
        user = await self._user_repository.get_by_id(request.user_id)

        if not user:
            raise EntityNotFoundError(
                entity_type="User",
                entity_id=str(request.user_id),
            )

        # 2. Update email (if provided)
        if request.email is not None:
            try:
                email = Email(request.email)
            except ValueError:
                raise ValidationError(
                    message="Invalid email format",
                    field="email",
                    code="INVALID_EMAIL",
                ) from None

            # Check for duplicate (only if email actually changed)
            if email != user.email:
                if await self._user_repository.exists_by_email(email.value):
                    raise ConflictError(
                        message="A user with this email already exists",
                        code="EMAIL_EXISTS",
                    )
                user.email = email

        # 3. Update name fields (if provided)
        if request.first_name is not None:
            user.first_name = request.first_name

        if request.last_name is not None:
            user.last_name = request.last_name

        # 4. Update active status (if provided)
        if request.is_active is not None:
            if request.is_active:
                user.activate()
            else:
                user.deactivate()

        # 5. Update roles (if provided)
        if request.roles is not None:
            user.roles = request.roles

        # 6. Mark updated
        if request.updated_by is not None:
            user.mark_updated(by_user=request.updated_by)

        # 7. Persist
        updated_user = await self._user_repository.update(user)

        return UpdateUserResponse(user=updated_user)
