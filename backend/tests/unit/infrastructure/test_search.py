# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for search infrastructure.

Tests for search module initialization and data structures.
"""

import pytest

from app.domain.ports.search import (
    BulkIndexResult,
    IndexDocument,
    SearchFilter,
    SearchHighlight,
    SearchHit,
    SearchIndex,
    SearchQuery,
    SearchResult,
    SearchSort,
    SortOrder,
)


class TestSearchQuery:
    """Tests for SearchQuery data structure."""

    def test_default_values(self) -> None:
        """Test SearchQuery default values."""
        query = SearchQuery(query="test", index=SearchIndex.USERS)

        assert query.query == "test"
        assert query.index == SearchIndex.USERS
        assert query.page == 1
        assert query.page_size == 20

    def test_with_pagination(self) -> None:
        """Test SearchQuery with custom pagination."""
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
            page=3,
            page_size=50,
        )

        assert query.page == 3
        assert query.page_size == 50

    def test_with_fuzzy(self) -> None:
        """Test SearchQuery with fuzzy search settings."""
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
            fuzzy=True,
        )

        assert query.fuzzy is True


class TestSearchResult:
    """Tests for SearchResult data structure."""

    def test_empty_result(self) -> None:
        """Test empty SearchResult."""
        result = SearchResult(
            hits=[],
            total=0,
            page=1,
            page_size=20,
        )

        assert result.hits == []
        assert result.total == 0
        assert result.has_next is False

    def test_with_hits(self) -> None:
        """Test SearchResult with hits."""
        hits = [
            SearchHit(id="1", score=1.0, source={"name": "Test"}),
            SearchHit(id="2", score=0.9, source={"name": "Test 2"}),
        ]

        result = SearchResult(
            hits=hits,
            total=2,
            page=1,
            page_size=20,
        )

        assert len(result.hits) == 2
        assert result.total == 2

    def test_has_next_true(self) -> None:
        """Test has_next is True when more results available."""
        result = SearchResult(
            hits=[SearchHit(id="1", score=1.0, source={})],
            total=100,
            page=1,
            page_size=20,
        )

        assert result.has_next is True

    def test_has_next_false(self) -> None:
        """Test has_next is False on last page."""
        result = SearchResult(
            hits=[SearchHit(id="1", score=1.0, source={})],
            total=1,
            page=1,
            page_size=20,
        )

        assert result.has_next is False

    def test_has_previous_false_on_first_page(self) -> None:
        """Test has_previous is False on first page."""
        result = SearchResult(
            hits=[],
            total=100,
            page=1,
            page_size=20,
        )

        assert result.has_previous is False

    def test_has_previous_true_on_later_page(self) -> None:
        """Test has_previous is True on page 2+."""
        result = SearchResult(
            hits=[],
            total=100,
            page=2,
            page_size=20,
        )

        assert result.has_previous is True

    def test_total_pages_calculation(self) -> None:
        """Test total pages calculation."""
        result = SearchResult(
            hits=[],
            total=45,
            page=1,
            page_size=20,
        )

        assert result.total_pages == 3  # 45/20 = 3 pages


class TestSearchHit:
    """Tests for SearchHit data structure."""

    def test_basic_hit(self) -> None:
        """Test basic SearchHit."""
        hit = SearchHit(
            id="123",
            score=0.95,
            source={"name": "Test User"},
        )

        assert hit.id == "123"
        assert hit.score == 0.95
        assert hit.source["name"] == "Test User"

    def test_hit_with_highlight(self) -> None:
        """Test SearchHit with highlights."""
        hit = SearchHit(
            id="123",
            score=0.95,
            source={"name": "Test User"},
            highlights={"name": ["<mark>Test</mark> User"]},
        )

        assert hit.highlights is not None
        assert "name" in hit.highlights


class TestSearchFilter:
    """Tests for SearchFilter data structure."""

    def test_term_filter(self) -> None:
        """Test term filter."""
        filter = SearchFilter(
            field="status",
            value="active",
            operator="eq",
        )

        assert filter.field == "status"
        assert filter.value == "active"
        assert filter.operator == "eq"

    def test_default_operator(self) -> None:
        """Test default operator is eq."""
        filter = SearchFilter(field="status", value="active")

        assert filter.operator == "eq"


class TestSearchSort:
    """Tests for SearchSort data structure."""

    def test_ascending_sort(self) -> None:
        """Test ascending sort."""
        sort = SearchSort(
            field="name",
            order=SortOrder.ASC,
        )

        assert sort.field == "name"
        assert sort.order == SortOrder.ASC

    def test_default_order_is_desc(self) -> None:
        """Test default order is descending."""
        sort = SearchSort(field="created_at")

        assert sort.order == SortOrder.DESC


class TestSortOrder:
    """Tests for SortOrder enum."""

    def test_sort_order_values(self) -> None:
        """Test sort order enum values."""
        assert SortOrder.ASC.value == "asc"
        assert SortOrder.DESC.value == "desc"


class TestSearchIndex:
    """Tests for SearchIndex enum."""

    def test_index_values(self) -> None:
        """Test search index enum values."""
        assert SearchIndex.USERS.value == "users"
        assert SearchIndex.AUDIT_LOGS.value == "audit_logs"


class TestIndexDocument:
    """Tests for IndexDocument data structure."""

    def test_index_document(self) -> None:
        """Test index document."""
        doc = IndexDocument(
            id="123",
            index=SearchIndex.USERS,
            data={"name": "Test User", "email": "test@example.com"},
        )

        assert doc.id == "123"
        assert doc.index == SearchIndex.USERS
        assert doc.data["name"] == "Test User"


class TestBulkIndexResult:
    """Tests for BulkIndexResult data structure."""

    def test_successful_bulk(self) -> None:
        """Test successful bulk indexing result."""
        result = BulkIndexResult(
            indexed=100,
            failed=0,
            errors=[],
        )

        assert result.indexed == 100
        assert result.failed == 0
        assert result.errors == []

    def test_partial_failure_bulk(self) -> None:
        """Test bulk indexing with failures."""
        result = BulkIndexResult(
            indexed=95,
            failed=5,
            errors=["Document 1 failed", "Document 2 failed"],
        )

        assert result.indexed == 95
        assert result.failed == 5
        assert len(result.errors) == 2


class TestSearchHighlight:
    """Tests for SearchHighlight data structure."""

    def test_default_values(self) -> None:
        """Test default highlight values."""
        highlight = SearchHighlight(fields=["name", "content"])

        assert highlight.fields == ["name", "content"]
        assert highlight.pre_tag == "<mark>"
        assert highlight.post_tag == "</mark>"
        assert highlight.fragment_size == 150
        assert highlight.number_of_fragments == 3

    def test_custom_tags(self) -> None:
        """Test custom highlight tags."""
        highlight = SearchHighlight(
            fields=["name"],
            pre_tag="<em>",
            post_tag="</em>",
        )

        assert highlight.pre_tag == "<em>"
        assert highlight.post_tag == "</em>"


class TestSearchModule:
    """Tests for search module initialization."""

    def test_postgres_search_export(self) -> None:
        """Test PostgresFullTextSearch is exported."""
        from app.infrastructure.search import PostgresFullTextSearch

        assert PostgresFullTextSearch is not None

    def test_get_postgres_search_export(self) -> None:
        """Test get_postgres_search is exported."""
        from app.infrastructure.search import get_postgres_search

        assert callable(get_postgres_search)


class TestGetSearchBackend:
    """Tests for get_search_backend factory function."""

    @pytest.mark.asyncio
    async def test_postgres_backend_with_session(self) -> None:
        """Test postgres backend returns search port."""
        from unittest.mock import MagicMock

        from app.domain.ports.search import SearchPort
        from app.infrastructure.search import get_search_backend

        mock_session = MagicMock()

        result = await get_search_backend(session=mock_session, language="spanish")

        assert isinstance(result, SearchPort)
