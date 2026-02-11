# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Get user use case.

Retrieves a user by ID from the repository.
"""

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.user import User
from app.domain.exceptions.base import EntityNotFoundError
from app.domain.ports.user_repository import UserRepositoryPort


@dataclass
class GetUserRequest:
    """Get user request data."""

    user_id: UUID


@dataclass
class GetUserResponse:
    """Get user response."""

    user: User


class GetUserUseCase:
    """
    Use case for retrieving a user by ID.

    Follows the hexagonal architecture pattern with
    request/response dataclasses and a single `execute` method.
    """

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        """
        Initialize use case.

        Args:
            user_repository: Repository for user data access
        """
        self._user_repository = user_repository

    async def execute(self, request: GetUserRequest) -> GetUserResponse:
        """
        Execute get user flow.

        Args:
            request: Get user request with user_id

        Returns:
            GetUserResponse with the user entity

        Raises:
            EntityNotFoundError: If user does not exist
        """
        user = await self._user_repository.get_by_id(request.user_id)

        if not user:
            raise EntityNotFoundError(
                entity_type="User",
                entity_id=str(request.user_id),
            )

        return GetUserResponse(user=user)
