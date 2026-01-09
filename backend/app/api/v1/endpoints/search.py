# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Full-Text Search API endpoints.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, CurrentTenantId, DbSession
from app.config import settings
from app.domain.ports.search import (
    SearchFilter,
    SearchHighlight,
    SearchIndex,
    SearchQuery,
    SearchSort,
    SortOrder,
)
from app.infrastructure.search import get_search_backend


router = APIRouter(prefix="/search", tags=["Search"])


# ==============================================================================
# Schemas
# ==============================================================================


class SearchFilterRequest(BaseModel):
    """Search filter."""
    
    field: str = Field(..., description="Field to filter on")
    value: Any = Field(..., description="Filter value")
    operator: str = Field(
        "eq",
        description="Filter operator: eq, ne, gt, gte, lt, lte, in, contains, startswith, endswith",
    )


class SearchSortRequest(BaseModel):
    """Search sort criteria."""
    
    field: str = Field(..., description="Field to sort by")
    order: str = Field("desc", description="Sort order: asc or desc")


class SearchRequest(BaseModel):
    """Full-text search request."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    index: str = Field(..., description="Search index: users, posts, messages, documents, audit_logs")
    filters: list[SearchFilterRequest] = Field(default_factory=list)
    sort: list[SearchSortRequest] = Field(default_factory=list)
    highlight_fields: list[str] = Field(default_factory=list)
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Results per page")
    fuzzy: bool = Field(True, description="Enable fuzzy matching")


class SearchHitResponse(BaseModel):
    """Individual search result."""
    
    id: str
    score: float
    source: dict[str, Any]
    highlights: dict[str, list[str]] = Field(default_factory=dict)
    matched_fields: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Search results response."""
    
    hits: list[SearchHitResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    took_ms: float
    max_score: float | None = None
    suggestions: list[str] = Field(default_factory=list)


class SuggestResponse(BaseModel):
    """Search suggestions response."""
    
    suggestions: list[str]


class HealthResponse(BaseModel):
    """Search health status."""
    
    status: str
    backend: str
    details: dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# Endpoints
# ==============================================================================


@router.post(
    "",
    response_model=SearchResponse,
    summary="Full-text search",
    description="Search across indexed documents with filters, sorting, and highlighting.",
)
async def search(
    request: SearchRequest,
    session: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId = None,
) -> SearchResponse:
    """
    Execute full-text search.
    
    Supports:
    - Multi-field search with relevance ranking
    - Filters with various operators
    - Sorting by any field
    - Result highlighting
    - Fuzzy matching for typo tolerance
    - Pagination
    """
    # Validate index
    try:
        search_index = SearchIndex(request.index.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search index: {request.index}. Valid options: {[i.value for i in SearchIndex]}",
        )
    
    # Build search query
    filters = [
        SearchFilter(
            field=f.field,
            value=f.value,
            operator=f.operator,
        )
        for f in request.filters
    ]
    
    sort = [
        SearchSort(
            field=s.field,
            order=SortOrder(s.order.lower()) if s.order.lower() in ["asc", "desc"] else SortOrder.DESC,
        )
        for s in request.sort
    ]
    
    highlight = None
    if request.highlight_fields:
        highlight = SearchHighlight(
            fields=request.highlight_fields,
        )
    
    query = SearchQuery(
        query=request.query,
        index=search_index,
        filters=filters,
        sort=sort,
        highlight=highlight,
        page=request.page,
        page_size=request.page_size,
        tenant_id=tenant_id,
        fuzzy=request.fuzzy,
    )
    
    # Get search backend
    backend = getattr(settings, "SEARCH_BACKEND", "postgres")
    
    try:
        search_service = await get_search_backend(
            backend=backend,
            session=session,
            url=getattr(settings, "ELASTICSEARCH_URL", "http://localhost:9200"),
            index_prefix=getattr(settings, "SEARCH_INDEX_PREFIX", "app"),
        )
        
        result = await search_service.search(query)
        
        return SearchResponse(
            hits=[
                SearchHitResponse(
                    id=hit.id,
                    score=hit.score,
                    source=hit.source,
                    highlights=hit.highlights,
                    matched_fields=hit.matched_fields,
                )
                for hit in result.hits
            ],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            total_pages=result.total_pages,
            has_next=result.has_next,
            has_previous=result.has_previous,
            took_ms=result.took_ms,
            max_score=result.max_score,
            suggestions=result.suggestions,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.get(
    "/simple",
    response_model=SearchResponse,
    summary="Simple search",
    description="Simple search with query string parameters.",
)
async def simple_search(
    session: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId = None,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    index: str = Query("posts", description="Search index"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SearchResponse:
    """
    Simple GET-based search.
    """
    request = SearchRequest(
        query=q,
        index=index,
        page=page,
        page_size=page_size,
        fuzzy=True,
    )
    
    return await search(request, session, current_user, tenant_id)


@router.get(
    "/suggest",
    response_model=SuggestResponse,
    summary="Search suggestions",
    description="Get search suggestions/autocomplete.",
)
async def suggest(
    session: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId = None,
    q: str = Query(..., min_length=1, max_length=100, description="Partial query"),
    index: str = Query("posts", description="Search index"),
    field: str = Query("title", description="Field to get suggestions from"),
    size: int = Query(5, ge=1, le=20, description="Number of suggestions"),
) -> SuggestResponse:
    """
    Get search suggestions for autocomplete.
    """
    try:
        search_index = SearchIndex(index.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search index: {index}",
        )
    
    backend = getattr(settings, "SEARCH_BACKEND", "postgres")
    
    try:
        search_service = await get_search_backend(
            backend=backend,
            session=session,
        )
        
        suggestions = await search_service.suggest(
            query=q,
            index=search_index,
            field=field,
            size=size,
            tenant_id=tenant_id,
        )
        
        return SuggestResponse(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Suggest failed: {str(e)}",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Search health",
    description="Check search service health.",
)
async def health(
    session: DbSession,
) -> HealthResponse:
    """
    Check search backend health.
    """
    backend = getattr(settings, "SEARCH_BACKEND", "postgres")
    
    try:
        search_service = await get_search_backend(
            backend=backend,
            session=session,
        )
        
        health_info = await search_service.health_check()
        
        return HealthResponse(
            status=health_info.get("status", "unknown"),
            backend=health_info.get("backend", backend),
            details=health_info,
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            backend=backend,
            details={"error": str(e)},
        )


@router.get(
    "/indices",
    summary="List search indices",
    description="Get list of available search indices.",
)
async def list_indices(
    current_user: CurrentUser,
) -> list[dict[str, str]]:
    """
    List available search indices.
    """
    return [
        {"name": index.value, "description": index.name.replace("_", " ").title()}
        for index in SearchIndex
    ]


# ==============================================================================
# Admin Endpoints
# ==============================================================================


@router.post(
    "/indices/{index}/create",
    status_code=status.HTTP_201_CREATED,
    summary="Create search index",
    description="Create a search index (admin only).",
)
async def create_index(
    index: str,
    session: DbSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Create a search index.
    
    For PostgreSQL, this creates the GIN index.
    For Elasticsearch, this creates the index with mappings.
    
    Requires superadmin privileges.
    """
    # Check admin privileges
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can create search indices",
        )
    
    try:
        search_index = SearchIndex(index.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search index: {index}",
        )
    
    backend = getattr(settings, "SEARCH_BACKEND", "postgres")
    
    try:
        search_service = await get_search_backend(
            backend=backend,
            session=session,
        )
        
        success = await search_service.create_index(search_index)
        
        if success:
            return {"status": "created", "index": index}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create index",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Create index failed: {str(e)}",
        )


@router.post(
    "/indices/{index}/reindex",
    summary="Reindex documents",
    description="Reindex all documents in an index (admin only).",
)
async def reindex(
    index: str,
    session: DbSession,
    current_user: CurrentUser,
    tenant_id: CurrentTenantId = None,
) -> dict[str, Any]:
    """
    Reindex all documents in an index.
    
    Requires superadmin privileges.
    """
    # Check admin privileges
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can reindex search indices",
        )
    
    try:
        search_index = SearchIndex(index.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search index: {index}",
        )
    
    backend = getattr(settings, "SEARCH_BACKEND", "postgres")
    
    try:
        search_service = await get_search_backend(
            backend=backend,
            session=session,
        )
        
        result = await search_service.reindex(
            index=search_index,
            tenant_id=tenant_id,
        )
        
        return {
            "status": "completed",
            "index": index,
            "indexed": result.indexed,
            "failed": result.failed,
            "took_ms": result.took_ms,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindex failed: {str(e)}",
        )


@router.delete(
    "/indices/{index}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete search index",
    description="Delete a search index (admin only).",
)
async def delete_index(
    index: str,
    session: DbSession,
    current_user: CurrentUser,
) -> None:
    """
    Delete a search index.
    
    Requires superadmin privileges.
    """
    # Check admin privileges
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can delete search indices",
        )
    
    try:
        search_index = SearchIndex(index.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search index: {index}",
        )
    
    backend = getattr(settings, "SEARCH_BACKEND", "postgres")
    
    try:
        search_service = await get_search_backend(
            backend=backend,
            session=session,
        )
        
        success = await search_service.delete_index(search_index)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete index",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Delete index failed: {str(e)}",
        )
