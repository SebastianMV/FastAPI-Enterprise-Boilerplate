# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Integration tests for user management CLI commands."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from app.cli.commands.users import _create_superuser, app


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Mock rich console to prevent actual output."""
    with patch("app.cli.commands.users.console") as mock:
        yield mock


class TestCreateSuperuser:
    """Test superuser creation command."""

    @patch("app.cli.commands.users.asyncio.run")
    def test_create_superuser_with_prompts(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test creating superuser with prompts."""
        result = cli_runner.invoke(
            app,
            ["create-superuser"],
            input="superadmin@example.com\nSuperSecure123!\nSuperSecure123!\n",
        )

        mock_run.assert_called_once()
        assert result.exit_code == 0

    @patch("app.cli.commands.users.asyncio.run")
    def test_create_superuser_with_options(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test creating superuser with all options specified."""
        result = cli_runner.invoke(
            app,
            [
                "create-superuser",
                "--email",
                "admin@example.com",
                "--password",
                "AdminPass123!",
                "--first-name",
                "John",
                "--last-name",
                "Doe",
            ],
        )

        mock_run.assert_called_once()
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_create_superuser_invalid_email(
        self,
        mock_console: MagicMock,
        db_session,
    ):
        """Test that invalid email is rejected."""
        import typer

        with pytest.raises((SystemExit, typer.Exit)):
            await _create_superuser(
                email="not-an-email",
                password="ValidPass123!",
                first_name="Admin",
                last_name="User",
            )

    @pytest.mark.asyncio
    async def test_create_superuser_weak_password(
        self,
        mock_console: MagicMock,
        db_session,
    ):
        """Test that weak password is rejected."""
        import typer

        with pytest.raises((SystemExit, typer.Exit)):
            await _create_superuser(
                email="admin@example.com",
                password="weak",
                first_name="Admin",
                last_name="User",
            )

    @pytest.mark.asyncio
    async def test_create_superuser_duplicate_email(
        self,
        mock_console: MagicMock,
        db_session,
        real_test_user,
    ):
        """Test that duplicate email is rejected."""
        # This test requires a properly configured database session
        # that matches what the CLI expects. Skip for now as it requires
        # more complex mocking of the async session maker.
        pytest.skip("Test requires complex async session mock - covered by unit tests")


class TestListUsers:
    """Test user listing command."""

    @patch("app.cli.commands.users.asyncio.run")
    def test_list_all_users(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test listing all users."""
        result = cli_runner.invoke(app, ["list"])

        mock_run.assert_called_once()
        assert result.exit_code == 0

    @patch("app.cli.commands.users.asyncio.run")
    def test_list_with_limit(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test listing users with limit."""
        result = cli_runner.invoke(app, ["list", "--limit", "10"])

        mock_run.assert_called_once()
        assert result.exit_code == 0


class TestActivateUser:
    """Test user activation command."""

    @patch("app.cli.commands.users.asyncio.run")
    def test_activate_user(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test activating user by ID."""
        user_id = str(uuid4())
        result = cli_runner.invoke(
            app,
            ["activate", user_id],
        )

        mock_run.assert_called_once()
        assert result.exit_code == 0


class TestDeactivateUser:
    """Test user deactivation command."""

    @patch("app.cli.commands.users.asyncio.run")
    def test_deactivate_user(
        self,
        mock_run: MagicMock,
        cli_runner: CliRunner,
    ):
        """Test deactivating user by ID."""
        user_id = str(uuid4())
        result = cli_runner.invoke(
            app,
            ["deactivate", user_id],
        )

        mock_run.assert_called_once()
        assert result.exit_code == 0
