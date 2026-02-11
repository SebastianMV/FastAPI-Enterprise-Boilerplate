# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Full-Text Search port interface.

Defines the abstract interface for search implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


class SearchIndex(str, Enum):
    """Available search indices."""

    USERS = "users"
    AUDIT_LOGS = "audit_logs"


class SortOrder(str, Enum):
    """Sort order."""

    ASC = "asc"
    DESC = "desc"


@dataclass
class SearchFilter:
    """Search filter criteria."""

    field: str
    value: Any
    operator: str = "eq"  # eq, ne, gt, gte, lt, lte, in, contains, startswith, endswith


@dataclass
class SearchSort:
    """Search sort criteria."""

    field: str
    order: SortOrder = SortOrder.DESC


@dataclass
class SearchHighlight:
    """Search highlight configuration."""

    fields: list[str]
    pre_tag: str = "<mark>"
    post_tag: str = "</mark>"
    fragment_size: int = 150
    number_of_fragments: int = 3


@dataclass
class SearchQuery:
    """
    Full-text search query.

    Attributes:
        query: The search query string
        index: Search index to query
        filters: Additional filters to apply
        sort: Sort criteria
        highlight: Highlight configuration
        page: Page number (1-indexed)
        page_size: Number of results per page
        tenant_id: Tenant context for multi-tenant search
        include_deleted: Whether to include soft-deleted records
    """

    query: str
    index: SearchIndex
    filters: list[SearchFilter] = field(default_factory=list)
    sort: list[SearchSort] = field(default_factory=list)
    highlight: SearchHighlight | None = None
    page: int = 1
    page_size: int = 20
    tenant_id: UUID | None = None
    include_deleted: bool = False
    fuzzy: bool = True


@dataclass
class SearchHit(Generic[T]):
    """
    Individual search result.

    Attributes:
        id: Document ID
        score: Relevance score
        source: The matched document
        highlights: Highlighted text fragments
        matched_fields: Fields that matched the query
    """

    id: str
    score: float
    source: T
    highlights: dict[str, list[str]] = field(default_factory=dict)
    matched_fields: list[str] = field(default_factory=list)


@dataclass
class SearchResult(Generic[T]):
    """
    Search results container.

    Attributes:
        hits: List of search hits
        total: Total number of matching documents
        page: Current page number
        page_size: Results per page
        took_ms: Query execution time in milliseconds
        max_score: Maximum relevance score
        aggregations: Aggregation results
        suggestions: Search suggestions
    """

    hits: list[SearchHit[T]]
    total: int
    page: int
    page_size: int
    took_ms: float = 0.0
    max_score: float | None = None
    aggregations: dict[str, Any] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)

    @property
    def total_pages(self) -> int:
        """Calculate total pages."""
        return (
            (self.total + self.page_size - 1) // self.page_size
            if self.page_size > 0
            else 0
        )

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


@dataclass
class IndexDocument:
    """
    Document to be indexed.

    Attributes:
        id: Document ID (usually UUID)
        index: Target index
        data: Document data
        tenant_id: Tenant context
        routing: Routing key for sharding
    """

    id: str
    index: SearchIndex
    data: dict[str, Any]
    tenant_id: UUID | None = None
    routing: str | None = None


@dataclass
class BulkIndexResult:
    """
    Bulk indexing result.

    Attributes:
        indexed: Number of successfully indexed documents
        failed: Number of failed documents
        errors: List of error messages
        took_ms: Operation time in milliseconds
    """

    indexed: int
    failed: int
    errors: list[str] = field(default_factory=list)
    took_ms: float = 0.0


class SearchPort(ABC):
    """
    Abstract interface for full-text search.

    Default Implementation:
    - PostgresFullTextSearch: Uses PostgreSQL's built-in FTS

    The interface is designed to be extensible for custom implementations.
    """

    @abstractmethod
    async def search(
        self,
        query: SearchQuery,
    ) -> SearchResult[dict[str, Any]]:
        """
        Execute a search query.

        Args:
            query: The search query to execute

        Returns:
            SearchResult containing matching documents
        """
        ...

    @abstractmethod
    async def index_document(
        self,
        document: IndexDocument,
    ) -> bool:
        """
        Index a single document.

        Args:
            document: The document to index

        Returns:
            True if successful, False otherwise
        """
        ...

    @abstractmethod
    async def bulk_index(
        self,
        documents: list[IndexDocument],
    ) -> BulkIndexResult:
        """
        Index multiple documents in bulk.

        Args:
            documents: List of documents to index

        Returns:
            BulkIndexResult with operation summary
        """
        ...

    @abstractmethod
    async def delete_document(
        self,
        index: SearchIndex,
        document_id: str,
        tenant_id: UUID | None = None,
    ) -> bool:
        """
        Delete a document from the index.

        Args:
            index: The index containing the document
            document_id: The document ID to delete
            tenant_id: Tenant context

        Returns:
            True if successful, False otherwise
        """
        ...

    @abstractmethod
    async def update_document(
        self,
        document: IndexDocument,
        upsert: bool = True,
    ) -> bool:
        """
        Update a document in the index.

        Args:
            document: The document with updated data
            upsert: Create if doesn't exist

        Returns:
            True if successful, False otherwise
        """
        ...

    @abstractmethod
    async def get_document(
        self,
        index: SearchIndex,
        document_id: str,
        tenant_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        """
        Get a document by ID.

        Args:
            index: The index containing the document
            document_id: The document ID
            tenant_id: Tenant context

        Returns:
            Document data or None if not found
        """
        ...

    @abstractmethod
    async def suggest(
        self,
        query: str,
        index: SearchIndex,
        field: str = "title",
        size: int = 5,
        tenant_id: UUID | None = None,
    ) -> list[str]:
        """
        Get search suggestions/autocomplete.

        Args:
            query: Partial query string
            index: Index to search
            field: Field to get suggestions from
            size: Number of suggestions
            tenant_id: Tenant context

        Returns:
            List of suggestions
        """
        ...

    @abstractmethod
    async def reindex(
        self,
        index: SearchIndex,
        tenant_id: UUID | None = None,
    ) -> BulkIndexResult:
        """
        Reindex all documents in an index.

        Args:
            index: The index to reindex
            tenant_id: Only reindex for specific tenant

        Returns:
            BulkIndexResult with operation summary
        """
        ...

    @abstractmethod
    async def create_index(
        self,
        index: SearchIndex,
    ) -> bool:
        """
        Create a search index with appropriate mappings.

        Args:
            index: The index to create

        Returns:
            True if successful, False otherwise
        """
        ...

    @abstractmethod
    async def delete_index(
        self,
        index: SearchIndex,
    ) -> bool:
        """
        Delete a search index.

        Args:
            index: The index to delete

        Returns:
            True if successful, False otherwise
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Check search service health.

        Returns:
            Health status information
        """
        ...
