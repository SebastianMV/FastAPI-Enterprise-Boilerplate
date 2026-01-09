# Copyright (c) 2025 Sebastián Muñoz
# Licensed under the MIT License

"""
Comprehensive tests for search endpoints to improve coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.api.v1.endpoints.search import (
    search,
    simple_search,
    suggest,
    health,
    list_indices,
    SearchRequest,
    SearchFilterRequest,
    SearchSortRequest,
)
from app.domain.ports.search import SearchIndex


class MockSearchHit:
    """Mock search hit for testing."""
    
    def __init__(self, id: str, score: float = 1.0):
        self.id = id
        self.score = score
        self.source = {"title": "Test", "content": "Test content"}
        self.highlights = {"title": ["<em>Test</em>"]}
        self.matched_fields = ["title"]


class MockSearchResult:
    """Mock search result for testing."""
    
    def __init__(self, total: int = 1, hits: list | None = None):
        self.hits = hits or [MockSearchHit("1")]
        self.total = total
        self.page = 1
        self.page_size = 20
        self.total_pages = 1
        self.has_next = False
        self.has_previous = False
        self.took_ms = 10.5
        self.max_score = 1.0
        self.suggestions = []


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    return user


class TestSearchEndpoint:
    """Tests for search endpoint."""

    @pytest.mark.asyncio
    async def test_search_invalid_index(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test search with invalid index."""
        request = SearchRequest(  # type: ignore[call-arg]
            query="test",
            index="invalid_index",
        )
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await search(
                request=request,
                session=mock_session,
                current_user=mock_user,
                tenant_id=None,
            )
        
        assert exc.value.status_code == 400
        assert "Invalid search index" in exc.value.detail

    @pytest.mark.asyncio
    async def test_search_success(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test successful search."""
        request = SearchRequest(  # type: ignore[call-arg]
            query="test query",
            index="users",
            page=1,
            page_size=20,
        )
        
        mock_result = MockSearchResult(total=1)
        mock_service = AsyncMock()
        mock_service.search.return_value = mock_result
        
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.return_value = mock_service
            
            result = await search(
                request=request,
                session=mock_session,
                current_user=mock_user,
                tenant_id=uuid4(),
            )
            
            assert result.total == 1
            assert len(result.hits) == 1
            assert result.page == 1

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test search with filters."""
        request = SearchRequest(  # type: ignore[call-arg]
            query="test",
            index="users",
            filters=[
                SearchFilterRequest(field="is_active", value=True, operator="eq"),
                SearchFilterRequest(field="created_at", value="2024-01-01", operator="gte"),
            ],
        )
        
        mock_result = MockSearchResult(total=5)
        mock_service = AsyncMock()
        mock_service.search.return_value = mock_result
        
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.return_value = mock_service
            
            result = await search(
                request=request,
                session=mock_session,
                current_user=mock_user,
                tenant_id=None,
            )
            
            assert result.total == 5

    @pytest.mark.asyncio
    async def test_search_with_sorting(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test search with sorting."""
        request = SearchRequest(  # type: ignore[call-arg]
            query="test",
            index="posts",
            sort=[
                SearchSortRequest(field="created_at", order="desc"),
                SearchSortRequest(field="title", order="asc"),
            ],
        )
        
        mock_result = MockSearchResult(total=10)
        mock_service = AsyncMock()
        mock_service.search.return_value = mock_result
        
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.return_value = mock_service
            
            result = await search(
                request=request,
                session=mock_session,
                current_user=mock_user,
                tenant_id=None,
            )
            
            assert result.total == 10

    @pytest.mark.asyncio
    async def test_search_with_highlights(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test search with highlight fields."""
        request = SearchRequest(  # type: ignore[call-arg]
            query="test",
            index="documents",
            highlight_fields=["title", "content", "summary"],
        )
        
        mock_result = MockSearchResult(total=3)
        mock_service = AsyncMock()
        mock_service.search.return_value = mock_result
        
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.return_value = mock_service
            
            result = await search(
                request=request,
                session=mock_session,
                current_user=mock_user,
                tenant_id=None,
            )
            
            assert result.total == 3

    @pytest.mark.asyncio
    async def test_search_backend_error(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test search when backend fails."""
        request = SearchRequest(  # type: ignore[call-arg]
            query="test",
            index="users",
        )
        
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.side_effect = Exception("Backend error")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await search(
                    request=request,
                    session=mock_session,
                    current_user=mock_user,
                    tenant_id=None,
                )
            
            assert exc.value.status_code == 500
            assert "Search failed" in exc.value.detail


class TestSimpleSearchEndpoint:
    """Tests for simple_search endpoint."""

    @pytest.mark.asyncio
    async def test_simple_search_success(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test successful simple search."""
        mock_result = MockSearchResult(total=5)
        mock_service = AsyncMock()
        mock_service.search.return_value = mock_result
        
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.return_value = mock_service
            
            result = await simple_search(
                session=mock_session,
                current_user=mock_user,
                tenant_id=None,
                q="test query",
                index="posts",
                page=1,
                page_size=10,
            )
            
            assert result.total == 5

    @pytest.mark.asyncio
    async def test_simple_search_with_tenant(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test simple search with tenant context."""
        tenant_id = uuid4()
        
        mock_result = MockSearchResult(total=3)
        mock_service = AsyncMock()
        mock_service.search.return_value = mock_result
        
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.return_value = mock_service
            
            result = await simple_search(
                session=mock_session,
                current_user=mock_user,
                tenant_id=tenant_id,
                q="test",
                index="users",
                page=2,
                page_size=20,
            )
            
            assert result.total == 3


class TestSuggestEndpoint:
    """Tests for suggest endpoint."""

    @pytest.mark.asyncio
    async def test_suggest_invalid_index(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test suggest with invalid index."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await suggest(
                session=mock_session,
                current_user=mock_user,
                tenant_id=None,
                q="test",
                index="invalid_index",
                field="title",
                size=5,
            )
        
        assert exc.value.status_code == 400
        assert "Invalid search index" in exc.value.detail

    @pytest.mark.asyncio
    async def test_suggest_success(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test successful suggest."""
        mock_service = AsyncMock()
        mock_service.suggest.return_value = ["suggestion1", "suggestion2", "suggestion3"]
        
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.return_value = mock_service
            
            result = await suggest(
                session=mock_session,
                current_user=mock_user,
                tenant_id=uuid4(),
                q="tes",
                index="posts",
                field="title",
                size=5,
            )
            
            assert len(result.suggestions) == 3

    @pytest.mark.asyncio
    async def test_suggest_backend_error(
        self, mock_session: MagicMock, mock_user: MagicMock
    ) -> None:
        """Test suggest when backend fails."""
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.side_effect = Exception("Backend error")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await suggest(
                    session=mock_session,
                    current_user=mock_user,
                    tenant_id=None,
                    q="test",
                    index="posts",
                    field="title",
                    size=5,
                )
            
            assert exc.value.status_code == 500
            assert "Suggest failed" in exc.value.detail


class TestHealthEndpoint:
    """Tests for health endpoint."""

    @pytest.mark.asyncio
    async def test_health_success(self, mock_session: MagicMock) -> None:
        """Test successful health check."""
        mock_service = AsyncMock()
        mock_service.health_check.return_value = {
            "status": "healthy",
            "backend": "postgres",
            "version": "15",
        }
        
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.return_value = mock_service
            
            result = await health(session=mock_session)
            
            assert result.status == "healthy"
            assert result.backend == "postgres"

    @pytest.mark.asyncio
    async def test_health_unhealthy(self, mock_session: MagicMock) -> None:
        """Test health check when backend is unhealthy."""
        with patch("app.api.v1.endpoints.search.get_search_backend") as mock_get_backend:
            mock_get_backend.side_effect = Exception("Connection failed")
            
            result = await health(session=mock_session)
            
            assert result.status == "unhealthy"
            assert "error" in result.details


class TestListIndicesEndpoint:
    """Tests for list_indices endpoint."""

    @pytest.mark.asyncio
    async def test_list_indices(self, mock_user: MagicMock) -> None:
        """Test listing search indices."""
        result = await list_indices(current_user=mock_user)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check structure
        for item in result:
            assert "name" in item
            assert "description" in item


class TestSearchSchemas:
    """Tests for search request schemas."""

    def test_search_filter_request(self) -> None:
        """Test SearchFilterRequest schema."""
        filter_req = SearchFilterRequest(
            field="is_active",
            value=True,
            operator="eq",
        )
        
        assert filter_req.field == "is_active"
        assert filter_req.value is True
        assert filter_req.operator == "eq"

    def test_search_sort_request(self) -> None:
        """Test SearchSortRequest schema."""
        sort_req = SearchSortRequest(
            field="created_at",
            order="desc",
        )
        
        assert sort_req.field == "created_at"
        assert sort_req.order == "desc"

    def test_search_request_defaults(self) -> None:
        """Test SearchRequest default values."""
        request = SearchRequest(  # type: ignore[call-arg]
            query="test",
            index="users",
        )
        
        assert request.page == 1
        assert request.page_size == 20
        assert request.fuzzy is True
        assert request.filters == []
        assert request.sort == []
        assert request.highlight_fields == []

    def test_search_request_full(self) -> None:
        """Test SearchRequest with all fields."""
        request = SearchRequest(
            query="test query",
            index="posts",
            filters=[SearchFilterRequest(field="status", value="published", operator="eq")],
            sort=[SearchSortRequest(field="created_at", order="desc")],
            highlight_fields=["title", "content"],
            page=2,
            page_size=50,
            fuzzy=False,
        )
        
        assert request.query == "test query"
        assert request.page == 2
        assert request.page_size == 50
        assert request.fuzzy is False
        assert len(request.filters) == 1
        assert len(request.sort) == 1
        assert len(request.highlight_fields) == 2
