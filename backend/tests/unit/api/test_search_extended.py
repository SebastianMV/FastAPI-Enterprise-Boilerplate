# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Extended unit tests for Search API endpoints.

Tests for search endpoint schemas and functionality.
"""


import pytest
from pydantic import ValidationError


class TestSearchFilterRequest:
    """Tests for SearchFilterRequest schema."""

    def test_search_filter_eq(self) -> None:
        """Test equality filter."""
        from app.api.v1.endpoints.search import SearchFilterRequest

        filter_req = SearchFilterRequest(
            field="status",
            value="active",
            operator="eq",
        )

        assert filter_req.field == "status"
        assert filter_req.operator == "eq"

    def test_search_filter_operators(self) -> None:
        """Test various filter operators."""
        from app.api.v1.endpoints.search import SearchFilterRequest

        operators = ["eq", "ne", "gt", "gte", "lt", "lte", "in", "contains"]

        for op in operators:
            filter_req = SearchFilterRequest(
                field="test_field",
                value="test_value",
                operator=op,
            )
            assert filter_req.operator == op

    def test_search_filter_default_operator(self) -> None:
        """Test default operator is eq."""
        from app.api.v1.endpoints.search import SearchFilterRequest

        filter_req = SearchFilterRequest(  # type: ignore[call-arg]
            field="status",
            value="active",
        )

        assert filter_req.operator == "eq"

    def test_search_filter_in_operator_with_list(self) -> None:
        """Test in operator with list value."""
        from app.api.v1.endpoints.search import SearchFilterRequest

        filter_req = SearchFilterRequest(
            field="category",
            value=["tech", "science", "art"],
            operator="in",
        )

        assert filter_req.value == ["tech", "science", "art"]


class TestSearchSortRequest:
    """Tests for SearchSortRequest schema."""

    def test_search_sort_desc(self) -> None:
        """Test descending sort."""
        from app.api.v1.endpoints.search import SearchSortRequest

        sort_req = SearchSortRequest(
            field="created_at",
            order="desc",
        )

        assert sort_req.field == "created_at"
        assert sort_req.order == "desc"

    def test_search_sort_asc(self) -> None:
        """Test ascending sort."""
        from app.api.v1.endpoints.search import SearchSortRequest

        sort_req = SearchSortRequest(
            field="title",
            order="asc",
        )

        assert sort_req.order == "asc"

    def test_search_sort_default(self) -> None:
        """Test default sort order is desc."""
        from app.api.v1.endpoints.search import SearchSortRequest

        sort_req = SearchSortRequest(field="score")  # type: ignore[call-arg]

        assert sort_req.order == "desc"


class TestSearchRequest:
    """Tests for SearchRequest schema."""

    def test_search_request_minimal(self) -> None:
        """Test minimal search request."""
        from app.api.v1.endpoints.search import SearchRequest

        request = SearchRequest(  # type: ignore[call-arg]
            query="test query",
            index="users",
        )

        assert request.query == "test query"
        assert request.index == "users"
        assert request.page == 1
        assert request.page_size == 20
        assert request.fuzzy is True

    def test_search_request_full(self) -> None:
        """Test full search request with all fields."""
        from app.api.v1.endpoints.search import (
            SearchFilterRequest,
            SearchRequest,
            SearchSortRequest,
        )

        request = SearchRequest(
            query="search term",
            index="posts",
            filters=[
                SearchFilterRequest(field="status", value="published", operator="eq"),
                SearchFilterRequest(field="category", value="tech", operator="eq"),
            ],
            sort=[
                SearchSortRequest(field="created_at", order="desc"),
            ],
            highlight_fields=["title", "content"],
            page=2,
            page_size=50,
            fuzzy=False,
        )

        assert len(request.filters) == 2
        assert len(request.sort) == 1
        assert request.page == 2
        assert request.fuzzy is False

    def test_search_request_empty_query_fails(self) -> None:
        """Test empty query fails validation."""
        from app.api.v1.endpoints.search import SearchRequest

        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="", index="users")  # type: ignore[call-arg]

        assert "query" in str(exc_info.value)

    def test_search_request_query_too_long_fails(self) -> None:
        """Test query too long fails validation."""
        from app.api.v1.endpoints.search import SearchRequest

        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(  # type: ignore[call-arg]
                query="x" * 501,  # Over 500 char limit
                index="users",
            )

        assert "query" in str(exc_info.value)

    def test_search_request_invalid_page_fails(self) -> None:
        """Test invalid page number fails."""
        from app.api.v1.endpoints.search import SearchRequest

        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(  # type: ignore[call-arg]
                query="test",
                index="users",
                page=0,  # Must be >= 1
            )

        assert "page" in str(exc_info.value)

    def test_search_request_page_size_limits(self) -> None:
        """Test page size limits."""
        from app.api.v1.endpoints.search import SearchRequest

        # Valid page size
        request = SearchRequest(  # type: ignore[call-arg]
            query="test",
            index="users",
            page_size=100,  # Max allowed
        )
        assert request.page_size == 100

        # Invalid page size
        with pytest.raises(ValidationError):
            SearchRequest(  # type: ignore[call-arg]
                query="test",
                index="users",
                page_size=101,  # Over limit
            )


class TestSearchHitResponse:
    """Tests for SearchHitResponse schema."""

    def test_search_hit_response(self) -> None:
        """Test search hit response."""
        from app.api.v1.endpoints.search import SearchHitResponse

        hit = SearchHitResponse(
            id="doc-123",
            score=0.95,
            source={"title": "Test Doc", "content": "Test content"},
            highlights={"title": ["<em>Test</em> Doc"]},
            matched_fields=["title"],
        )

        assert hit.id == "doc-123"
        assert hit.score == 0.95
        assert "title" in hit.source

    def test_search_hit_response_minimal(self) -> None:
        """Test search hit with minimal fields."""
        from app.api.v1.endpoints.search import SearchHitResponse

        hit = SearchHitResponse(
            id="doc-456",
            score=0.8,
            source={"id": "456"},
        )

        assert hit.highlights == {}
        assert hit.matched_fields == []


class TestSearchResponse:
    """Tests for SearchResponse schema."""

    def test_search_response_with_hits(self) -> None:
        """Test search response with results."""
        from app.api.v1.endpoints.search import SearchHitResponse, SearchResponse

        hits = [
            SearchHitResponse(
                id=f"doc-{i}",
                score=0.9 - (i * 0.1),
                source={"title": f"Document {i}"},
            )
            for i in range(3)
        ]

        response = SearchResponse(
            hits=hits,
            total=100,
            page=1,
            page_size=10,
            total_pages=10,
            has_next=True,
            has_previous=False,
            took_ms=15.5,
        )

        assert len(response.hits) == 3
        assert response.total == 100
        assert response.page == 1
        assert response.total_pages == 10
        assert response.has_next is True
        assert response.has_previous is False

    def test_search_response_empty(self) -> None:
        """Test empty search response."""
        from app.api.v1.endpoints.search import SearchResponse

        response = SearchResponse(
            hits=[],
            total=0,
            page=1,
            page_size=10,
            total_pages=0,
            has_next=False,
            has_previous=False,
            took_ms=1.2,
        )

        assert len(response.hits) == 0
        assert response.total == 0
        assert response.total_pages == 0


class TestSearchIndex:
    """Tests for SearchIndex enum."""

    def test_search_index_values(self) -> None:
        """Test search index values."""
        from app.domain.ports.search import SearchIndex

        assert SearchIndex.USERS.value == "users"
        assert SearchIndex.AUDIT_LOGS.value == "audit_logs"

    def test_search_index_list(self) -> None:
        """Test listing search indexes."""
        from app.domain.ports.search import SearchIndex

        indexes = [i.value for i in SearchIndex]

        assert "users" in indexes
        assert "audit_logs" in indexes


class TestSearchQuery:
    """Tests for SearchQuery domain object."""

    def test_search_query_creation(self) -> None:
        """Test creating SearchQuery."""
        from app.domain.ports.search import SearchIndex, SearchQuery

        query = SearchQuery(
            query="search term",
            index=SearchIndex.USERS,
            page=1,
            page_size=20,
        )

        assert query.query == "search term"
        assert query.index == SearchIndex.USERS

    def test_search_query_with_filters(self) -> None:
        """Test SearchQuery with filters."""
        from app.domain.ports.search import SearchFilter, SearchIndex, SearchQuery

        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
            filters=[
                SearchFilter(field="status", value="published"),
            ],
        )

        assert len(query.filters) == 1


class TestSearchFilter:
    """Tests for SearchFilter domain object."""

    def test_search_filter_creation(self) -> None:
        """Test creating SearchFilter."""
        from app.domain.ports.search import SearchFilter

        filter_obj = SearchFilter(
            field="category",
            value="technology",
            operator="eq",
        )

        assert filter_obj.field == "category"
        assert filter_obj.value == "technology"


class TestSearchSort:
    """Tests for SearchSort domain object."""

    def test_search_sort_creation(self) -> None:
        """Test creating SearchSort."""
        from app.domain.ports.search import SearchSort, SortOrder

        sort = SearchSort(
            field="created_at",
            order=SortOrder.DESC,
        )

        assert sort.field == "created_at"
        assert sort.order == SortOrder.DESC

    def test_sort_order_values(self) -> None:
        """Test SortOrder enum values."""
        from app.domain.ports.search import SortOrder

        assert SortOrder.ASC.value == "asc"
        assert SortOrder.DESC.value == "desc"


class TestSearchHighlight:
    """Tests for SearchHighlight domain object."""

    def test_search_highlight_creation(self) -> None:
        """Test creating SearchHighlight."""
        from app.domain.ports.search import SearchHighlight

        highlight = SearchHighlight(
            fields=["title", "content"],
            pre_tag="<em>",
            post_tag="</em>",
        )

        assert "title" in highlight.fields
        assert highlight.pre_tag == "<em>"


class TestSearchEdgeCases:
    """Tests for edge cases in search."""

    def test_search_filter_numeric_value(self) -> None:
        """Test filter with numeric value."""
        from app.api.v1.endpoints.search import SearchFilterRequest

        filter_req = SearchFilterRequest(
            field="age",
            value=25,
            operator="gte",
        )

        assert filter_req.value == 25

    def test_search_filter_boolean_value(self) -> None:
        """Test filter with boolean value."""
        from app.api.v1.endpoints.search import SearchFilterRequest

        filter_req = SearchFilterRequest(
            field="is_active",
            value=True,
            operator="eq",
        )

        assert filter_req.value is True

    def test_search_request_multiple_sorts(self) -> None:
        """Test request with multiple sort criteria."""
        from app.api.v1.endpoints.search import SearchRequest, SearchSortRequest

        request = SearchRequest(  # type: ignore[call-arg]
            query="test",
            index="posts",
            sort=[
                SearchSortRequest(field="score", order="desc"),
                SearchSortRequest(field="created_at", order="desc"),
                SearchSortRequest(field="title", order="asc"),
            ],
        )

        assert len(request.sort) == 3

    def test_search_hit_with_nested_source(self) -> None:
        """Test search hit with nested source data."""
        from app.api.v1.endpoints.search import SearchHitResponse

        hit = SearchHitResponse(
            id="doc-nested",
            score=0.88,
            source={
                "title": "Nested Doc",
                "author": {
                    "name": "John Doe",
                    "email": "john@example.com",
                },
                "tags": ["python", "fastapi"],
            },
        )

        assert hit.source["author"]["name"] == "John Doe"
        assert len(hit.source["tags"]) == 2
