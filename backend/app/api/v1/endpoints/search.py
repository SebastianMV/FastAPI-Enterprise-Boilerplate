# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Full-Text Search API endpoints.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import DataError, ProgrammingError

from app.api.deps import (
    CurrentTenantId,
    DbSession,
    SuperuserId,
    require_permission,
)
from app.domain.ports.search import (
    SearchFilter,
    SearchHighlight,
    SearchIndex,
    SearchQuery,
    SearchSort,
    SortOrder,
)
from app.infrastructure.observability.logging import get_logger
from app.infrastructure.search import get_search_backend

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])

# Per-index allowed fields for filters, sort, suggest, and highlight.
# Fields not in this set are rejected to prevent probing of sensitive columns.
_ALLOWED_FIELDS: dict[str, set[str]] = {
    "users": {
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_superuser",
        "created_at",
        "updated_at",
        "tenant_id",
    },
    "audit_logs": {
        "action",
        "resource_type",
        "resource_id",
        "reason",
        "actor_id",
        "actor_ip",
        "created_at",
        "tenant_id",
    },
}


def _validate_field_name(field: str, index: str, context: str = "filter") -> None:
    """Validate that *field* is in the allowed set for *index*."""
    allowed = _ALLOWED_FIELDS.get(index.lower())
    if allowed is None:
        return  # Unknown index — let the index validator handle it
    if field not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FIELD",
                "message": f"Field '{field}' is not allowed for {context} on index '{index}'",
            },
        )


def _validate_search_index(index_name: str) -> SearchIndex:
    """Validate and convert a search index name, raising HTTP 400 on invalid input."""
    try:
        return SearchIndex(index_name.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_SEARCH_INDEX", "message": "Invalid search index"},
        ) from None


# ==============================================================================
# Schemas
# ==============================================================================


class SearchFilterRequest(BaseModel):
    """Search filter."""

    field: str = Field(..., max_length=100, description="Field to filter on")
    value: str | int | float | bool | list[str] = Field(..., description="Filter value")
    operator: str = Field(
        "eq",
        max_length=20,
        pattern="^(eq|ne|gt|gte|lt|lte|in|contains|startswith|endswith)$",
        description="Filter operator: eq, ne, gt, gte, lt, lte, in, contains, startswith, endswith",
    )


class SearchSortRequest(BaseModel):
    """Search sort criteria."""

    field: str = Field(..., max_length=100, description="Field to sort by")
    order: str = Field(
        "desc", pattern="^(asc|desc)$", description="Sort order: asc or desc"
    )


class SearchRequest(BaseModel):
    """Full-text search request."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    index: str = Field(
        ...,
        max_length=50,
        description="Search index: users, posts, messages, documents, audit_logs",
    )
    filters: list[SearchFilterRequest] = Field(default_factory=list, max_length=20)
    sort: list[SearchSortRequest] = Field(default_factory=list, max_length=5)
    highlight_fields: list[str] = Field(default_factory=list, max_length=20)
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Results per page")
    fuzzy: bool = Field(True, description="Enable fuzzy matching")


class SearchHitResponse(BaseModel):
    """Individual search result."""

    id: str = Field(max_length=50)
    score: float
    source: dict[str, Any]
    highlights: dict[str, list[str]] = Field(default_factory=dict)
    matched_fields: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list
    )


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
    suggestions: list[Annotated[str, Field(max_length=500)]] = Field(
        default_factory=list
    )


class SuggestResponse(BaseModel):
    """Search suggestions response."""

    suggestions: list[Annotated[str, Field(max_length=500)]]


class HealthResponse(BaseModel):
    """Search health status."""

    status: str = Field(max_length=20)
    backend: str = Field(max_length=50)
    details: dict[str, Any] = Field(default_factory=dict)


class SearchIndexResponse(BaseModel):
    """Search index information."""

    name: str = Field(max_length=100)
    description: str = Field(max_length=200)


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
    current_user_id: UUID = Depends(require_permission("search", "read")),
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
    search_index = _validate_search_index(request.index)

    # Validate filter/sort fields against allowlist (B6)
    for f in request.filters:
        _validate_field_name(f.field, request.index, "filter")
    for s in request.sort:
        _validate_field_name(s.field, request.index, "sort")
    for hf in request.highlight_fields:
        _validate_field_name(hf, request.index, "highlight")

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
            order=SortOrder(s.order.lower())
            if s.order.lower() in ["asc", "desc"]
            else SortOrder.DESC,
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

    # Get search backend (PostgreSQL FTS)
    try:
        search_service = await get_search_backend(session=session)

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
    except ValueError as e:
        # Invalid query parameters — log detail, return generic
        logger.warning("search_invalid_query", error=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_QUERY",
                "message": "Invalid search query parameters",
            },
        ) from e
    except (ProgrammingError, DataError):
        # Bad query syntax or invalid data type — return empty results
        logger.warning("search_database_error", query_length=len(request.query))
        return SearchResponse(
            hits=[],
            total=0,
            page=request.page,
            page_size=request.page_size,
            total_pages=0,
            has_next=False,
            has_previous=False,
            took_ms=0,
            max_score=None,
            suggestions=[],
        )
    except Exception as e:
        logger.warning("search_unexpected_error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SEARCH_ERROR",
                "message": "An internal search error occurred",
            },
        ) from e


@router.get(
    "/simple",
    response_model=SearchResponse,
    summary="Simple search",
    description="Simple search with query string parameters.",
)
async def simple_search(
    session: DbSession,
    current_user_id: UUID = Depends(require_permission("search", "read")),
    tenant_id: CurrentTenantId = None,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    index: str = Query("posts", max_length=50, description="Search index"),
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

    return await search(request, session, current_user_id, tenant_id)


@router.get(
    "/suggest",
    response_model=SuggestResponse,
    summary="Search suggestions",
    description="Get search suggestions/autocomplete.",
)
async def suggest(
    session: DbSession,
    current_user_id: UUID = Depends(require_permission("search", "read")),
    tenant_id: CurrentTenantId = None,
    q: str = Query(..., min_length=1, max_length=100, description="Partial query"),
    index: str = Query("posts", max_length=50, description="Search index"),
    field: str = Query(
        "title", max_length=100, description="Field to get suggestions from"
    ),
    size: int = Query(5, ge=1, le=20, description="Number of suggestions"),
) -> SuggestResponse:
    """
    Get search suggestions for autocomplete.
    """
    search_index = _validate_search_index(index)

    # Validate suggest field against allowlist (B6)
    _validate_field_name(field, index, "suggest")

    try:
        search_service = await get_search_backend(session=session)

        suggestions = await search_service.suggest(
            query=q,
            index=search_index,
            field=field,
            size=size,
            tenant_id=tenant_id,
        )

        return SuggestResponse(suggestions=suggestions)
    except Exception as e:
        logger.warning("suggest_unexpected_error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SEARCH_ERROR",
                "message": "An internal search error occurred",
            },
        ) from e


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Search health",
    description="Check search service health.",
)
async def health(
    session: DbSession,
    current_user_id: UUID = Depends(require_permission("search", "read")),
    tenant_id: CurrentTenantId = None,
) -> HealthResponse:
    """
    Check search backend health.
    """
    try:
        search_service = await get_search_backend(session=session)

        health_info = await search_service.health_check()

        return HealthResponse(
            status=health_info.get("status", "unknown"),
            backend=health_info.get("backend", "postgres"),
            details=health_info,
        )
    except Exception as e:
        logger.error("search_health_check_failed", error=type(e).__name__)
        return HealthResponse(
            status="unhealthy",
            backend="postgres",
            details={"error": "Health check failed"},
        )


@router.get(
    "/indices",
    response_model=list[SearchIndexResponse],
    summary="List search indices",
    description="Get list of available search indices.",
)
async def list_indices(
    current_user_id: UUID = Depends(require_permission("search", "read")),
    tenant_id: CurrentTenantId = None,
) -> list[SearchIndexResponse]:
    """
    List available search indices.
    """
    return [
        SearchIndexResponse(
            name=index.value,
            description=index.name.replace("_", " ").title(),
        )
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
    index: str = Path(..., max_length=50),
    *,
    session: DbSession,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId = None,
) -> dict[str, Any]:
    """
    Create a search index.

    Creates the GIN index for PostgreSQL Full-Text Search.

    Requires superadmin privileges.
    """
    search_index = _validate_search_index(index)

    try:
        search_service = await get_search_backend(session=session)

        success = await search_service.create_index(search_index)

        if success:
            return {"status": "created", "index": index}
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INDEX_CREATE_FAILED", "message": "Failed to create index"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("search_create_index_failed", error=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INDEX_CREATE_FAILED",
                "message": "Failed to create search index",
            },
        ) from e


@router.post(
    "/indices/{index}/reindex",
    summary="Reindex documents",
    description="Reindex all documents in an index (admin only).",
)
async def reindex(
    index: str = Path(..., max_length=50),
    *,
    session: DbSession,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId = None,
) -> dict[str, Any]:
    """
    Reindex all documents in an index.

    Requires superadmin privileges.
    """
    search_index = _validate_search_index(index)

    try:
        search_service = await get_search_backend(session=session)

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("search_reindex_failed", error=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "REINDEX_FAILED", "message": "Reindex operation failed"},
        ) from e


@router.delete(
    "/indices/{index}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete search index",
    description="Delete a search index (admin only).",
)
async def delete_index(
    index: str = Path(..., max_length=50),
    *,
    session: DbSession,
    superuser_id: SuperuserId,
    tenant_id: CurrentTenantId = None,
) -> None:
    """
    Delete a search index.

    Requires superadmin privileges.
    """
    search_index = _validate_search_index(index)

    try:
        search_service = await get_search_backend(session=session)

        success = await search_service.delete_index(search_index)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "INDEX_DELETE_FAILED",
                    "message": "Failed to delete index",
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("search_delete_index_failed", error=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INDEX_DELETE_FAILED",
                "message": "Failed to delete search index",
            },
        ) from e
