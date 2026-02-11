# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Repository port (interface) for User entity.

This is a PORT in hexagonal architecture - defines the contract
that infrastructure adapters must implement.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.user import User


class UserRepositoryPort(ABC):
    """
    Abstract repository for User entity.

    Implementations:
    - SQLAlchemyUserRepository (PostgreSQL)
    - InMemoryUserRepository (Testing)
    """

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """
        Get user by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            User entity if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email address.

        Args:
            email: User's email address (case-insensitive)

        Returns:
            User entity if found, None otherwise
        """
        ...

    @abstractmethod
    async def create(self, user: User) -> User:
        """
        Create a new user.

        Args:
            user: User entity to persist

        Returns:
            Created user with generated ID

        Raises:
            ConflictError: If email already exists
        """
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        """
        Update existing user.

        Args:
            user: User entity with updated data

        Returns:
            Updated user

        Raises:
            EntityNotFoundError: If user doesn't exist
        """
        ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """
        Soft delete user by ID.

        Args:
            user_id: User's unique identifier

        Raises:
            EntityNotFoundError: If user doesn't exist
        """
        ...

    @abstractmethod
    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> list[User]:
        """
        List users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status

        Returns:
            List of users matching criteria
        """
        ...

    @abstractmethod
    async def count(self, *, is_active: bool | None = None) -> int:
        """
        Count users matching criteria.

        Args:
            is_active: Filter by active status

        Returns:
            Number of users matching criteria
        """
        ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """
        Check if user with email exists.

        Args:
            email: Email address to check

        Returns:
            True if exists, False otherwise
        """
        ...
