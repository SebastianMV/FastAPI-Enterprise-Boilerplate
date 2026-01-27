# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests to cover missing lines in connection.py (lines 191-199)."""

import pytest
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.database.connection import init_database


class TestInitDatabaseMissingLines:
    """Tests for init_database function to cover missing lines."""

    @pytest.mark.asyncio
    async def test_init_database_success_with_stdout(self):
        """Test init_database when Alembic succeeds with stdout output."""
        # Lines 191-193: for line in result.stdout.strip().split('\n'): logger.info(f"  {line}")
        stdout_output = "Running upgrade -> rev1\nRunning upgrade rev1 -> rev2"
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=stdout_output,
                stderr=""
            )
            
            # Should not raise
            await init_database()
            
            # Verify subprocess.run was called
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_database_timeout(self):
        """Test init_database when Alembic times out."""
        # Lines 194-195: except subprocess.TimeoutExpired: logger.error(...) raise
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("alembic", 30)
            
            # Should raise TimeoutExpired
            with pytest.raises(subprocess.TimeoutExpired):
                await init_database()

    @pytest.mark.asyncio
    async def test_init_database_file_not_found(self):
        """Test init_database when Alembic is not found."""
        # Lines 197-199: except FileNotFoundError: ...Base.metadata.create_all()
        mock_conn = AsyncMock()
        mock_begin_ctx = AsyncMock()
        mock_begin_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin_ctx.__aexit__ = AsyncMock(return_value=None)
        
        with patch("subprocess.run") as mock_run, \
             patch("app.infrastructure.database.connection.engine") as mock_engine:
            
            mock_run.side_effect = FileNotFoundError("alembic not found")
            mock_engine.begin.return_value = mock_begin_ctx
            
            # Should not raise, fallback to create_all
            await init_database()
            
            # Verify fallback was called
            mock_conn.run_sync.assert_called_once()
