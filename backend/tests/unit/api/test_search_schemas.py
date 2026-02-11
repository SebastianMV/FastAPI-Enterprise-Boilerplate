# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Tests for search endpoint schemas and validation."""

from __future__ import annotations

from app.api.v1.endpoints.search import (
    HealthResponse,
    SearchFilterRequest,
    SearchHitResponse,
    SearchRequest,
    SearchResponse,
    SearchSortRequest,
    SuggestResponse,
)


class TestSearchFilterRequest:
    """Tests for SearchFilterRequest schema."""

    def test_filter_basic(self) -> None:
        """Test basic filter."""
        data = SearchFilterRequest(  # type: ignore[call-arg]
            field="status",
            value="active",
        )
        assert data.field == "status"
        assert data.value == "active"
        assert data.operator == "eq"

    def test_filter_with_operator(self) -> None:
        """Test filter with operator."""
        data = SearchFilterRequest(
            field="age",
            value=18,
            operator="gte",
        )
        assert data.operator == "gte"


class TestSearchSortRequest:
    """Tests for SearchSortRequest schema."""

    def test_sort_default_order(self) -> None:
        """Test sort with default order."""
        data = SearchSortRequest(  # type: ignore[call-arg]
            field="created_at",
        )
        assert data.field == "created_at"
        assert data.order == "desc"

    def test_sort_asc_order(self) -> None:
        """Test sort with ascending order."""
        data = SearchSortRequest(
            field="name",
            order="asc",
        )
        assert data.order == "asc"


class TestSearchRequest:
    """Tests for SearchRequest schema."""

    def test_search_request_basic(self) -> None:
        """Test basic search request."""
        data = SearchRequest(  # type: ignore[call-arg]
            query="test search",
            index="users",
        )
        assert data.query == "test search"
        assert data.index == "users"

    def test_search_request_with_filters(self) -> None:
        """Test search request with filters."""
        filter_req = SearchFilterRequest(field="status", value="active", operator="eq")
        data = SearchRequest(  # type: ignore[call-arg]
            query="user",
            index="users",
            filters=[filter_req],
            page_size=50,
        )
        assert len(data.filters) == 1
        assert data.page_size == 50

    def test_search_request_with_pagination(self) -> None:
        """Test search request with pagination."""
        data = SearchRequest(  # type: ignore[call-arg]
            query="document",
            index="documents",
            page=2,
            page_size=20,
        )
        assert data.page == 2

    def test_search_request_fuzzy_default(self) -> None:
        """Test search request fuzzy default."""
        data = SearchRequest(  # type: ignore[call-arg]
            query="test",
            index="users",
        )
        assert data.fuzzy is True


class TestSearchHitResponse:
    """Tests for SearchHitResponse schema."""

    def test_search_hit_basic(self) -> None:
        """Test basic search hit."""
        data = SearchHitResponse(
            id="123",
            score=0.95,
            source={"name": "John", "email": "john@example.com"},
        )
        assert data.id == "123"
        assert data.score == 0.95

    def test_search_hit_with_highlights(self) -> None:
        """Test search hit with highlights."""
        data = SearchHitResponse(
            id="456",
            score=0.8,
            source={"content": "Test document"},
            highlights={"content": ["This is <em>test</em> content"]},
        )
        assert "content" in data.highlights


class TestSearchResponse:
    """Tests for SearchResponse schema."""

    def test_search_response_empty(self) -> None:
        """Test empty search response."""
        data = SearchResponse(
            hits=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
            has_next=False,
            has_previous=False,
            took_ms=15.5,
        )
        assert data.hits == []
        assert data.total == 0

    def test_search_response_with_results(self) -> None:
        """Test search response with results."""
        hit1 = SearchHitResponse(
            id="1",
            score=0.9,
            source={"name": "User 1"},
        )
        hit2 = SearchHitResponse(
            id="2",
            score=0.85,
            source={"name": "User 2"},
        )
        data = SearchResponse(
            hits=[hit1, hit2],
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
            has_next=False,
            has_previous=False,
            took_ms=10.2,
            max_score=0.9,
        )
        assert len(data.hits) == 2
        assert data.max_score == 0.9


class TestSuggestResponse:
    """Tests for SuggestResponse schema."""

    def test_suggest_response(self) -> None:
        """Test suggest response."""
        data = SuggestResponse(
            suggestions=["test suggestion", "test query"],
        )
        assert len(data.suggestions) == 2

    def test_suggest_response_empty(self) -> None:
        """Test empty suggest response."""
        data = SuggestResponse(suggestions=[])
        assert data.suggestions == []


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_health_response_healthy(self) -> None:
        """Test healthy response."""
        data = HealthResponse(
            status="healthy",
            backend="postgres",
        )
        assert data.status == "healthy"

    def test_health_response_with_details(self) -> None:
        """Test health response with details."""
        data = HealthResponse(
            status="healthy",
            backend="postgres",
            details={"language": "english"},
        )
        assert "language" in data.details


class TestSearchRouter:
    """Tests for search router configuration."""

    def test_router_exists(self) -> None:
        """Test router exists."""
        from app.api.v1.endpoints.search import router

        assert router is not None

    def test_router_has_routes(self) -> None:
        """Test router has routes."""
        from app.api.v1.endpoints.search import router

        assert len(router.routes) > 0
