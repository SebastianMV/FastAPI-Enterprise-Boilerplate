# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Search infrastructure package.

Provides full-text search implementations:
- PostgreSQL FTS (built-in)
- Elasticsearch (optional)
"""

from typing import Any

from app.domain.ports.search import (
    SearchPort,
    SearchQuery,
    SearchResult,
    SearchHit,
    SearchFilter,
    SearchSort,
    SearchHighlight,
    SearchIndex,
    SortOrder,
    IndexDocument,
    BulkIndexResult,
)
from app.infrastructure.search.postgres_fts import PostgresFullTextSearch, get_postgres_search


# Optional Elasticsearch import
try:
    from app.infrastructure.search.elasticsearch import (
        ElasticsearchSearch,
        get_elasticsearch_search,
    )
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    ElasticsearchSearch = None  # type: ignore
    get_elasticsearch_search = None  # type: ignore


__all__ = [
    # Port interface
    "SearchPort",
    "SearchQuery",
    "SearchResult",
    "SearchHit",
    "SearchFilter",
    "SearchSort",
    "SearchHighlight",
    "SearchIndex",
    "SortOrder",
    "IndexDocument",
    "BulkIndexResult",
    # PostgreSQL implementation
    "PostgresFullTextSearch",
    "get_postgres_search",
    # Elasticsearch implementation
    "ElasticsearchSearch",
    "get_elasticsearch_search",
    "ELASTICSEARCH_AVAILABLE",
    # Factory
    "get_search_backend",
]


async def get_search_backend(
    backend: str = "postgres",
    session: Any = None,
    **kwargs,
) -> SearchPort:
    """
    Get search backend based on configuration.
    
    Args:
        backend: "postgres" or "elasticsearch"
        session: SQLAlchemy session (required for postgres)
        **kwargs: Additional backend-specific arguments
        
    Returns:
        SearchPort implementation
        
    Raises:
        ValueError: If backend is invalid or not available
    """
    if backend == "postgres":
        if session is None:
            raise ValueError("SQLAlchemy session required for PostgreSQL FTS")
        
        language = kwargs.get("language", "english")
        return get_postgres_search(session=session, language=language)
    
    elif backend == "elasticsearch":
        if not ELASTICSEARCH_AVAILABLE:
            raise ValueError(
                "Elasticsearch not available. "
                "Install with: pip install elasticsearch[async]"
            )
        
        if get_elasticsearch_search is None:
            raise ValueError("Elasticsearch backend not properly initialized")
        
        return get_elasticsearch_search(
            url=kwargs.get("url", "http://localhost:9200"),
            index_prefix=kwargs.get("index_prefix", "app"),
            username=kwargs.get("username"),
            password=kwargs.get("password"),
        )
    
    else:
        raise ValueError(f"Unknown search backend: {backend}")
