# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for CLI utility functions."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import UUID

from app.cli.utils import format_uuid, print_table


class TestFormatUUID:
    """Tests for format_uuid function."""

    def test_format_uuid_valid(self):
        """Test valid UUID parsing."""
        uuid_str = "12345678-1234-1234-1234-123456789abc"
        result = format_uuid(uuid_str)
        assert result is not None
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_format_uuid_valid_uppercase(self):
        """Test valid UUID with uppercase."""
        uuid_str = "12345678-1234-1234-1234-123456789ABC"
        result = format_uuid(uuid_str)
        assert result is not None

    def test_format_uuid_valid_no_dashes(self):
        """Test valid UUID without dashes."""
        uuid_str = "12345678123412341234123456789abc"
        result = format_uuid(uuid_str)
        assert result is not None

    def test_format_uuid_invalid(self):
        """Test invalid UUID parsing."""
        result = format_uuid("not-a-uuid")
        assert result is None

    def test_format_uuid_empty(self):
        """Test empty string."""
        result = format_uuid("")
        assert result is None

    def test_format_uuid_partial(self):
        """Test partial UUID."""
        result = format_uuid("12345678-1234")
        assert result is None


class TestPrintTable:
    """Tests for print_table function."""

    def test_print_table_basic(self, capsys):
        """Test basic table printing."""
        headers = ["Name", "Age"]
        rows = [["Alice", "25"], ["Bob", "30"]]
        
        with patch("typer.echo") as mock_echo:
            print_table(headers, rows)
            # Should be called 4 times: header, separator, row1, row2
            assert mock_echo.call_count == 4

    def test_print_table_empty(self, capsys):
        """Test empty table."""
        headers = ["Name", "Age"]
        rows = []
        
        with patch("typer.echo") as mock_echo:
            print_table(headers, rows)
            mock_echo.assert_called_once_with("No data to display")

    def test_print_table_single_row(self):
        """Test single row table."""
        headers = ["ID", "Value"]
        rows = [["1", "test"]]
        
        with patch("typer.echo") as mock_echo:
            print_table(headers, rows)
            assert mock_echo.call_count == 3

    def test_print_table_long_values(self):
        """Test table with values longer than headers."""
        headers = ["A", "B"]
        rows = [["VeryLongValue", "AnotherLongValue"]]
        
        with patch("typer.echo") as mock_echo:
            print_table(headers, rows)
            assert mock_echo.call_count == 3
