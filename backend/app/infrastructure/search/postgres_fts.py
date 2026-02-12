# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
PostgreSQL Full-Text Search implementation.

Uses PostgreSQL's built-in full-text search capabilities with:
- tsvector for document indexing
- tsquery for search queries
- GIN indexes for performance
- Trigram matching for fuzzy search
"""

import re
import time
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.search import (
    BulkIndexResult,
    IndexDocument,
    SearchFilter,
    SearchHit,
    SearchIndex,
    SearchPort,
    SearchQuery,
    SearchResult,
    SortOrder,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

# Valid PostgreSQL text search configurations (defense-in-depth)
_VALID_FTS_LANGUAGES = {
    "simple", "arabic", "armenian", "basque", "catalan", "danish", "dutch",
    "english", "finnish", "french", "german", "greek", "hindi", "hungarian",
    "indonesian", "irish", "italian", "lithuanian", "nepali", "norwegian",
    "portuguese", "romanian", "russian", "serbian", "spanish", "swedish",
    "tamil", "turkish", "yiddish",
}

# Default number of suggestions returned by fuzzy/trigram search
DEFAULT_SUGGESTION_LIMIT = 5

# Index configurations: defines which tables and columns are searchable
INDEX_CONFIGS: dict[SearchIndex, dict[str, Any]] = {
    SearchIndex.USERS: {
        "table": "users",
        "id_column": "id",
        "tenant_column": "tenant_id",
        "deleted_column": "deleted_at",
        "search_columns": {
            "email": "A",  # Weight A (highest)
            "first_name": "A",
            "last_name": "A",
        },
        "highlight_columns": ["email", "first_name", "last_name"],
        "suggest_column": "email",
        "allowed_filter_fields": {
            "email", "first_name", "last_name", "is_active",
            "is_superuser", "created_at", "updated_at", "tenant_id",
        },
    },
    SearchIndex.AUDIT_LOGS: {
        "table": "audit_logs",
        "id_column": "id",
        "tenant_column": "tenant_id",
        "deleted_column": None,  # No soft delete
        "search_columns": {
            "action": "A",
            "resource_type": "B",
            "reason": "C",
        },
        "highlight_columns": ["action", "reason"],
        "suggest_column": "action",
        "allowed_filter_fields": {
            "action", "resource_type", "resource_id", "reason",
            "actor_id", "actor_ip", "created_at", "tenant_id",
        },
    },
}


class PostgresFullTextSearch(SearchPort):
    """
    PostgreSQL Full-Text Search implementation.

    Features:
    - Native FTS with tsvector/tsquery
    - Multi-language support (configurable)
    - Fuzzy matching with trigrams (pg_trgm)
    - Ranking with ts_rank_cd
    - Highlighting with ts_headline
    """

    def __init__(
        self,
        session: AsyncSession,
        language: str = "english",
    ) -> None:
        """
        Initialize PostgreSQL FTS.

        Args:
            session: SQLAlchemy async session
            language: PostgreSQL text search configuration
        """
        self._session = session
        if language not in _VALID_FTS_LANGUAGES:
            raise ValueError(
                f"Invalid FTS language configuration: must be one of {sorted(_VALID_FTS_LANGUAGES)}"
            )
        self._language = language

    async def search(
        self,
        query: SearchQuery,
    ) -> SearchResult[dict[str, Any]]:
        """Execute full-text search using PostgreSQL FTS."""
        start_time = time.perf_counter()

        config = INDEX_CONFIGS.get(query.index)
        if not config:
            raise ValueError(f"Unsupported search index: {query.index}")

        table = config["table"]
        id_col = config["id_column"]
        search_cols = config["search_columns"]
        highlight_cols = config.get("highlight_columns", [])

        # Build the tsvector expression
        tsvector_parts = []
        for col, weight in search_cols.items():
            tsvector_parts.append(
                f"setweight(to_tsvector('{self._language}', COALESCE({col}::text, '')), '{weight}')"
            )
        tsvector_expr = " || ".join(tsvector_parts)

        # Build tsquery from search terms
        search_terms = self._parse_search_query(query.query)

        # If search terms are empty or invalid after sanitization, return empty results
        if not search_terms or search_terms.strip() in ["", "&", "|", ":*"]:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return SearchResult(
                hits=[],
                total=0,
                page=query.page,
                page_size=query.page_size,
                took_ms=elapsed_ms,
                max_score=None,
                suggestions=[],
            )

        # Build the main query
        sql_parts = [
            f"SELECT {id_col}::text as id,",
            f"  ts_rank_cd({tsvector_expr}, query) as score,",
            f"  row_to_json({table}.*) as source",
        ]

        # Add highlights
        for col in highlight_cols:
            if col in search_cols:
                sql_parts.append(
                    f",  ts_headline('{self._language}', {col}::text, query, "
                    f"'StartSel=<mark>, StopSel=</mark>, MaxFragments=3, MaxWords=20, MinWords=5') "
                    f"as highlight_{col}"
                )

        sql_parts.append(f"FROM {table},")
        sql_parts.append(f"  to_tsquery('{self._language}', :query) as query")

        # WHERE clause
        where_clauses = [f"({tsvector_expr}) @@ query"]
        params: dict[str, Any] = {"query": search_terms}

        # Tenant filter
        if query.tenant_id and config.get("tenant_column"):
            where_clauses.append(f"{config['tenant_column']} = :tenant_id")
            params["tenant_id"] = str(query.tenant_id)

        # Soft delete filter
        if not query.include_deleted and config.get("deleted_column"):
            where_clauses.append(f"{config['deleted_column']} IS NULL")

        # Additional filters
        allowed_fields = config.get("allowed_filter_fields")
        for i, f in enumerate(query.filters):
            param_name = f"filter_{i}"
            where_clauses.append(
                self._build_filter_clause(f, param_name, allowed_fields=allowed_fields)
            )
            params[param_name] = f.value

        sql_parts.append("WHERE " + " AND ".join(where_clauses))

        # ORDER BY - validate fields to prevent SQL injection
        order_clauses = []
        if query.sort:
            # Get valid columns for this index
            valid_columns = set(search_cols.keys())
            valid_columns.add("id")
            valid_columns.add("created_at")
            valid_columns.add("updated_at")

            for s in query.sort:
                # Sanitize field name - only allow alphanumeric and underscore
                sanitized_field = re.sub(r"[^a-zA-Z0-9_]", "", s.field)

                # Only allow known columns
                if sanitized_field in valid_columns:
                    order_dir = "ASC" if s.order == SortOrder.ASC else "DESC"
                    order_clauses.append(f"{sanitized_field} {order_dir}")
                else:
                    logger.warning("Invalid sort field ignored: %s", s.field)
        order_clauses.append("score DESC")  # Always include score

        sql_parts.append("ORDER BY " + ", ".join(order_clauses))

        # Pagination — use bind params
        offset = (query.page - 1) * query.page_size
        sql_parts.append("LIMIT :_limit OFFSET :_offset")
        params["_limit"] = query.page_size
        params["_offset"] = offset

        full_sql = "\n".join(sql_parts)

        # Execute main query
        result = await self._session.execute(text(full_sql), params)
        rows = result.fetchall()

        # Count total
        count_sql = f"""
            SELECT COUNT(*) 
            FROM {table},
                 to_tsquery('{self._language}', :query) as query
            WHERE {" AND ".join(where_clauses)}
        """
        count_result = await self._session.execute(text(count_sql), params)
        total = count_result.scalar() or 0

        # Build search hits
        hits: list[SearchHit[dict[str, Any]]] = []
        max_score = 0.0

        for row in rows:
            score = float(row.score) if row.score else 0.0
            max_score = max(max_score, score)

            # Extract highlights
            highlights: dict[str, list[str]] = {}
            for col in highlight_cols:
                highlight_key = f"highlight_{col}"
                if hasattr(row, highlight_key):
                    highlight_value = getattr(row, highlight_key)
                    if highlight_value:
                        highlights[col] = [highlight_value]

            hits.append(
                SearchHit(
                    id=row.id,
                    score=score,
                    source=row.source,
                    highlights=highlights,
                    matched_fields=list(highlights.keys()),
                )
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Get suggestions if no results
        suggestions: list[str] = []
        if not hits and query.fuzzy:
            suggestions = await self.suggest(
                query=query.query,
                index=query.index,
                tenant_id=query.tenant_id,
            )

        return SearchResult(
            hits=hits,
            total=int(total),
            page=query.page,
            page_size=query.page_size,
            took_ms=elapsed_ms,
            max_score=max_score if hits else None,
            suggestions=suggestions,
        )

    async def index_document(
        self,
        document: IndexDocument,
    ) -> bool:
        """
        For PostgreSQL FTS, documents are indexed automatically via triggers.
        This method can be used to update the search vector column if using one.
        """
        config = INDEX_CONFIGS.get(document.index)
        if not config:
            return False

        # PostgreSQL FTS uses the actual table data, no separate indexing needed
        # If you have a dedicated tsvector column, update it here

        logger.debug("Document %s indexed in %s", document.id, document.index.value)
        return True

    async def bulk_index(
        self,
        documents: list[IndexDocument],
    ) -> BulkIndexResult:
        """Bulk index documents (no-op for PostgreSQL FTS)."""
        start_time = time.perf_counter()

        indexed = 0
        for doc in documents:
            if await self.index_document(doc):
                indexed += 1

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return BulkIndexResult(
            indexed=indexed,
            failed=len(documents) - indexed,
            took_ms=elapsed_ms,
        )

    async def delete_document(
        self,
        index: SearchIndex,
        document_id: str,
        tenant_id: UUID | None = None,
    ) -> bool:
        """
        For PostgreSQL FTS, deleting from the table removes from search.
        """
        # Actual deletion is handled by the main application
        logger.debug("Document %s removed from %s", document_id, index.value)
        return True

    async def update_document(
        self,
        document: IndexDocument,
        upsert: bool = True,
    ) -> bool:
        """Update document (same as index for PostgreSQL)."""
        return await self.index_document(document)

    async def get_document(
        self,
        index: SearchIndex,
        document_id: str,
        tenant_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        """Get document by ID."""
        config = INDEX_CONFIGS.get(index)
        if not config:
            return None

        table = config["table"]
        id_col = config["id_column"]

        sql = f"SELECT * FROM {table} WHERE {id_col} = :id"
        params: dict[str, Any] = {"id": document_id}

        if tenant_id and config.get("tenant_column"):
            sql += f" AND {config['tenant_column']} = :tenant_id"
            params["tenant_id"] = str(tenant_id)

        result = await self._session.execute(text(sql), params)
        row = result.mappings().first()

        return dict(row) if row else None

    async def suggest(
        self,
        query: str,
        index: SearchIndex,
        field: str = "title",
        size: int = DEFAULT_SUGGESTION_LIMIT,
        tenant_id: UUID | None = None,
    ) -> list[str]:
        """
        Get search suggestions using trigram similarity.

        Requires pg_trgm extension.
        """
        config = INDEX_CONFIGS.get(index)
        if not config:
            return []

        table = config["table"]
        suggest_col = config.get("suggest_column", field)

        # Use trigram similarity for suggestions
        # Note: Use subquery to allow ORDER BY with DISTINCT
        sql = f"""
            SELECT {suggest_col} FROM (
                SELECT DISTINCT {suggest_col}, similarity({suggest_col}, :query) as sim
                FROM {table}
                WHERE {suggest_col} % :query
                ORDER BY sim DESC
                LIMIT :limit
            ) subq
        """

        params: dict[str, Any] = {"query": query, "limit": size}

        try:
            result = await self._session.execute(text(sql), params)
            return [row[0] for row in result.fetchall() if row[0]]
        except Exception as e:
            logger.warning("Trigram suggestion failed: %s", e)

            # Fallback to ILIKE
            sql = f"""
                SELECT DISTINCT {suggest_col}
                FROM {table}
                WHERE {suggest_col} ILIKE :pattern
                LIMIT :limit
            """
            params = {"pattern": f"%{self._escape_like(query)}%", "limit": size}

            result = await self._session.execute(text(sql), params)
            return [row[0] for row in result.fetchall() if row[0]]

    async def reindex(
        self,
        index: SearchIndex,
        tenant_id: UUID | None = None,
    ) -> BulkIndexResult:
        """
        Reindex by refreshing materialized views or updating tsvector columns.
        """
        start_time = time.perf_counter()

        config = INDEX_CONFIGS.get(index)
        if not config:
            return BulkIndexResult(indexed=0, failed=0, took_ms=0)

        # If using a tsvector column, update it
        # This is a no-op if relying on expression indexes

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return BulkIndexResult(
            indexed=0,
            failed=0,
            took_ms=elapsed_ms,
        )

    async def create_index(
        self,
        index: SearchIndex,
    ) -> bool:
        """
        Create GIN index for full-text search.
        """
        config = INDEX_CONFIGS.get(index)
        if not config:
            return False

        table = config["table"]
        search_cols = config["search_columns"]

        # Build tsvector expression for index
        tsvector_parts = []
        for col, weight in search_cols.items():
            tsvector_parts.append(
                f"setweight(to_tsvector('{self._language}', COALESCE({col}::text, '')), '{weight}')"
            )
        tsvector_expr = " || ".join(tsvector_parts)

        # Create GIN index
        index_name = f"idx_{table}_fts"
        sql = f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table}
            USING GIN (({tsvector_expr}))
        """

        try:
            await self._session.execute(text(sql))
            logger.info("Created FTS index: %s", index_name)
            return True
        except Exception as e:
            logger.error("Failed to create FTS index: %s", e)
            return False

    async def delete_index(
        self,
        index: SearchIndex,
    ) -> bool:
        """
        Drop the FTS index.
        """
        config = INDEX_CONFIGS.get(index)
        if not config:
            return False

        table = config["table"]
        index_name = f"idx_{table}_fts"

        sql = f"DROP INDEX IF EXISTS {index_name}"

        try:
            await self._session.execute(text(sql))
            logger.info("Dropped FTS index: %s", index_name)
            return True
        except Exception as e:
            logger.error("Failed to drop FTS index: %s", e)
            return False

    async def health_check(self) -> dict[str, Any]:
        """Check PostgreSQL FTS availability."""
        try:
            # Test basic FTS functionality
            result = await self._session.execute(
                text(
                    "SELECT to_tsvector('english', 'test') @@ to_tsquery('english', 'test')"
                )
            )
            fts_works = result.scalar()

            # Check pg_trgm extension
            trgm_result = await self._session.execute(text("SELECT 'test' % 'test'"))
            trgm_works = True
        except Exception as e:
            trgm_works = False
            fts_works = False
            logger.warning("FTS health check failed: %s", e)

        return {
            "status": "healthy" if fts_works else "unhealthy",
            "backend": "postgresql",
            "fts_available": fts_works,
            "trigram_available": trgm_works,
            "language": self._language,
        }

    def _parse_search_query(self, query: str) -> str:
        """
        Parse search query into PostgreSQL tsquery format.

        Handles:
        - Basic terms: hello world -> hello & world
        - Phrases: "hello world" -> hello <-> world
        - OR: hello | world -> hello | world
        - NOT: -hello -> !hello
        - Prefix: hello* -> hello:*

        Also sanitizes input to prevent SQL injection.
        """
        if not query or not query.strip():
            return ""

        query = query.strip()

        # Sanitize: remove dangerous SQL characters/patterns
        # Remove SQL injection patterns
        dangerous_patterns = [
            r";\s*DROP\s+",
            r";\s*DELETE\s+",
            r";\s*UPDATE\s+",
            r";\s*INSERT\s+",
            r";\s*ALTER\s+",
            r";\s*CREATE\s+",
            r"--",
            r"/\*",
            r"\*/",
            r"UNION\s+SELECT",
            r"UNION\s+ALL",
            r"SELECT\s+\*",
            r"FROM\s+\w+",
            r"DROP\s+TABLE",
            r"DELETE\s+FROM",
        ]
        for pattern in dangerous_patterns:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

        # Remove semicolons and other dangerous chars for tsquery
        query = re.sub(r"[;'`\\]", "", query)

        # Handle quoted phrases
        phrases = re.findall(r'"([^"]+)"', query)
        query = re.sub(r'"[^"]+"', "", query)

        # Split remaining terms
        terms = query.split()

        tsquery_parts = []

        for term in terms:
            if not term:
                continue

            # Sanitize individual term - keep only alphanumeric and allowed chars
            term = re.sub(r"[^a-zA-Z0-9_\-*|@.]", "", term)
            if not term:
                continue

            # Handle NOT
            if term.startswith("-"):
                term = term[1:]
                if term:
                    tsquery_parts.append(f"!{term}")
            # Handle OR
            elif term == "|" or term.upper() == "OR":
                if tsquery_parts:
                    tsquery_parts.append("|")
            # Handle prefix
            elif term.endswith("*"):
                tsquery_parts.append(f"{term[:-1]}:*")
            else:
                # Regular term
                tsquery_parts.append(term)

        # Add phrase queries
        for phrase in phrases:
            phrase_terms = phrase.split()
            if phrase_terms:
                phrase_query = " <-> ".join(phrase_terms)
                tsquery_parts.append(f"({phrase_query})")

        # Join with AND by default
        result = []
        for i, part in enumerate(tsquery_parts):
            if part == "|":
                result.append("|")
            elif result and result[-1] != "|":
                result.append("&")
                result.append(part)
            else:
                result.append(part)

        return " ".join(result) if result else ""

    @staticmethod
    def _escape_like(value: str) -> str:
        """Escape LIKE/ILIKE wildcard characters in user input."""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _build_filter_clause(
        self,
        filter: SearchFilter,
        param_name: str,
        *,
        allowed_fields: set[str] | None = None,
    ) -> str:
        """Build SQL filter clause with field sanitization and allowlist check."""
        # Sanitize field name: only allow alphanumeric and underscore
        field = re.sub(r"[^a-zA-Z0-9_]", "", filter.field)
        if not field:
            raise ValueError(f"Invalid filter field: {filter.field}")

        # Allowlist check — reject fields not explicitly permitted (B6)
        if allowed_fields and field not in allowed_fields:
            raise ValueError(
                f"Field '{field}' is not allowed for filtering on this index"
            )

        op = filter.operator.lower()

        # NOTE: For ILIKE operators, callers must escape user input via
        # _escape_like() before passing values as bind parameters.
        operators = {
            "eq": f"{field} = :{param_name}",
            "ne": f"{field} != :{param_name}",
            "gt": f"{field} > :{param_name}",
            "gte": f"{field} >= :{param_name}",
            "lt": f"{field} < :{param_name}",
            "lte": f"{field} <= :{param_name}",
            "in": f"{field} = ANY(:{param_name})",
            "contains": f"{field} ILIKE '%' || :{param_name} || '%' ESCAPE '\\'",
            "startswith": f"{field} ILIKE :{param_name} || '%' ESCAPE '\\'",
            "endswith": f"{field} ILIKE '%' || :{param_name} ESCAPE '\\'",
        }

        return operators.get(op, f"{field} = :{param_name}")


# Factory function
def get_postgres_search(
    session: AsyncSession, language: str = "english"
) -> PostgresFullTextSearch:
    """Get PostgreSQL FTS instance."""
    return PostgresFullTextSearch(session=session, language=language)
