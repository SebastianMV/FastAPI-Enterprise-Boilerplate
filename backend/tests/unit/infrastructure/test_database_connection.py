# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for database connection module."""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from uuid import uuid4

from app.infrastructure.database.connection import (
    Base,
    set_tenant_context,
    get_db_session,
    get_db_context,
    init_database,
    close_database,
)


class TestBase:
    """Tests for Base declarative class."""
    
    def test_base_is_declarative_base(self):
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)


class TestSetTenantContext:
    """Tests for set_tenant_context function."""
    
    @pytest.mark.asyncio
    async def test_sets_tenant_id(self):
        mock_session = AsyncMock()
        tenant_id = uuid4()
        
        await set_tenant_context(mock_session, tenant_id)
        
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0][0]
        assert str(tenant_id) in str(call_args)
    
    @pytest.mark.asyncio
    async def test_resets_when_none(self):
        mock_session = AsyncMock()
        
        await set_tenant_context(mock_session, None)
        
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0][0]
        assert "RESET" in str(call_args)


class TestGetDbSession:
    """Tests for get_db_session generator."""
    
    @pytest.mark.asyncio
    async def test_yields_session(self):
        mock_session = AsyncMock()
        mock_session_maker = MagicMock()
        
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            with patch("app.middleware.tenant.get_current_tenant_id", return_value=None):
                with patch("app.infrastructure.database.connection.set_tenant_context"):
                    async for session in get_db_session():
                        assert session is mock_session
    
    @pytest.mark.asyncio
    async def test_sets_tenant_context_when_available(self):
        mock_session = AsyncMock()
        tenant_id = uuid4()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            with patch("app.middleware.tenant.get_current_tenant_id", return_value=tenant_id):
                with patch("app.infrastructure.database.connection.set_tenant_context") as mock_set_ctx:
                    async for session in get_db_session():
                        pass
                    mock_set_ctx.assert_called_once_with(mock_session, tenant_id)
    
    @pytest.mark.asyncio
    async def test_commits_on_success(self):
        mock_session = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            with patch("app.middleware.tenant.get_current_tenant_id", return_value=None):
                async for session in get_db_session():
                    pass
        
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rollback_on_error(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock(side_effect=Exception("DB Error"))
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            with patch("app.middleware.tenant.get_current_tenant_id", return_value=None):
                with pytest.raises(Exception):
                    async for session in get_db_session():
                        pass
        
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_closes_session(self):
        mock_session = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            with patch("app.middleware.tenant.get_current_tenant_id", return_value=None):
                async for session in get_db_session():
                    pass
        
        mock_session.close.assert_called_once()


class TestGetDbContext:
    """Tests for get_db_context context manager."""
    
    @pytest.mark.asyncio
    async def test_yields_session(self):
        mock_session = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            with patch("app.infrastructure.database.connection.set_tenant_context"):
                async with get_db_context() as session:
                    assert session is mock_session
    
    @pytest.mark.asyncio
    async def test_sets_tenant_context_when_provided(self):
        mock_session = AsyncMock()
        tenant_id = uuid4()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            with patch("app.infrastructure.database.connection.set_tenant_context") as mock_set_ctx:
                async with get_db_context(tenant_id=tenant_id) as session:
                    pass
                mock_set_ctx.assert_called_once_with(mock_session, tenant_id)
    
    @pytest.mark.asyncio
    async def test_skips_tenant_context_when_none(self):
        mock_session = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            with patch("app.infrastructure.database.connection.set_tenant_context") as mock_set_ctx:
                async with get_db_context(tenant_id=None) as session:
                    pass
                mock_set_ctx.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_commits_on_success(self):
        mock_session = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            async with get_db_context() as session:
                pass
        
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rollback_on_error(self):
        mock_session = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            with pytest.raises(ValueError):
                async with get_db_context() as session:
                    raise ValueError("Test error")
        
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_closes_session(self):
        mock_session = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch("app.infrastructure.database.connection.async_session_maker", mock_session_maker):
            async with get_db_context() as session:
                pass
        
        mock_session.close.assert_called_once()


class TestInitDatabase:
    """Tests for init_database function."""
    
    @pytest.mark.asyncio
    async def test_calls_alembic_upgrade(self):
        """Test that init_database calls alembic upgrade head."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            
            await init_database()
        
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["alembic", "upgrade", "head"]

    @pytest.mark.asyncio
    async def test_handles_alembic_error(self):
        """Test that init_database handles alembic errors gracefully."""
        # Mock the async engine.begin() context manager
        mock_conn = AsyncMock()
        mock_begin_ctx = AsyncMock()
        mock_begin_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin_ctx.__aexit__ = AsyncMock(return_value=None)
        
        with patch("subprocess.run") as mock_run, \
             patch("app.infrastructure.database.connection.engine") as mock_engine:
            
            mock_run.return_value = MagicMock(
                returncode=1, 
                stdout="", 
                stderr="Migration error"
            )
            mock_engine.begin.return_value = mock_begin_ctx
            
            # Should not raise, just log warning and fallback to create_all
            await init_database()
            
            # Verify fallback was called
            mock_conn.run_sync.assert_called_once()


class TestCloseDatabase:
    """Tests for close_database function."""
    
    @pytest.mark.asyncio
    async def test_disposes_engine(self):
        mock_engine = AsyncMock()
        
        with patch("app.infrastructure.database.connection.engine", mock_engine):
            await close_database()
        
        mock_engine.dispose.assert_called_once()
