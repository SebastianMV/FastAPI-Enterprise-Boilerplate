# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for authentication use cases.

Tests for Login, Register, and Refresh token use cases.
"""

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.use_cases.auth.login import (
    LoginRequest,
    LoginResponse,
    LoginUseCase,
)
from app.application.use_cases.auth.register import (
    RegisterRequest,
    RegisterResponse,
    RegisterUseCase,
)
from app.application.use_cases.auth.refresh import (
    RefreshRequest,
    RefreshResponse,
    RefreshTokenUseCase,
)
from app.domain.entities.user import User
from app.domain.exceptions.base import AuthenticationError, ConflictError, ValidationError
from app.domain.value_objects.email import Email


class TestLoginUseCase:
    """Tests for LoginUseCase."""

    @pytest.fixture
    def mock_user_repository(self) -> AsyncMock:
        """Create mock user repository."""
        return AsyncMock()

    @pytest.fixture
    def user(self) -> User:
        """Create test user."""
        return User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("test@example.com"),
            password_hash="$2b$12$hashed_password",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
        )

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        mock_user_repository: AsyncMock,
        user: User,
    ) -> None:
        """Test successful login."""
        mock_user_repository.get_by_email.return_value = user
        mock_user_repository.update.return_value = user

        use_case = LoginUseCase(mock_user_repository)

        with patch(
            "app.application.use_cases.auth.login.verify_password",
            return_value=True,
        ):
            request = LoginRequest(email="test@example.com", password="SecureP@ss123")
            response = await use_case.execute(request)

        assert isinstance(response, LoginResponse)
        assert response.access_token
        assert response.refresh_token
        assert response.user_id == user.id
        assert response.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Test login with non-existent user."""
        mock_user_repository.get_by_email.return_value = None

        use_case = LoginUseCase(mock_user_repository)
        request = LoginRequest(email="nonexistent@example.com", password="pass")

        with pytest.raises(AuthenticationError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Test login with inactive user."""
        # Create inactive user
        inactive_user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("test@example.com"),
            password_hash="$2b$12$hashed_password",
            first_name="Test",
            last_name="User",
            is_active=False,
            is_superuser=False,
        )
        mock_user_repository.get_by_email.return_value = inactive_user

        use_case = LoginUseCase(mock_user_repository)
        request = LoginRequest(email="test@example.com", password="pass")

        with pytest.raises(AuthenticationError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.code == "ACCOUNT_INACTIVE"

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        mock_user_repository: AsyncMock,
        user: User,
    ) -> None:
        """Test login with wrong password."""
        mock_user_repository.get_by_email.return_value = user

        use_case = LoginUseCase(mock_user_repository)

        with patch(
            "app.application.use_cases.auth.login.verify_password",
            return_value=False,
        ):
            request = LoginRequest(email="test@example.com", password="wrong_password")

            with pytest.raises(AuthenticationError) as exc_info:
                await use_case.execute(request)

            assert exc_info.value.code == "INVALID_CREDENTIALS"


class TestRegisterUseCase:
    """Tests for RegisterUseCase."""

    @pytest.fixture
    def mock_user_repository(self) -> AsyncMock:
        """Create mock user repository."""
        repo = AsyncMock()
        repo.exists_by_email.return_value = False
        return repo

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Test successful registration."""
        # Mock create to return a user with the same data
        async def mock_create(user: User) -> User:
            return user

        mock_user_repository.create.side_effect = mock_create

        use_case = RegisterUseCase(mock_user_repository)
        request = RegisterRequest(
            email="newuser@example.com",
            password="SecureP@ss123!",
            first_name="New",
            last_name="User",
        )

        response = await use_case.execute(request)

        assert isinstance(response, RegisterResponse)
        assert response.access_token
        assert response.refresh_token
        assert response.user.email.value == "newuser@example.com"
        mock_user_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_invalid_email(
        self,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Test registration with invalid email."""
        use_case = RegisterUseCase(mock_user_repository)
        request = RegisterRequest(
            email="invalid-email",
            password="SecureP@ss123!",
            first_name="Test",
            last_name="User",
        )

        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.field == "email"

    @pytest.mark.asyncio
    async def test_register_weak_password(
        self,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Test registration with weak password."""
        use_case = RegisterUseCase(mock_user_repository)
        request = RegisterRequest(
            email="valid@example.com",
            password="weak",
            first_name="Test",
            last_name="User",
        )

        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(request)

        assert exc_info.value.field == "password"

    @pytest.mark.asyncio
    async def test_register_email_exists(
        self,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Test registration with existing email."""
        mock_user_repository.exists_by_email.return_value = True

        use_case = RegisterUseCase(mock_user_repository)
        request = RegisterRequest(
            email="existing@example.com",
            password="SecureP@ss123!",
            first_name="Test",
            last_name="User",
        )

        with pytest.raises(ConflictError) as exc_info:
            await use_case.execute(request)

        assert "already registered" in str(exc_info.value)


class TestRefreshTokenUseCase:
    """Tests for RefreshTokenUseCase."""

    @pytest.fixture
    def mock_user_repository(self) -> AsyncMock:
        """Create mock user repository."""
        return AsyncMock()

    @pytest.fixture
    def user(self) -> User:
        """Create test user."""
        return User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("test@example.com"),
            password_hash="hashed",
            first_name="Test",
            last_name="User",
            is_active=True,
            is_superuser=False,
        )

    @pytest.mark.asyncio
    async def test_refresh_success(
        self,
        mock_user_repository: AsyncMock,
        user: User,
    ) -> None:
        """Test successful token refresh."""
        mock_user_repository.get_by_id.return_value = user

        use_case = RefreshTokenUseCase(mock_user_repository)

        with patch(
            "app.application.use_cases.auth.refresh.validate_refresh_token",
            return_value={
                "sub": str(user.id),
                "tenant_id": str(user.tenant_id),
                "type": "refresh",
            },
        ):
            request = RefreshRequest(refresh_token="valid_refresh_token")
            response = await use_case.execute(request)

        assert isinstance(response, RefreshResponse)
        assert response.access_token
        assert response.refresh_token

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(
        self,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Test refresh with invalid token."""
        use_case = RefreshTokenUseCase(mock_user_repository)

        with patch(
            "app.application.use_cases.auth.refresh.validate_refresh_token",
            side_effect=AuthenticationError(
                message="Invalid token", code="INVALID_TOKEN"
            ),
        ):
            request = RefreshRequest(refresh_token="invalid_token")

            with pytest.raises(AuthenticationError) as exc_info:
                await use_case.execute(request)

            assert exc_info.value.code == "INVALID_REFRESH_TOKEN"

    @pytest.mark.asyncio
    async def test_refresh_user_not_found(
        self,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Test refresh when user no longer exists."""
        mock_user_repository.get_by_id.return_value = None

        use_case = RefreshTokenUseCase(mock_user_repository)

        with patch(
            "app.application.use_cases.auth.refresh.validate_refresh_token",
            return_value={
                "sub": str(uuid4()),
                "tenant_id": str(uuid4()),
                "type": "refresh",
            },
        ):
            request = RefreshRequest(refresh_token="valid_token")

            with pytest.raises(AuthenticationError) as exc_info:
                await use_case.execute(request)

            assert exc_info.value.code == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_refresh_inactive_user(
        self,
        mock_user_repository: AsyncMock,
    ) -> None:
        """Test refresh with inactive user."""
        inactive_user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email=Email("test@example.com"),
            password_hash="hashed",
            first_name="Test",
            last_name="User",
            is_active=False,
            is_superuser=False,
        )
        mock_user_repository.get_by_id.return_value = inactive_user

        use_case = RefreshTokenUseCase(mock_user_repository)

        with patch(
            "app.application.use_cases.auth.refresh.validate_refresh_token",
            return_value={
                "sub": str(inactive_user.id),
                "tenant_id": str(inactive_user.tenant_id),
                "type": "refresh",
            },
        ):
            request = RefreshRequest(refresh_token="valid_token")

            with pytest.raises(AuthenticationError) as exc_info:
                await use_case.execute(request)

            assert exc_info.value.code == "ACCOUNT_INACTIVE"
