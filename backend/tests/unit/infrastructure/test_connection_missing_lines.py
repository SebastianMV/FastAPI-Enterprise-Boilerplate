# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests to cover missing lines in connection.py (lines 191-199)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.database.connection import init_database


class TestInitDatabaseMissingLines:
    """Tests for init_database function to cover missing lines."""

    @pytest.mark.asyncio
    async def test_init_database_success_with_stdout(self):
        """Test init_database when Alembic succeeds with stdout output."""
        stdout_output = b"Running upgrade -> rev1\nRunning upgrade rev1 -> rev2"

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(stdout_output, b""))
        mock_process.returncode = 0

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_process
        ) as mock_exec:
            # Should not raise
            await init_database()

            # Verify asyncio.create_subprocess_exec was called
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_database_timeout(self):
        """Test init_database when Alembic times out."""
        mock_process = AsyncMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("asyncio.wait_for", side_effect=TimeoutError()),
        ):
            # Should raise TimeoutError (re-raised after logging)
            with pytest.raises(TimeoutError):
                await init_database()

    @pytest.mark.asyncio
    async def test_init_database_file_not_found(self):
        """Test init_database when Alembic is not found."""
        mock_conn = AsyncMock()
        mock_begin_ctx = AsyncMock()
        mock_begin_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError("alembic not found"),
            ),
            patch("app.infrastructure.database.connection.engine") as mock_engine,
        ):
            mock_engine.begin.return_value = mock_begin_ctx

            # Should not raise, fallback to create_all
            await init_database()

            # Verify fallback was called
            mock_conn.run_sync.assert_called_once()
