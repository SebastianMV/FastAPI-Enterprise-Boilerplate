# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for search endpoint schemas."""

import pytest

from app.api.v1.endpoints.search import (
    SearchFilterRequest,
    SearchSortRequest,
    SearchRequest,
    SearchHitResponse,
    SearchResponse,
    SuggestResponse,
)


class TestSearchSchemas:
    """Tests for search schemas."""

    def test_search_filter_request_schema(self):
        """Test SearchFilterRequest schema."""
        filter_req = SearchFilterRequest(
            field="status",
            value="active",
            operator="eq"
        )
        assert filter_req.field == "status"
        assert filter_req.value == "active"
        assert filter_req.operator == "eq"

    def test_search_filter_request_default_operator(self):
        """Test SearchFilterRequest default operator."""
        filter_req = SearchFilterRequest(field="name", value="test")  # type: ignore[call-arg]
        assert filter_req.operator == "eq"

    def test_search_sort_request_schema(self):
        """Test SearchSortRequest schema."""
        sort_req = SearchSortRequest(field="created_at", order="desc")
        assert sort_req.field == "created_at"
        assert sort_req.order == "desc"

    def test_search_sort_request_default_order(self):
        """Test SearchSortRequest default order."""
        sort_req = SearchSortRequest(field="score")  # type: ignore[call-arg]
        assert sort_req.order == "desc"

    def test_search_request_schema(self):
        """Test SearchRequest schema."""
        request = SearchRequest(  # type: ignore[call-arg]
            query="test query",
            index="users"
        )
        assert request.query == "test query"
        assert request.index == "users"
        assert request.page == 1
        assert request.page_size == 20
        assert request.fuzzy is True

    def test_search_request_with_filters(self):
        """Test SearchRequest with filters."""
        request = SearchRequest(
            query="search term",
            index="documents",
            filters=[
                SearchFilterRequest(field="status", value="published", operator="eq"),
                SearchFilterRequest(field="category", value="tech", operator="eq")
            ],
            sort=[
                SearchSortRequest(field="created_at", order="desc")
            ],
            highlight_fields=["title", "content"],
            page=2,
            page_size=50,
            fuzzy=False
        )
        assert len(request.filters) == 2
        assert len(request.sort) == 1
        assert len(request.highlight_fields) == 2
        assert request.page == 2
        assert request.page_size == 50
        assert request.fuzzy is False

    def test_search_hit_response_schema(self):
        """Test SearchHitResponse schema."""
        hit = SearchHitResponse(
            id="doc-123",
            score=0.95,
            source={"title": "Test Doc", "content": "Content here"},
            highlights={"title": ["<em>Test</em> Doc"]},
            matched_fields=["title"]
        )
        assert hit.id == "doc-123"
        assert hit.score == 0.95
        assert "title" in hit.source
        assert "title" in hit.highlights

    def test_search_response_schema(self):
        """Test SearchResponse schema."""
        response = SearchResponse(
            hits=[
                SearchHitResponse(
                    id="1",
                    score=0.9,
                    source={"title": "Result 1"}
                )
            ],
            total=100,
            page=1,
            page_size=20,
            total_pages=5,
            has_next=True,
            has_previous=False,
            took_ms=15.5,
            max_score=0.9,
            suggestions=["alternative query"]
        )
        assert len(response.hits) == 1
        assert response.total == 100
        assert response.has_next is True
        assert response.has_previous is False
        assert response.took_ms == 15.5

    def test_suggest_response_schema(self):
        """Test SuggestResponse schema."""
        response = SuggestResponse(suggestions=["suggestion1", "suggestion2"])
        assert len(response.suggestions) == 2

    def test_search_hit_response_defaults(self):
        """Test SearchHitResponse with defaults."""
        hit = SearchHitResponse(
            id="test",
            score=0.5,
            source={}
        )
        assert hit.highlights == {}
        assert hit.matched_fields == []

    def test_search_request_minimum(self):
        """Test SearchRequest with minimum fields."""
        request = SearchRequest(query="test", index="users")  # type: ignore[call-arg]
        assert request.filters == []
        assert request.sort == []
        assert request.highlight_fields == []

    def test_search_filter_operators(self):
        """Test various filter operators."""
        operators = ["eq", "ne", "gt", "gte", "lt", "lte", "in", "contains"]
        for op in operators:
            filter_req = SearchFilterRequest(field="f", value="v", operator=op)
            assert filter_req.operator == op

    def test_search_sort_orders(self):
        """Test sort orders."""
        asc = SearchSortRequest(field="name", order="asc")
        desc = SearchSortRequest(field="name", order="desc")
        assert asc.order == "asc"
        assert desc.order == "desc"

    def test_suggest_response_empty(self):
        """Test empty SuggestResponse."""
        response = SuggestResponse(suggestions=[])
        assert response.suggestions == []
