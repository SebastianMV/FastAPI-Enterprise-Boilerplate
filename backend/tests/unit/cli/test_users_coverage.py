# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for CLI users commands to achieve 100% coverage.
Focuses on 66 uncovered lines in app/cli/commands/users.py
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import typer


class TestCreateSuperuserAsync:
    """Tests for _create_superuser async implementation."""

    @pytest.mark.asyncio
    async def test_create_superuser_invalid_email(self):
        """Test create superuser with invalid email format."""
        from app.cli.commands.users import _create_superuser

        with (
            patch("app.cli.commands.users.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            await _create_superuser("invalid-email", "Password123!", "Admin", "User")

        assert exc_info.value.exit_code == 1
        assert "Invalid email" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_create_superuser_weak_password(self):
        """Test create superuser with weak password."""
        from app.cli.commands.users import _create_superuser

        with (
            patch("app.cli.commands.users.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            await _create_superuser("valid@example.com", "weak", "Admin", "User")

        assert exc_info.value.exit_code == 1
        assert "Password does not meet security requirements" in str(
            mock_console.print.call_args
        )

    @pytest.mark.asyncio
    async def test_create_superuser_email_already_exists(self):
        """Test create superuser when email already exists."""
        from app.cli.commands.users import _create_superuser

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = MagicMock()  # Existing user

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.commands.users.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _create_superuser(
                "existing@example.com", "SecureP@ss123!", "Admin", "User"
            )

        assert exc_info.value.exit_code == 1
        assert "already exists" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_create_superuser_success(self):
        """Test successful superuser creation."""
        from app.cli.commands.users import _create_superuser

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email.return_value = None  # No existing user

        created_user = MagicMock()
        created_user.id = uuid4()
        mock_user_repo.create.return_value = created_user

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.utils.get_or_create_default_tenant", return_value=uuid4()),
            patch(
                "app.infrastructure.auth.jwt_handler.hash_password",
                return_value="hashed",
            ),
            patch("app.cli.commands.users.console") as mock_console,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _create_superuser(
                "newadmin@example.com", "SecureP@ss123!", "Admin", "User"
            )

        mock_user_repo.create.assert_called_once()
        mock_session.commit.assert_called_once()
        assert "Superuser created successfully" in str(
            mock_console.print.call_args_list
        )


class TestListUsersAsync:
    """Tests for _list_users async implementation."""

    @pytest.mark.asyncio
    async def test_list_users_no_users_found(self):
        """Test list users when no users exist."""
        from app.cli.commands.users import _list_users

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.list.return_value = []

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.commands.users.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _list_users(50, False)

        assert exc_info.value.exit_code == 0
        assert "No users found" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_list_users_with_results(self):
        """Test list users with results."""
        from app.cli.commands.users import _list_users

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "user@example.com"
        mock_user.full_name = "Test User"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.created_at = datetime.now(UTC)

        mock_user_repo.list.return_value = [mock_user]

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.commands.users.console") as mock_console,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _list_users(50, False)

        mock_user_repo.list.assert_called_once_with(limit=50, is_active=None)
        mock_console.print.assert_called()

    @pytest.mark.asyncio
    async def test_list_users_active_only(self):
        """Test list users with active_only filter."""
        from app.cli.commands.users import _list_users

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "active@example.com"
        mock_user.full_name = None  # Test None case
        mock_user.is_active = True
        mock_user.is_superuser = True
        mock_user.created_at = None  # Test None created_at

        mock_user_repo.list.return_value = [mock_user]

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.commands.users.console"),
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _list_users(20, True)

        mock_user_repo.list.assert_called_once_with(limit=20, is_active=True)


class TestSetUserActiveAsync:
    """Tests for _set_user_active async implementation (activate/deactivate)."""

    @pytest.mark.asyncio
    async def test_set_user_active_user_not_found(self):
        """Test activate when user doesn't exist."""
        from app.cli.commands.users import _set_user_active

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = None

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.commands.users.console") as mock_console,
            pytest.raises(typer.Exit) as exc_info,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _set_user_active(uuid4(), True)

        assert exc_info.value.exit_code == 1
        assert "User not found" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_set_user_active_activate_success(self):
        """Test successful user activation."""
        from app.cli.commands.users import _set_user_active

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_user = MagicMock()
        mock_user.email = "user@example.com"
        mock_user_repo.get_by_id.return_value = mock_user

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.commands.users.console") as mock_console,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _set_user_active(uuid4(), True)

        mock_user.activate.assert_called_once()
        mock_user_repo.update.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()
        assert "activated" in str(mock_console.print.call_args)

    @pytest.mark.asyncio
    async def test_set_user_active_deactivate_success(self):
        """Test successful user deactivation."""
        from app.cli.commands.users import _set_user_active

        mock_session = AsyncMock()
        mock_user_repo = AsyncMock()

        mock_user = MagicMock()
        mock_user.email = "user@example.com"
        mock_user_repo.get_by_id.return_value = mock_user

        with (
            patch(
                "app.infrastructure.database.connection.async_session_maker"
            ) as mock_maker,
            patch(
                "app.infrastructure.database.repositories.user_repository.SQLAlchemyUserRepository",
                return_value=mock_user_repo,
            ),
            patch("app.cli.commands.users.console") as mock_console,
        ):
            mock_maker.return_value.__aenter__.return_value = mock_session

            await _set_user_active(uuid4(), False)

        mock_user.deactivate.assert_called_once()
        mock_user_repo.update.assert_called_once_with(mock_user)
        mock_session.commit.assert_called_once()
        assert "deactivated" in str(mock_console.print.call_args)


class TestUsersCLICommands:
    """Tests for CLI command wrappers."""

    def test_activate_user_invalid_uuid(self):
        """Test activate with invalid UUID format."""
        from typer.testing import CliRunner

        from app.cli.commands.users import app

        runner = CliRunner()
        result = runner.invoke(app, ["activate", "invalid-uuid"])

        assert result.exit_code == 1
        assert "Invalid UUID" in result.output

    def test_deactivate_user_invalid_uuid(self):
        """Test deactivate with invalid UUID format."""
        from typer.testing import CliRunner

        from app.cli.commands.users import app

        runner = CliRunner()
        result = runner.invoke(app, ["deactivate", "not-a-uuid"])

        assert result.exit_code == 1
        assert "Invalid UUID" in result.output

    @patch("app.cli.commands.users.asyncio.run")
    def test_list_command_calls_async(self, mock_run):
        """Test list command calls async implementation."""
        from typer.testing import CliRunner

        from app.cli.commands.users import app

        runner = CliRunner()
        result = runner.invoke(app, ["list", "--limit", "10"])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.asyncio.run")
    def test_activate_command_valid_uuid(self, mock_run):
        """Test activate command with valid UUID."""
        from typer.testing import CliRunner

        from app.cli.commands.users import app

        runner = CliRunner()
        result = runner.invoke(app, ["activate", str(uuid4())])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.asyncio.run")
    def test_deactivate_command_valid_uuid(self, mock_run):
        """Test deactivate command with valid UUID."""
        from typer.testing import CliRunner

        from app.cli.commands.users import app

        runner = CliRunner()
        result = runner.invoke(app, ["deactivate", str(uuid4())])

        assert result.exit_code == 0
        mock_run.assert_called_once()
