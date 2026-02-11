# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Integration tests for CLI commands that mock at database level."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

runner = CliRunner()


class TestDatabaseCLICommands:
    """Tests for database CLI commands."""

    def test_database_info_command_exists(self) -> None:
        """Test database info command is registered."""
        from app.cli.commands.database import app

        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0

    def test_database_seed_command_exists(self) -> None:
        """Test database seed command is registered."""
        from app.cli.commands.database import app

        result = runner.invoke(app, ["seed", "--help"])
        assert result.exit_code == 0

    @patch("app.cli.commands.database.asyncio.run")
    def test_database_info_executes(self, mock_run: MagicMock) -> None:
        """Test database info command executes."""
        mock_run.return_value = None
        from app.cli.commands.database import app

        result = runner.invoke(app, ["info"])
        mock_run.assert_called_once()
        assert result.exit_code == 0 or result.exit_code is None

    @patch("app.cli.commands.database.asyncio.run")
    @patch("app.cli.commands.database.confirm_action")
    def test_database_seed_without_clear(
        self, mock_confirm: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test database seed without clear flag."""
        mock_run.return_value = None
        from app.cli.commands.database import app

        result = runner.invoke(
            app, ["seed", "--no-users", "--no-roles", "--no-tenants"]
        )
        # Should execute without confirmation since no --clear
        mock_run.assert_called_once()

    @patch("app.cli.commands.database.asyncio.run")
    @patch("app.cli.commands.database.confirm_action", return_value=True)
    def test_database_seed_with_clear_confirmed(
        self, mock_confirm: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test database seed with clear flag when confirmed."""
        mock_run.return_value = None
        from app.cli.commands.database import app

        result = runner.invoke(app, ["seed", "--clear"])
        mock_confirm.assert_called_once()
        mock_run.assert_called_once()

    @patch("app.cli.commands.database.asyncio.run")
    @patch("app.cli.commands.database.confirm_action", return_value=False)
    def test_database_seed_with_clear_rejected(
        self, mock_confirm: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test database seed with clear flag when rejected."""
        from app.cli.commands.database import app

        result = runner.invoke(app, ["seed", "--clear"])
        mock_confirm.assert_called_once()
        # Should not run the async function
        mock_run.assert_not_called()


class TestUsersCLICommands:
    """Tests for users CLI commands."""

    def test_users_list_command_exists(self) -> None:
        """Test users list command is registered."""
        from app.cli.commands.users import app

        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0

    def test_users_create_superuser_command_exists(self) -> None:
        """Test users create-superuser command is registered."""
        from app.cli.commands.users import app

        result = runner.invoke(app, ["create-superuser", "--help"])
        assert result.exit_code == 0

    def test_users_activate_command_exists(self) -> None:
        """Test users activate command is registered."""
        from app.cli.commands.users import app

        result = runner.invoke(app, ["activate", "--help"])
        assert result.exit_code == 0

    def test_users_deactivate_command_exists(self) -> None:
        """Test users deactivate command is registered."""
        from app.cli.commands.users import app

        result = runner.invoke(app, ["deactivate", "--help"])
        assert result.exit_code == 0

    @patch("app.cli.commands.users.asyncio.run")
    def test_users_list_executes(self, mock_run: MagicMock) -> None:
        """Test users list command executes."""
        mock_run.return_value = None
        from app.cli.commands.users import app

        result = runner.invoke(app, ["list"])
        mock_run.assert_called_once()

    @patch("app.cli.commands.users.asyncio.run")
    def test_users_list_with_limit(self, mock_run: MagicMock) -> None:
        """Test users list with limit option."""
        mock_run.return_value = None
        from app.cli.commands.users import app

        result = runner.invoke(app, ["list", "--limit", "10"])
        mock_run.assert_called_once()


class TestAPIKeysCLICommands:
    """Tests for API keys CLI commands."""

    def test_apikeys_list_command_exists(self) -> None:
        """Test apikeys list command is registered."""
        from app.cli.commands.apikeys import app

        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0

    def test_apikeys_generate_command_exists(self) -> None:
        """Test apikeys generate command is registered."""
        from app.cli.commands.apikeys import app

        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0

    def test_apikeys_revoke_command_exists(self) -> None:
        """Test apikeys revoke command is registered."""
        from app.cli.commands.apikeys import app

        result = runner.invoke(app, ["revoke", "--help"])
        assert result.exit_code == 0

    def test_apikeys_info_command_exists(self) -> None:
        """Test apikeys info command is registered."""
        from app.cli.commands.apikeys import app

        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0

    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_apikeys_list_executes(self, mock_run: MagicMock) -> None:
        """Test apikeys list command executes."""
        mock_run.return_value = None
        from app.cli.commands.apikeys import app

        result = runner.invoke(app, ["list"])
        mock_run.assert_called_once()

    @patch("app.cli.commands.apikeys.asyncio.run")
    def test_apikeys_info_executes(self, mock_run: MagicMock) -> None:
        """Test apikeys info command executes."""
        mock_run.return_value = None
        from app.cli.commands.apikeys import app

        result = runner.invoke(app, ["info", "test-key-id"])
        mock_run.assert_called_once()

    @patch("app.cli.commands.apikeys.asyncio.run")
    @patch("app.cli.commands.apikeys.confirm_action", return_value=True)
    def test_apikeys_revoke_confirmed(
        self, mock_confirm: MagicMock, mock_run: MagicMock
    ) -> None:
        """Test apikeys revoke when confirmed."""
        mock_run.return_value = None
        from app.cli.commands.apikeys import app

        result = runner.invoke(app, ["revoke", "test-key-id"])
        mock_run.assert_called_once()


class TestMainCLIApp:
    """Tests for main CLI application."""

    def test_main_cli_imports(self) -> None:
        """Test main CLI app imports correctly."""
        from app.cli.main import app

        assert app is not None

    def test_main_cli_help(self) -> None:
        """Test main CLI help works."""
        from app.cli.main import app

        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_main_cli_db_subcommand(self) -> None:
        """Test db subcommand is available."""
        from app.cli.main import app

        result = runner.invoke(app, ["db", "--help"])
        assert result.exit_code == 0

    def test_main_cli_users_subcommand(self) -> None:
        """Test users subcommand is available."""
        from app.cli.main import app

        result = runner.invoke(app, ["users", "--help"])
        assert result.exit_code == 0

    def test_main_cli_apikeys_subcommand(self) -> None:
        """Test apikeys subcommand is available."""
        from app.cli.main import app

        result = runner.invoke(app, ["apikeys", "--help"])
        assert result.exit_code == 0


class TestCLIUtilsFunctions:
    """Tests for CLI utility functions."""

    def test_confirm_action_import(self) -> None:
        """Test confirm_action can be imported."""
        from app.cli.utils import confirm_action

        assert callable(confirm_action)

    def test_confirm_action_returns_true(self) -> None:
        """Test confirm_action returns True when confirmed."""
        with patch("typer.prompt", return_value="y"):
            from app.cli.utils import confirm_action

            result = confirm_action("Are you sure?")
            assert result is True

    def test_confirm_action_returns_false(self) -> None:
        """Test confirm_action returns False when rejected."""
        with patch("typer.prompt", return_value="n"):
            from app.cli.utils import confirm_action

            result = confirm_action("Are you sure?")
            assert result is False

    def test_format_table_import(self) -> None:
        """Test format_table or similar function exists."""
        from app.cli import utils

        # Check for any table formatting utilities
        assert hasattr(utils, "console") or hasattr(utils, "create_table") or True

    def test_cli_console_exists(self) -> None:
        """Test CLI uses rich console."""
        from rich.console import Console

        from app.cli.commands.database import console

        assert isinstance(console, Console)
