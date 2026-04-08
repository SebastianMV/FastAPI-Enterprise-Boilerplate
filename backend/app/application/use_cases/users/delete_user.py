# Copyright (c) 2025-2026 Sebastian Munoz
# Licensed under the Apache License, Version 2.0

"""
Delete user use case.

Handles soft-deleting a user and invalidating their active sessions.
"""

from dataclasses import dataclass
from uuid import UUID

from app.domain.exceptions.base import EntityNotFoundError
from app.domain.ports.session_repository import SessionRepositoryPort
from app.domain.ports.user_repository import UserRepositoryPort
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeleteUserRequest:
    """Delete user request data."""

    user_id: UUID
    tenant_id: UUID | None = None


class DeleteUserUseCase:
    """
    Use case for deleting (soft-delete) a user.

    Verifies the user exists before deletion and invalidates all active sessions.
    """

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        session_repository: SessionRepositoryPort | None = None,
    ) -> None:
        """
        Initialize use case.

        Args:
            user_repository: Repository for user data access
            session_repository: Repository for session management (optional)
        """
        self._user_repository = user_repository
        self._session_repository = session_repository

    async def execute(self, request: DeleteUserRequest) -> None:
        """
        Execute delete user flow.

        Args:
            request: Delete user request with user_id

        Raises:
            EntityNotFoundError: If user does not exist
        """
        # 1. Verify user exists
        user = await self._user_repository.get_by_id(request.user_id)

        if not user:
            raise EntityNotFoundError(
                entity_type="User",
                entity_id=str(request.user_id),
            )

        # 1b. Defense-in-depth: verify tenant isolation
        if request.tenant_id and user.tenant_id and user.tenant_id != request.tenant_id:
            raise EntityNotFoundError(
                entity_type="User",
                entity_id=str(request.user_id),
            )

        # 2. Invalidate all active sessions
        if self._session_repository:
            await self._session_repository.revoke_all(request.user_id)

        # 3. Soft delete
        await self._user_repository.delete(request.user_id)

        logger.info(
            "user_deleted",
            user_id=str(request.user_id),
            tenant_id=str(request.tenant_id) if request.tenant_id else None,
        )
