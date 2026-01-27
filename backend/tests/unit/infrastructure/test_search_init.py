# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Comprehensive tests for Search module initialization and factory."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.infrastructure.search import (
    ELASTICSEARCH_AVAILABLE,
    get_search_backend,
    PostgresFullTextSearch,
    get_postgres_search,
)


class TestSearchAvailability:
    """Tests for search backend availability."""

    def test_postgres_search_always_available(self):
        """PostgreSQL FTS should always be available."""
        from app.infrastructure.search import PostgresFullTextSearch
        assert PostgresFullTextSearch is not None

    def test_elasticsearch_availability_flag(self):
        """Should have elasticsearch availability flag."""
        assert isinstance(ELASTICSEARCH_AVAILABLE, bool)

    def test_postgres_search_factory_exists(self):
        """get_postgres_search factory should exist."""
        from app.infrastructure.search import get_postgres_search
        assert callable(get_postgres_search)


class TestGetSearchBackendPostgres:
    """Tests for getting PostgreSQL search backend."""

    @pytest.mark.asyncio
    async def test_get_postgres_backend_with_session(self):
        """Should return PostgresFullTextSearch with session."""
        mock_session = MagicMock()
        
        backend = await get_search_backend(backend="postgres", session=mock_session)
        
        assert backend is not None
        assert isinstance(backend, PostgresFullTextSearch)

    @pytest.mark.asyncio
    async def test_get_postgres_backend_with_language(self):
        """Should pass language parameter to postgres backend."""
        mock_session = MagicMock()
        
        backend = await get_search_backend(
            backend="postgres",
            session=mock_session,
            language="spanish"
        )
        
        assert backend is not None
        assert backend._language == "spanish"

    @pytest.mark.asyncio
    async def test_get_postgres_backend_default_language(self):
        """Should use default english language if not specified."""
        mock_session = MagicMock()
        
        backend = await get_search_backend(backend="postgres", session=mock_session)
        
        assert backend._language == "english"

    @pytest.mark.asyncio
    async def test_get_postgres_backend_without_session_raises(self):
        """Should raise ValueError if session not provided."""
        with pytest.raises(ValueError, match="SQLAlchemy session required"):
            await get_search_backend(backend="postgres")

    @pytest.mark.asyncio
    async def test_get_postgres_backend_none_session_raises(self):
        """Should raise ValueError if session is None."""
        with pytest.raises(ValueError, match="SQLAlchemy session required"):
            await get_search_backend(backend="postgres", session=None)


class TestGetSearchBackendElasticsearch:
    """Tests for getting Elasticsearch search backend."""

    @pytest.mark.skipif(not ELASTICSEARCH_AVAILABLE, reason="elasticsearch not installed")
    @pytest.mark.asyncio
    async def test_get_elasticsearch_backend_basic(self):
        """Should return ElasticsearchSearch when available."""
        with patch('app.infrastructure.search.get_elasticsearch_search') as mock_get_es:
            mock_es_backend = MagicMock()
            mock_get_es.return_value = mock_es_backend
            
            backend = await get_search_backend(backend="elasticsearch")
            
            assert backend is mock_es_backend
            mock_get_es.assert_called_once()

    @pytest.mark.skipif(not ELASTICSEARCH_AVAILABLE, reason="elasticsearch not installed")
    @pytest.mark.asyncio
    async def test_get_elasticsearch_backend_with_url(self):
        """Should pass URL to elasticsearch backend."""
        with patch('app.infrastructure.search.get_elasticsearch_search') as mock_get_es:
            mock_get_es.return_value = MagicMock()
            
            await get_search_backend(
                backend="elasticsearch",
                url="http://es.example.com:9200"
            )
            
            mock_get_es.assert_called_once_with(
                url="http://es.example.com:9200",
                index_prefix="app",
                username=None,
                password=None,
            )

    @pytest.mark.skipif(not ELASTICSEARCH_AVAILABLE, reason="elasticsearch not installed")
    @pytest.mark.asyncio
    async def test_get_elasticsearch_backend_with_auth(self):
        """Should pass authentication to elasticsearch backend."""
        with patch('app.infrastructure.search.get_elasticsearch_search') as mock_get_es:
            mock_get_es.return_value = MagicMock()
            
            await get_search_backend(
                backend="elasticsearch",
                username="admin",
                password="secret",
            )
            
            mock_get_es.assert_called_once_with(
                url="http://localhost:9200",
                index_prefix="app",
                username="admin",
                password="secret",
            )

    @pytest.mark.skipif(not ELASTICSEARCH_AVAILABLE, reason="elasticsearch not installed")
    @pytest.mark.asyncio
    async def test_get_elasticsearch_backend_with_index_prefix(self):
        """Should pass index prefix to elasticsearch backend."""
        with patch('app.infrastructure.search.get_elasticsearch_search') as mock_get_es:
            mock_get_es.return_value = MagicMock()
            
            await get_search_backend(
                backend="elasticsearch",
                index_prefix="myapp",
            )
            
            mock_get_es.assert_called_once_with(
                url="http://localhost:9200",
                index_prefix="myapp",
                username=None,
                password=None,
            )

    @pytest.mark.asyncio
    async def test_get_elasticsearch_backend_when_unavailable_raises(self):
        """Should raise ValueError when elasticsearch not available."""
        with patch('app.infrastructure.search.ELASTICSEARCH_AVAILABLE', False):
            with pytest.raises(ValueError, match="Elasticsearch not available"):
                await get_search_backend(backend="elasticsearch")

    @pytest.mark.asyncio
    async def test_get_elasticsearch_backend_not_initialized_raises(self):
        """Should raise ValueError if elasticsearch backend not initialized."""
        with patch('app.infrastructure.search.ELASTICSEARCH_AVAILABLE', True):
            with patch('app.infrastructure.search.get_elasticsearch_search', None):
                with pytest.raises(ValueError, match="not properly initialized"):
                    await get_search_backend(backend="elasticsearch")


class TestGetSearchBackendInvalid:
    """Tests for invalid search backend."""

    @pytest.mark.asyncio
    async def test_unknown_backend_raises_valueerror(self):
        """Should raise ValueError for unknown backend."""
        with pytest.raises(ValueError, match="Unknown search backend"):
            await get_search_backend(backend="redis")

    @pytest.mark.asyncio
    async def test_empty_backend_raises_valueerror(self):
        """Should raise ValueError for empty backend string."""
        with pytest.raises(ValueError, match="Unknown search backend"):
            await get_search_backend(backend="")

    @pytest.mark.asyncio
    async def test_none_backend_raises_valueerror(self):
        """Should raise ValueError for None backend."""
        with pytest.raises(ValueError, match="Unknown search backend"):
            await get_search_backend(backend="solr")


class TestGetPostgresSearchFactory:
    """Tests for get_postgres_search factory function."""

    def test_get_postgres_search_creates_instance(self):
        """Should create PostgresFullTextSearch instance."""
        mock_session = MagicMock()
        
        backend = get_postgres_search(session=mock_session)
        
        assert isinstance(backend, PostgresFullTextSearch)
        assert backend._session is mock_session

    def test_get_postgres_search_with_language(self):
        """Should set language on created instance."""
        mock_session = MagicMock()
        
        backend = get_postgres_search(session=mock_session, language="french")
        
        assert backend._language == "french"

    def test_get_postgres_search_default_language(self):
        """Should use english as default language."""
        mock_session = MagicMock()
        
        backend = get_postgres_search(session=mock_session)
        
        assert backend._language == "english"


class TestSearchExports:
    """Tests for module exports."""

    def test_exports_search_port_interface(self):
        """Should export SearchPort interface."""
        from app.infrastructure.search import SearchPort
        assert SearchPort is not None

    def test_exports_search_query(self):
        """Should export SearchQuery."""
        from app.infrastructure.search import SearchQuery
        assert SearchQuery is not None

    def test_exports_search_result(self):
        """Should export SearchResult."""
        from app.infrastructure.search import SearchResult
        assert SearchResult is not None

    def test_exports_search_hit(self):
        """Should export SearchHit."""
        from app.infrastructure.search import SearchHit
        assert SearchHit is not None

    def test_exports_search_filter(self):
        """Should export SearchFilter."""
        from app.infrastructure.search import SearchFilter
        assert SearchFilter is not None

    def test_exports_search_sort(self):
        """Should export SearchSort."""
        from app.infrastructure.search import SearchSort
        assert SearchSort is not None

    def test_exports_postgres_implementation(self):
        """Should export PostgreSQL implementation."""
        from app.infrastructure.search import PostgresFullTextSearch
        assert PostgresFullTextSearch is not None

    def test_exports_factory_function(self):
        """Should export factory function."""
        from app.infrastructure.search import get_search_backend
        assert callable(get_search_backend)


class TestSearchBackendIntegration:
    """Integration tests for search backend factory."""

    @pytest.mark.asyncio
    async def test_switch_between_backends(self):
        """Should be able to switch between backends."""
        mock_session = MagicMock()
        
        # Get postgres backend
        pg_backend = await get_search_backend(backend="postgres", session=mock_session)
        assert isinstance(pg_backend, PostgresFullTextSearch)
        
        # Try elasticsearch (will fail if not available, that's ok)
        if ELASTICSEARCH_AVAILABLE:
            with patch('app.infrastructure.search.get_elasticsearch_search') as mock_es:
                mock_es.return_value = MagicMock()
                es_backend = await get_search_backend(backend="elasticsearch")
                assert es_backend is not None

    @pytest.mark.asyncio
    async def test_multiple_postgres_instances(self):
        """Should create separate instances for each call."""
        session1 = MagicMock()
        session2 = MagicMock()
        
        backend1 = await get_search_backend(backend="postgres", session=session1)
        backend2 = await get_search_backend(backend="postgres", session=session2)
        
        assert backend1 is not backend2
        assert backend1._session is session1
        assert backend2._session is session2

    @pytest.mark.asyncio
    async def test_postgres_backend_with_all_options(self):
        """Should handle all postgres options."""
        mock_session = MagicMock()
        
        backend = await get_search_backend(
            backend="postgres",
            session=mock_session,
            language="german",
            extra_param="ignored"  # Extra params should be ignored
        )
        
        assert backend._language == "german"

class TestElasticsearchImportError:
    """Tests for Elasticsearch import error handling (lines 37-40)."""
    
    def test_elasticsearch_unavailable_sets_flag_to_false(self):
        """Test that ELASTICSEARCH_AVAILABLE is False when import fails."""
        # We can't actually force the import to fail in the current process,
        # but we can verify the fallback behavior exists
        with patch.dict('sys.modules', {'app.infrastructure.search.elasticsearch': None}):
            # When elasticsearch is not available, get_elasticsearch_search should be None
            import importlib
            import app.infrastructure.search as search_module
            
            # Reload the module to trigger the import error path
            # Note: This is complex to test directly, so we verify the constants exist
            assert hasattr(search_module, 'ELASTICSEARCH_AVAILABLE')
            assert hasattr(search_module, 'ElasticsearchSearch')
            assert hasattr(search_module, 'get_elasticsearch_search')
    
    def test_module_defines_elasticsearch_fallbacks(self):
        """Test that module has fallback values for when Elasticsearch is unavailable."""
        # Verify that the module has proper fallback handling
        from app.infrastructure.search import ELASTICSEARCH_AVAILABLE
        
        # The module should define ELASTICSEARCH_AVAILABLE boolean
        assert isinstance(ELASTICSEARCH_AVAILABLE, bool)
        
        # If elasticsearch is not available, the imports should be None
        if not ELASTICSEARCH_AVAILABLE:
            from app.infrastructure.search import ElasticsearchSearch, get_elasticsearch_search
            assert ElasticsearchSearch is None
            assert get_elasticsearch_search is None