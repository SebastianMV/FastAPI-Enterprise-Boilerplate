# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for PostgreSQL Full-Text Search implementation."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.infrastructure.search.postgres_fts import (
    PostgresFullTextSearch,
    INDEX_CONFIGS,
    get_postgres_search,
)
from app.domain.ports.search import (
    SearchQuery,
    SearchResult,
    SearchHit,
    SearchFilter,
    SearchSort,
    SearchIndex,
    IndexDocument,
    BulkIndexResult,
    SortOrder,
    SearchHighlight,
)


class TestPostgresFullTextSearchInit:
    """Tests for PostgresFullTextSearch initialization."""

    def test_init_with_default_language(self):
        """Test initialization with default language."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        assert fts._session is session
        assert fts._language == "english"

    def test_init_with_custom_language(self):
        """Test initialization with custom language."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session, language="spanish")
        
        assert fts._language == "spanish"


class TestIndexConfigs:
    """Tests for INDEX_CONFIGS."""

    def test_users_config_exists(self):
        """Test that users config exists."""
        assert SearchIndex.USERS in INDEX_CONFIGS
        config = INDEX_CONFIGS[SearchIndex.USERS]
        assert config["table"] == "users"
        assert config["id_column"] == "id"
        assert "email" in config["search_columns"]

    def test_posts_config_exists(self):
        """Test that posts config exists."""
        assert SearchIndex.POSTS in INDEX_CONFIGS
        config = INDEX_CONFIGS[SearchIndex.POSTS]
        assert config["table"] == "posts"
        assert "title" in config["search_columns"]

    def test_messages_config_exists(self):
        """Test that messages config exists."""
        assert SearchIndex.MESSAGES in INDEX_CONFIGS
        config = INDEX_CONFIGS[SearchIndex.MESSAGES]
        assert config["table"] == "messages"

    def test_documents_config_exists(self):
        """Test that documents config exists."""
        assert SearchIndex.DOCUMENTS in INDEX_CONFIGS

    def test_audit_logs_config_exists(self):
        """Test that audit_logs config exists."""
        assert SearchIndex.AUDIT_LOGS in INDEX_CONFIGS
        config = INDEX_CONFIGS[SearchIndex.AUDIT_LOGS]
        assert config["deleted_column"] is None  # No soft delete


class TestPostgresFullTextSearchSearch:
    """Tests for search method."""

    @pytest.mark.asyncio
    async def test_search_with_results(self):
        """Test search returning results."""
        session = AsyncMock()
        
        # Create mock row
        mock_row = MagicMock()
        mock_row.id = "123"
        mock_row.score = 0.75
        mock_row.source = {"email": "test@example.com"}
        mock_row.highlight_email = "test highlighted"
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        session.execute = AsyncMock(side_effect=[mock_result, mock_count_result])
        
        fts = PostgresFullTextSearch(session=session)
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
        )
        
        result = await fts.search(query)
        
        assert len(result.hits) == 1
        assert result.hits[0].id == "123"
        assert result.hits[0].score == 0.75
        assert result.max_score == 0.75


class TestPostgresFullTextSearchIndexDocument:
    """Tests for index_document method."""

    @pytest.mark.asyncio
    async def test_index_document_success(self):
        """Test successful document indexing."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        document = IndexDocument(
            id="doc-1",
            index=SearchIndex.USERS,
            data={"email": "test@example.com"},
        )
        
        result = await fts.index_document(document)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_index_document_invalid_index(self):
        """Test indexing with invalid index returns False."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        # Mock INDEX_CONFIGS to return None
        with patch.dict('app.infrastructure.search.postgres_fts.INDEX_CONFIGS', {}, clear=True):
            document = IndexDocument(
                id="doc-1",
                index=SearchIndex.USERS,
                data={"email": "test@example.com"},
            )
            
            result = await fts.index_document(document)
            
            assert result is False


class TestPostgresFullTextSearchBulkIndex:
    """Tests for bulk_index method."""

    @pytest.mark.asyncio
    async def test_bulk_index_success(self):
        """Test successful bulk indexing."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        documents = [
            IndexDocument(id="1", index=SearchIndex.USERS, data={"email": "a@test.com"}),
            IndexDocument(id="2", index=SearchIndex.USERS, data={"email": "b@test.com"}),
        ]
        
        result = await fts.bulk_index(documents)
        
        assert isinstance(result, BulkIndexResult)
        assert result.indexed == 2
        assert result.failed == 0
        assert result.took_ms >= 0

    @pytest.mark.asyncio
    async def test_bulk_index_empty(self):
        """Test bulk indexing with empty list."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.bulk_index([])
        
        assert result.indexed == 0
        assert result.failed == 0


class TestPostgresFullTextSearchDeleteDocument:
    """Tests for delete_document method."""

    @pytest.mark.asyncio
    async def test_delete_document_success(self):
        """Test successful document deletion."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.delete_document(
            index=SearchIndex.USERS,
            document_id="doc-1",
        )
        
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_document_with_tenant(self):
        """Test document deletion with tenant."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        tenant_id = uuid4()
        
        result = await fts.delete_document(
            index=SearchIndex.USERS,
            document_id="doc-1",
            tenant_id=tenant_id,
        )
        
        assert result is True


class TestPostgresFullTextSearchUpdateDocument:
    """Tests for update_document method."""

    @pytest.mark.asyncio
    async def test_update_document_success(self):
        """Test successful document update."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        document = IndexDocument(
            id="doc-1",
            index=SearchIndex.USERS,
            data={"email": "updated@test.com"},
        )
        
        result = await fts.update_document(document)
        
        assert result is True


class TestPostgresFullTextSearchGetDocument:
    """Tests for get_document method."""

    @pytest.mark.asyncio
    async def test_get_document_found(self):
        """Test getting existing document."""
        session = AsyncMock()
        
        mock_row = {"id": "doc-1", "email": "test@example.com"}
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = mock_row
        session.execute = AsyncMock(return_value=mock_result)
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.get_document(
            index=SearchIndex.USERS,
            document_id="doc-1",
        )
        
        assert result == mock_row

    @pytest.mark.asyncio
    async def test_get_document_not_found(self):
        """Test getting non-existent document."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        session.execute = AsyncMock(return_value=mock_result)
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.get_document(
            index=SearchIndex.USERS,
            document_id="nonexistent",
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_document_with_tenant(self):
        """Test getting document with tenant filter."""
        session = AsyncMock()
        tenant_id = uuid4()
        
        mock_row = {"id": "doc-1", "email": "test@example.com"}
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = mock_row
        session.execute = AsyncMock(return_value=mock_result)
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.get_document(
            index=SearchIndex.USERS,
            document_id="doc-1",
            tenant_id=tenant_id,
        )
        
        assert result == mock_row

    @pytest.mark.asyncio
    async def test_get_document_invalid_index(self):
        """Test getting document with invalid index."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        with patch.dict('app.infrastructure.search.postgres_fts.INDEX_CONFIGS', {}, clear=True):
            result = await fts.get_document(
                index=SearchIndex.USERS,
                document_id="doc-1",
            )
            
            assert result is None


class TestPostgresFullTextSearchSuggest:
    """Tests for suggest method."""

    @pytest.mark.asyncio
    async def test_suggest_success(self):
        """Test successful suggestions."""
        session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("suggestion1",), ("suggestion2",)]
        session.execute = AsyncMock(return_value=mock_result)
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.suggest(
            query="test",
            index=SearchIndex.USERS,
        )
        
        assert result == ["suggestion1", "suggestion2"]

    @pytest.mark.asyncio
    async def test_suggest_fallback_to_ilike(self):
        """Test suggestions falling back to ILIKE."""
        session = AsyncMock()
        
        # First call fails (trigram), second succeeds (ILIKE)
        mock_fallback_result = MagicMock()
        mock_fallback_result.fetchall.return_value = [("fallback",)]
        
        session.execute = AsyncMock(side_effect=[
            Exception("pg_trgm not available"),
            mock_fallback_result,
        ])
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.suggest(
            query="test",
            index=SearchIndex.USERS,
        )
        
        assert result == ["fallback"]

    @pytest.mark.asyncio
    async def test_suggest_invalid_index(self):
        """Test suggestions with invalid index."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        with patch.dict('app.infrastructure.search.postgres_fts.INDEX_CONFIGS', {}, clear=True):
            result = await fts.suggest(
                query="test",
                index=SearchIndex.USERS,
            )
            
            assert result == []


class TestPostgresFullTextSearchReindex:
    """Tests for reindex method."""

    @pytest.mark.asyncio
    async def test_reindex_success(self):
        """Test successful reindex."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.reindex(index=SearchIndex.USERS)
        
        assert isinstance(result, BulkIndexResult)
        assert result.indexed == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_reindex_invalid_index(self):
        """Test reindex with invalid index."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        with patch.dict('app.infrastructure.search.postgres_fts.INDEX_CONFIGS', {}, clear=True):
            result = await fts.reindex(index=SearchIndex.USERS)
            
            assert result.indexed == 0
            assert result.failed == 0


class TestPostgresFullTextSearchCreateIndex:
    """Tests for create_index method."""

    @pytest.mark.asyncio
    async def test_create_index_success(self):
        """Test successful index creation."""
        session = AsyncMock()
        session.execute = AsyncMock()
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.create_index(index=SearchIndex.USERS)
        
        assert result is True
        assert session.execute.called

    @pytest.mark.asyncio
    async def test_create_index_failure(self):
        """Test index creation failure."""
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=Exception("Create failed"))
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.create_index(index=SearchIndex.USERS)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_create_index_invalid_index(self):
        """Test index creation with invalid index."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        with patch.dict('app.infrastructure.search.postgres_fts.INDEX_CONFIGS', {}, clear=True):
            result = await fts.create_index(index=SearchIndex.USERS)
            
            assert result is False


class TestPostgresFullTextSearchDeleteIndex:
    """Tests for delete_index method."""

    @pytest.mark.asyncio
    async def test_delete_index_success(self):
        """Test successful index deletion."""
        session = AsyncMock()
        session.execute = AsyncMock()
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.delete_index(index=SearchIndex.USERS)
        
        assert result is True
        assert session.execute.called

    @pytest.mark.asyncio
    async def test_delete_index_failure(self):
        """Test index deletion failure."""
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=Exception("Delete failed"))
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.delete_index(index=SearchIndex.USERS)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_index_invalid_index(self):
        """Test index deletion with invalid index."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        with patch.dict('app.infrastructure.search.postgres_fts.INDEX_CONFIGS', {}, clear=True):
            result = await fts.delete_index(index=SearchIndex.USERS)
            
            assert result is False


class TestPostgresFullTextSearchHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test healthy status."""
        session = AsyncMock()
        
        mock_fts_result = MagicMock()
        mock_fts_result.scalar.return_value = True
        
        mock_trgm_result = MagicMock()
        mock_trgm_result.scalar.return_value = True
        
        session.execute = AsyncMock(side_effect=[mock_fts_result, mock_trgm_result])
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.health_check()
        
        assert result["status"] == "healthy"
        assert result["backend"] == "postgresql"
        assert result["fts_available"] is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test unhealthy status."""
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=Exception("Connection failed"))
        
        fts = PostgresFullTextSearch(session=session)
        
        result = await fts.health_check()
        
        assert result["status"] == "unhealthy"
        assert result["backend"] == "postgresql"


class TestParseSearchQuery:
    """Tests for _parse_search_query method."""

    def test_parse_empty_query(self):
        """Test parsing empty query."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        result = fts._parse_search_query("")
        assert result == ""
        
        result = fts._parse_search_query("   ")
        assert result == ""

    def test_parse_simple_terms(self):
        """Test parsing simple terms."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        result = fts._parse_search_query("hello world")
        assert "hello" in result
        assert "world" in result
        assert "&" in result

    def test_parse_negation(self):
        """Test parsing negation with minus."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        result = fts._parse_search_query("hello -world")
        assert "hello" in result
        assert "!world" in result

    def test_parse_or_operator(self):
        """Test parsing OR operator."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        result = fts._parse_search_query("hello | world")
        assert "|" in result

    def test_parse_prefix_wildcard(self):
        """Test parsing prefix wildcard."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        result = fts._parse_search_query("hello*")
        assert "hello:*" in result

    def test_parse_quoted_phrase(self):
        """Test parsing quoted phrase."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        result = fts._parse_search_query('"hello world"')
        assert "<->" in result


class TestBuildFilterClause:
    """Tests for _build_filter_clause method."""

    def test_build_eq_filter(self):
        """Test building equality filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="status", value="active", operator="eq")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert "status" in result
        assert ":filter_0" in result

    def test_build_ne_filter(self):
        """Test building not-equal filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="status", value="deleted", operator="ne")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert "!=" in result

    def test_build_gt_filter(self):
        """Test building greater-than filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="count", value=10, operator="gt")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert ">" in result

    def test_build_gte_filter(self):
        """Test building greater-than-or-equal filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="count", value=10, operator="gte")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert ">=" in result

    def test_build_lt_filter(self):
        """Test building less-than filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="count", value=10, operator="lt")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert "<" in result

    def test_build_lte_filter(self):
        """Test building less-than-or-equal filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="count", value=10, operator="lte")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert "<=" in result

    def test_build_in_filter(self):
        """Test building IN filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="status", value=["a", "b"], operator="in")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert "ANY" in result

    def test_build_contains_filter(self):
        """Test building contains filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="name", value="test", operator="contains")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert "ILIKE" in result
        assert "%" in result

    def test_build_startswith_filter(self):
        """Test building startswith filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="name", value="test", operator="startswith")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert "ILIKE" in result

    def test_build_endswith_filter(self):
        """Test building endswith filter."""
        session = AsyncMock()
        fts = PostgresFullTextSearch(session=session)
        
        filter = SearchFilter(field="name", value="test", operator="endswith")
        result = fts._build_filter_clause(filter, "filter_0")
        
        assert "ILIKE" in result


class TestGetPostgresSearch:
    """Tests for factory function."""

    def test_get_postgres_search_default(self):
        """Test factory with defaults."""
        session = AsyncMock()
        fts = get_postgres_search(session)
        
        assert isinstance(fts, PostgresFullTextSearch)
        assert fts._language == "english"

    def test_get_postgres_search_custom_language(self):
        """Test factory with custom language."""
        session = AsyncMock()
        fts = get_postgres_search(session, language="german")
        
        assert isinstance(fts, PostgresFullTextSearch)
        assert fts._language == "german"
