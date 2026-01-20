"""
Additional tests for search/__init__.py to improve coverage.

Tests the get_search_backend factory function with different backends and error conditions.
"""

import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session

from app.infrastructure.search import (
    get_search_backend,
    ELASTICSEARCH_AVAILABLE,
    PostgresFullTextSearch,
)


class TestGetSearchBackendPostgres:
    """Tests for get_search_backend with Postgres backend."""

    @pytest.mark.asyncio
    async def test_postgres_backend_with_default_language(self) -> None:
        """Test Postgres backend with default language."""
        mock_session = AsyncMock(spec=Session)
        
        backend = await get_search_backend(backend="postgres", session=mock_session)
        
        assert backend is not None
        assert isinstance(backend, PostgresFullTextSearch)

    @pytest.mark.asyncio
    async def test_postgres_backend_with_custom_language(self) -> None:
        """Test Postgres backend with custom language."""
        mock_session = AsyncMock(spec=Session)
        
        backend = await get_search_backend(
            backend="postgres",
            session=mock_session,
            language="spanish"
        )
        
        assert backend is not None
        assert isinstance(backend, PostgresFullTextSearch)

    @pytest.mark.asyncio
    async def test_postgres_backend_without_session_raises_error(self) -> None:
        """Test that Postgres backend requires a session."""
        with pytest.raises(ValueError) as exc_info:
            await get_search_backend(backend="postgres", session=None)
        
        assert "SQLAlchemy session required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_postgres_backend_missing_session_raises_error(self) -> None:
        """Test that Postgres backend raises error when session is missing."""
        with pytest.raises(ValueError) as exc_info:
            await get_search_backend(backend="postgres")
        
        assert "SQLAlchemy session required" in str(exc_info.value)


class TestGetSearchBackendElasticsearch:
    """Tests for get_search_backend with Elasticsearch backend."""

    @pytest.mark.asyncio
    async def test_elasticsearch_available_check(self) -> None:
        """Test that ELASTICSEARCH_AVAILABLE is a boolean."""
        assert isinstance(ELASTICSEARCH_AVAILABLE, bool)

    @pytest.mark.asyncio
    async def test_elasticsearch_backend_not_available(self) -> None:
        """Test Elasticsearch backend raises error when not available."""
        # Temporarily disable Elasticsearch
        with patch("app.infrastructure.search.ELASTICSEARCH_AVAILABLE", False):
            with pytest.raises(ValueError) as exc_info:
                await get_search_backend(backend="elasticsearch")
            
            assert "Elasticsearch not available" in str(exc_info.value)
            assert "pip install elasticsearch" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.skipif(not ELASTICSEARCH_AVAILABLE, reason="Elasticsearch not installed")
    async def test_elasticsearch_backend_with_defaults(self) -> None:
        """Test Elasticsearch backend with default parameters."""
        from app.infrastructure.search import ElasticsearchSearch
        
        backend = await get_search_backend(backend="elasticsearch")
        
        assert backend is not None
        assert isinstance(backend, ElasticsearchSearch)

    @pytest.mark.asyncio
    @pytest.mark.skipif(not ELASTICSEARCH_AVAILABLE, reason="Elasticsearch not installed")
    async def test_elasticsearch_backend_with_custom_url(self) -> None:
        """Test Elasticsearch backend with custom URL."""
        from app.infrastructure.search import ElasticsearchSearch
        
        backend = await get_search_backend(
            backend="elasticsearch",
            url="http://custom:9200",
            index_prefix="custom",
        )
        
        assert backend is not None
        assert isinstance(backend, ElasticsearchSearch)

    @pytest.mark.asyncio
    @pytest.mark.skipif(not ELASTICSEARCH_AVAILABLE, reason="Elasticsearch not installed")
    async def test_elasticsearch_backend_with_auth(self) -> None:
        """Test Elasticsearch backend with authentication."""
        from app.infrastructure.search import ElasticsearchSearch
        
        backend = await get_search_backend(
            backend="elasticsearch",
            url="http://localhost:9200",
            username="admin",
            password="secret",
            index_prefix="secure",
        )
        
        assert backend is not None
        assert isinstance(backend, ElasticsearchSearch)

    @pytest.mark.asyncio
    async def test_elasticsearch_get_function_none_when_not_available(self) -> None:
        """Test that get_elasticsearch_search is None when not available."""
        with patch("app.infrastructure.search.ELASTICSEARCH_AVAILABLE", True):
            with patch("app.infrastructure.search.get_elasticsearch_search", None):
                with pytest.raises(ValueError) as exc_info:
                    await get_search_backend(backend="elasticsearch")
                
                # Should fail with "not properly initialized"
                assert "not properly initialized" in str(exc_info.value)


class TestGetSearchBackendInvalidBackend:
    """Tests for invalid backend types."""

    @pytest.mark.asyncio
    async def test_invalid_backend_type(self) -> None:
        """Test that invalid backend type raises an error."""
        with pytest.raises(ValueError) as exc_info:
            await get_search_backend(backend="invalid_backend")
        
        assert "Unknown search backend" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_backend_string(self) -> None:
        """Test empty backend string."""
        with pytest.raises(ValueError) as exc_info:
            await get_search_backend(backend="")
        
        assert "Unknown search backend" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_none_backend(self) -> None:
        """Test None as backend."""
        with pytest.raises((ValueError, AttributeError, TypeError)):
            await get_search_backend(backend=None)  # type: ignore

    @pytest.mark.asyncio
    async def test_redis_backend_unsupported(self) -> None:
        """Test unsupported backend type."""
        with pytest.raises(ValueError) as exc_info:
            await get_search_backend(backend="redis")
        
        assert "Unknown search backend: redis" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mongo_backend_unsupported(self) -> None:
        """Test another unsupported backend type."""
        with pytest.raises(ValueError) as exc_info:
            await get_search_backend(backend="mongodb")
        
        assert "Unknown search backend" in str(exc_info.value)
