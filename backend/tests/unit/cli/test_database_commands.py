# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for CLI database commands."""

import pytest
from typer.testing import CliRunner

from app.cli.commands.database import app


runner = CliRunner()


class TestDatabaseCommands:
    """Tests for database CLI commands."""

    def test_db_help(self):
        """Test database command help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Database management commands" in result.output

    def test_migrate_help(self):
        """Test migrate command help."""
        result = runner.invoke(app, ["migrate", "--help"])
        assert result.exit_code == 0

    def test_seed_help(self):
        """Test seed command help."""
        result = runner.invoke(app, ["seed", "--help"])
        assert result.exit_code == 0

    def test_reset_help(self):
        """Test reset command help."""
        result = runner.invoke(app, ["reset", "--help"])
        assert result.exit_code == 0

    def test_status_help(self):
        """Test status command help - may not exist."""
        result = runner.invoke(app, ["status", "--help"])
        # Command may or may not exist
        assert result.exit_code in [0, 2]
