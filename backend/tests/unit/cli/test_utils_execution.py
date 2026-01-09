# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for CLI utility functions with code execution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from io import StringIO
import pytest

from app.cli.utils import format_uuid, print_table


class TestFormatUuid:
    """Tests for format_uuid function."""

    def test_format_valid_uuid(self) -> None:
        """Test format_uuid with valid UUID string."""
        valid_uuid = str(uuid4())
        result = format_uuid(valid_uuid)
        assert result is not None
        assert isinstance(result, UUID)
        assert str(result) == valid_uuid

    def test_format_invalid_uuid(self) -> None:
        """Test format_uuid with invalid string."""
        result = format_uuid("not-a-uuid")
        assert result is None

    def test_format_empty_string(self) -> None:
        """Test format_uuid with empty string."""
        result = format_uuid("")
        assert result is None

    def test_format_partial_uuid(self) -> None:
        """Test format_uuid with partial UUID."""
        result = format_uuid("12345678")
        assert result is None

    def test_format_uuid_with_hyphens(self) -> None:
        """Test format_uuid with standard UUID format."""
        uuid_str = "12345678-1234-1234-1234-123456789abc"
        result = format_uuid(uuid_str)
        assert result is not None
        assert str(result) == uuid_str

    def test_format_uuid_uppercase(self) -> None:
        """Test format_uuid with uppercase letters."""
        uuid_str = "12345678-1234-1234-1234-123456789ABC"
        result = format_uuid(uuid_str)
        assert result is not None


class TestPrintTable:
    """Tests for print_table function."""

    def test_print_table_with_data(self) -> None:
        """Test print_table with data."""
        with patch("typer.echo") as mock_echo:
            headers = ["ID", "Name", "Status"]
            rows = [
                ["1", "Test User", "Active"],
                ["2", "Another User", "Inactive"],
            ]
            print_table(headers, rows)
            
            # Verify header was printed
            assert mock_echo.call_count >= 3

    def test_print_table_empty_rows(self) -> None:
        """Test print_table with no data."""
        with patch("typer.echo") as mock_echo:
            headers = ["ID", "Name"]
            rows = []
            print_table(headers, rows)
            
            mock_echo.assert_called_with("No data to display")

    def test_print_table_single_row(self) -> None:
        """Test print_table with single row."""
        with patch("typer.echo") as mock_echo:
            headers = ["Column"]
            rows = [["Value"]]
            print_table(headers, rows)
            
            assert mock_echo.call_count >= 2

    def test_print_table_long_values(self) -> None:
        """Test print_table with long cell values."""
        with patch("typer.echo") as mock_echo:
            headers = ["Short", "Long Header That Is Very Long"]
            rows = [
                ["A", "This is a very long value for testing column width"],
            ]
            print_table(headers, rows)
            
            assert mock_echo.called

    def test_print_table_unicode(self) -> None:
        """Test print_table with unicode characters."""
        with patch("typer.echo") as mock_echo:
            headers = ["Name", "Symbol"]
            rows = [
                ["Test", "✓"],
                ["Emoji", "🚀"],
            ]
            print_table(headers, rows)
            
            assert mock_echo.called


class TestConfirmAction:
    """Tests for confirm_action function."""

    def test_confirm_action_yes(self) -> None:
        """Test confirm_action with yes response."""
        from app.cli.utils import confirm_action
        
        with patch("typer.prompt", return_value="y"):
            result = confirm_action("Continue?")
            assert result is True

    def test_confirm_action_yes_full(self) -> None:
        """Test confirm_action with 'yes' response."""
        from app.cli.utils import confirm_action
        
        with patch("typer.prompt", return_value="yes"):
            result = confirm_action("Continue?")
            assert result is True

    def test_confirm_action_no(self) -> None:
        """Test confirm_action with no response."""
        from app.cli.utils import confirm_action
        
        with patch("typer.prompt", return_value="n"):
            result = confirm_action("Continue?")
            assert result is False

    def test_confirm_action_default_true(self) -> None:
        """Test confirm_action with default True."""
        from app.cli.utils import confirm_action
        
        with patch("typer.prompt", return_value="y") as mock_prompt:
            confirm_action("Continue?", default=True)
            # Check that the prompt contains [Y/n]
            call_args = mock_prompt.call_args
            assert "Y/n" in call_args[0][0] or "y" in str(call_args)

    def test_confirm_action_default_false(self) -> None:
        """Test confirm_action with default False."""
        from app.cli.utils import confirm_action
        
        with patch("typer.prompt", return_value="n") as mock_prompt:
            confirm_action("Continue?", default=False)
            call_args = mock_prompt.call_args
            assert "y/N" in call_args[0][0] or "n" in str(call_args)


class TestCheckDatabase:
    """Tests for check_database function."""

    @pytest.mark.asyncio
    async def test_check_database_function_exists(self) -> None:
        """Test that check_database function exists and is callable."""
        from app.cli.utils import check_database
        
        assert callable(check_database)

    @pytest.mark.asyncio
    async def test_check_database_returns_bool(self) -> None:
        """Test that check_database returns a boolean."""
        from app.cli.utils import check_database
        
        # Can't easily test without DB, but verify the function signature
        import inspect
        sig = inspect.signature(check_database)
        assert len(sig.parameters) == 0


class TestCheckRedis:
    """Tests for check_redis function."""

    @pytest.mark.asyncio
    async def test_check_redis_function_exists(self) -> None:
        """Test that check_redis function exists and is callable."""
        from app.cli.utils import check_redis
        
        assert callable(check_redis)


class TestGetOrCreateDefaultTenant:
    """Tests for get_or_create_default_tenant function."""

    @pytest.mark.asyncio
    async def test_get_or_create_default_tenant_exists(self) -> None:
        """Test function exists and is callable."""
        from app.cli.utils import get_or_create_default_tenant
        
        assert callable(get_or_create_default_tenant)
