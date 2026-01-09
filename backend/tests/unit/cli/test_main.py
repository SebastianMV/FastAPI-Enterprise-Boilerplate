# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for CLI main module."""

import pytest
from typer.testing import CliRunner

from app.cli.main import app


runner = CliRunner()


class TestAppStructure:
    """Tests for app structure."""

    def test_app_help(self):
        """Test app shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "FastAPI Enterprise Boilerplate CLI" in result.output

    def test_users_subcommand_exists(self):
        """Test users subcommand is registered."""
        result = runner.invoke(app, ["users", "--help"])
        assert result.exit_code == 0

    def test_db_subcommand_exists(self):
        """Test db subcommand is registered."""
        result = runner.invoke(app, ["db", "--help"])
        assert result.exit_code == 0

    def test_apikeys_subcommand_exists(self):
        """Test apikeys subcommand is registered."""
        result = runner.invoke(app, ["apikeys", "--help"])
        assert result.exit_code == 0
    
    def test_version_subcommand_exists(self):
        """Test version subcommand is registered."""
        result = runner.invoke(app, ["--help"])
        assert "version" in result.output

    def test_health_subcommand_exists(self):
        """Test health subcommand is registered."""
        result = runner.invoke(app, ["--help"])
        assert "health" in result.output
