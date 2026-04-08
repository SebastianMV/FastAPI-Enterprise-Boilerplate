# Copyright (c) 2025-2026 Sebastian Munoz
# Licensed under the Apache License, Version 2.0

"""
Search infrastructure package.

Provides full-text search using PostgreSQL FTS (built-in, no extra dependencies).
"""

from typing import Any

from app.domain.ports.search import (
    BulkIndexResult,
    IndexDocument,
    SearchFilter,
    SearchHighlight,
    SearchHit,
    SearchIndex,
    SearchPort,
    SearchQuery,
    SearchResult,
    SearchSort,
    SortOrder,
)
from app.infrastructure.search.postgres_fts import (
    PostgresFullTextSearch,
    get_postgres_search,
)

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
    # Factory
    "get_search_backend",
]


async def get_search_backend(
    session: Any,
    language: str = "english",
) -> SearchPort:
    """
    Get search backend (PostgreSQL FTS).

    Args:
        session: SQLAlchemy async session
        language: PostgreSQL text search configuration (default: english)

    Returns:
        PostgresFullTextSearch instance
    """
    return get_postgres_search(session=session, language=language)
