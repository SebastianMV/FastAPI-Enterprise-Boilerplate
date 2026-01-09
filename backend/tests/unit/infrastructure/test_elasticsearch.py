# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for Elasticsearch Full-Text Search implementation."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

from app.infrastructure.search.elasticsearch import (
    ElasticsearchSearch,
    INDEX_MAPPINGS,
    get_elasticsearch_search,
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


class TestElasticsearchSearchInit:
    """Tests for ElasticsearchSearch initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        es = ElasticsearchSearch()
        
        assert es._url == "http://localhost:9200"
        assert es._index_prefix == "app"
        assert es._client is None
        assert es._username is None
        assert es._password is None
        assert es._verify_certs is True

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        es = ElasticsearchSearch(
            elasticsearch_url="http://custom:9200",
            index_prefix="myapp",
            username="user",
            password="pass",
            verify_certs=False,
        )
        
        assert es._url == "http://custom:9200"
        assert es._index_prefix == "myapp"
        assert es._username == "user"
        assert es._password == "pass"
        assert es._verify_certs is False


class TestIndexMappings:
    """Tests for INDEX_MAPPINGS configuration."""

    def test_users_mapping_exists(self):
        """Test that users mapping exists."""
        assert SearchIndex.USERS in INDEX_MAPPINGS
        mapping = INDEX_MAPPINGS[SearchIndex.USERS]
        assert "settings" in mapping
        assert "mappings" in mapping

    def test_posts_mapping_exists(self):
        """Test that posts mapping exists."""
        assert SearchIndex.POSTS in INDEX_MAPPINGS

    def test_messages_mapping_exists(self):
        """Test that messages mapping exists."""
        assert SearchIndex.MESSAGES in INDEX_MAPPINGS

    def test_documents_mapping_exists(self):
        """Test that documents mapping exists."""
        assert SearchIndex.DOCUMENTS in INDEX_MAPPINGS

    def test_audit_logs_mapping_exists(self):
        """Test that audit_logs mapping exists."""
        assert SearchIndex.AUDIT_LOGS in INDEX_MAPPINGS


class TestElasticsearchSearchGetClient:
    """Tests for _get_client method."""

    @pytest.mark.asyncio
    async def test_get_client_reuses_client(self):
        """Test that _get_client reuses existing client."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        es._client = mock_client
        
        client = await es._get_client()
        
        assert client == mock_client


class TestElasticsearchSearchGetIndexName:
    """Tests for _get_index_name method."""

    def test_get_index_name(self):
        """Test index name generation."""
        es = ElasticsearchSearch(index_prefix="myapp")
        
        result = es._get_index_name(SearchIndex.USERS)
        
        assert result == "myapp_users"

    def test_get_index_name_different_indices(self):
        """Test index name for different indices."""
        es = ElasticsearchSearch(index_prefix="app")
        
        assert es._get_index_name(SearchIndex.USERS) == "app_users"
        assert es._get_index_name(SearchIndex.POSTS) == "app_posts"
        assert es._get_index_name(SearchIndex.MESSAGES) == "app_messages"


class TestElasticsearchSearchSearch:
    """Tests for search method."""

    @pytest.mark.asyncio
    async def test_search_basic(self):
        """Test basic search execution."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={
            "hits": {
                "total": {"value": 0},
                "max_score": None,
                "hits": [],
            }
        })
        es._client = mock_client
        
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
        )
        
        result = await es.search(query)
        
        assert isinstance(result, SearchResult)
        assert result.total == 0
        assert result.hits == []

    @pytest.mark.asyncio
    async def test_search_with_results(self):
        """Test search with results."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={
            "hits": {
                "total": {"value": 1},
                "max_score": 1.5,
                "hits": [
                    {
                        "_id": "123",
                        "_score": 1.5,
                        "_source": {"email": "test@example.com"},
                        "highlight": {"email": ["<mark>test</mark>@example.com"]},
                    }
                ],
            }
        })
        es._client = mock_client
        
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
        )
        
        result = await es.search(query)
        
        assert result.total == 1
        assert len(result.hits) == 1
        assert result.hits[0].id == "123"
        assert result.hits[0].score == 1.5
        assert result.max_score == 1.5

    @pytest.mark.asyncio
    async def test_search_with_fuzzy(self):
        """Test search with fuzzy matching enabled."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        })
        es._client = mock_client
        
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
            fuzzy=True,
            fuzzy_max_edits=1,
        )
        
        result = await es.search(query)
        
        # Verify search was called
        assert mock_client.search.called
        assert isinstance(result, SearchResult)

    @pytest.mark.asyncio
    async def test_search_with_tenant_filter(self):
        """Test search with tenant filter."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={
            "hits": {"total": {"value": 0}, "hits": []}
        })
        es._client = mock_client
        
        tenant_id = uuid4()
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
            tenant_id=tenant_id,
        )
        
        await es.search(query)
        
        call_body = mock_client.search.call_args[1]["body"]
        assert "tenant_id" in str(call_body)

    @pytest.mark.asyncio
    async def test_search_with_sort(self):
        """Test search with sorting."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        })
        es._client = mock_client
        
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
            sort=[SearchSort(field="created_at", order=SortOrder.DESC)],
        )
        
        result = await es.search(query)
        
        assert mock_client.search.called
        assert isinstance(result, SearchResult)

    @pytest.mark.asyncio
    async def test_search_with_highlight_config(self):
        """Test search with highlight configuration."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        })
        es._client = mock_client
        
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
            highlight=SearchHighlight(
                fields=["email", "full_name"],
                pre_tag="<em>",
                post_tag="</em>",
            ),
        )
        
        result = await es.search(query)
        
        assert mock_client.search.called
        assert isinstance(result, SearchResult)

    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """Test search with additional filters."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={
            "hits": {"total": {"value": 0}, "max_score": None, "hits": []}
        })
        es._client = mock_client
        
        query = SearchQuery(
            query="test",
            index=SearchIndex.USERS,
            filters=[SearchFilter(field="is_active", value=True, operator="eq")],
        )
        
        result = await es.search(query)
        
        assert mock_client.search.called
        assert isinstance(result, SearchResult)


class TestElasticsearchSearchIndexDocument:
    """Tests for index_document method."""

    @pytest.mark.asyncio
    async def test_index_document_success(self):
        """Test successful document indexing."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.index = AsyncMock()
        es._client = mock_client
        
        document = IndexDocument(
            id="doc-1",
            index=SearchIndex.USERS,
            data={"email": "test@example.com"},
        )
        
        result = await es.index_document(document)
        
        assert result is True
        mock_client.index.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_document_with_routing(self):
        """Test document indexing with routing."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.index = AsyncMock()
        es._client = mock_client
        
        document = IndexDocument(
            id="doc-1",
            index=SearchIndex.USERS,
            data={"email": "test@example.com"},
            routing="tenant-123",
        )
        
        await es.index_document(document)
        
        call_kwargs = mock_client.index.call_args[1]
        assert call_kwargs["routing"] == "tenant-123"

    @pytest.mark.asyncio
    async def test_index_document_failure(self):
        """Test document indexing failure."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.index = AsyncMock(side_effect=Exception("Index failed"))
        es._client = mock_client
        
        document = IndexDocument(
            id="doc-1",
            index=SearchIndex.USERS,
            data={"email": "test@example.com"},
        )
        
        result = await es.index_document(document)
        
        assert result is False


class TestElasticsearchSearchBulkIndex:
    """Tests for bulk_index method."""

    @pytest.mark.asyncio
    async def test_bulk_index_requires_elasticsearch(self):
        """Test bulk indexing requires elasticsearch package.
        
        Note: This test verifies behavior when elasticsearch is not installed.
        The actual bulk_index functionality depends on the elasticsearch package.
        """
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        es._client = mock_client
        
        documents = [
            IndexDocument(id="1", index=SearchIndex.USERS, data={"email": "a@test.com"}),
        ]
        
        # The elasticsearch module is not installed in test environment
        # bulk_index will fail at import but should handle gracefully
        try:
            result = await es.bulk_index(documents)
            # If no error, check the result
            assert isinstance(result, BulkIndexResult)
        except ModuleNotFoundError:
            # Expected when elasticsearch is not installed
            pytest.skip("elasticsearch package not installed")


class TestElasticsearchSearchDeleteDocument:
    """Tests for delete_document method."""

    @pytest.mark.asyncio
    async def test_delete_document_success(self):
        """Test successful document deletion."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock()
        es._client = mock_client
        
        result = await es.delete_document(
            index=SearchIndex.USERS,
            document_id="doc-1",
        )
        
        assert result is True
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_document_failure(self):
        """Test document deletion failure."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(side_effect=Exception("Delete failed"))
        es._client = mock_client
        
        result = await es.delete_document(
            index=SearchIndex.USERS,
            document_id="doc-1",
        )
        
        assert result is False


class TestElasticsearchSearchUpdateDocument:
    """Tests for update_document method."""

    @pytest.mark.asyncio
    async def test_update_document_success(self):
        """Test successful document update."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.update = AsyncMock()
        es._client = mock_client
        
        document = IndexDocument(
            id="doc-1",
            index=SearchIndex.USERS,
            data={"email": "updated@test.com"},
        )
        
        result = await es.update_document(document)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_update_document_with_upsert(self):
        """Test document update with upsert."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.update = AsyncMock()
        es._client = mock_client
        
        document = IndexDocument(
            id="doc-1",
            index=SearchIndex.USERS,
            data={"email": "updated@test.com"},
        )
        
        await es.update_document(document, upsert=True)
        
        call_body = mock_client.update.call_args[1]["body"]
        assert call_body["doc_as_upsert"] is True

    @pytest.mark.asyncio
    async def test_update_document_failure(self):
        """Test document update failure."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.update = AsyncMock(side_effect=Exception("Update failed"))
        es._client = mock_client
        
        document = IndexDocument(
            id="doc-1",
            index=SearchIndex.USERS,
            data={},
        )
        
        result = await es.update_document(document)
        
        assert result is False


class TestElasticsearchSearchGetDocument:
    """Tests for get_document method."""

    @pytest.mark.asyncio
    async def test_get_document_found(self):
        """Test getting existing document."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value={
            "_source": {"email": "test@example.com"}
        })
        es._client = mock_client
        
        result = await es.get_document(
            index=SearchIndex.USERS,
            document_id="doc-1",
        )
        
        assert result == {"email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_get_document_not_found(self):
        """Test getting non-existent document."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Not found"))
        es._client = mock_client
        
        result = await es.get_document(
            index=SearchIndex.USERS,
            document_id="nonexistent",
        )
        
        assert result is None


class TestElasticsearchSearchSuggest:
    """Tests for suggest method."""

    @pytest.mark.asyncio
    async def test_suggest_success(self):
        """Test successful suggestions."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value={
            "suggest": {
                "suggestions": [
                    {
                        "options": [
                            {"text": "suggestion1"},
                            {"text": "suggestion2"},
                        ]
                    }
                ]
            }
        })
        es._client = mock_client
        
        result = await es.suggest(
            query="test",
            index=SearchIndex.USERS,
        )
        
        assert result == ["suggestion1", "suggestion2"]

    @pytest.mark.asyncio
    async def test_suggest_fallback_to_prefix(self):
        """Test suggestions falling back to prefix query."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        
        # First call fails, second succeeds
        mock_client.search = AsyncMock(side_effect=[
            Exception("Completion failed"),
            {"hits": {"hits": [{"_source": {"title": "fallback"}}]}},
        ])
        es._client = mock_client
        
        result = await es.suggest(
            query="test",
            index=SearchIndex.USERS,
        )
        
        assert result == ["fallback"]

    @pytest.mark.asyncio
    async def test_suggest_complete_failure(self):
        """Test suggestions complete failure."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(side_effect=Exception("All failed"))
        es._client = mock_client
        
        result = await es.suggest(
            query="test",
            index=SearchIndex.USERS,
        )
        
        assert result == []


class TestElasticsearchSearchReindex:
    """Tests for reindex method."""

    @pytest.mark.asyncio
    async def test_reindex_returns_result(self):
        """Test reindex returns BulkIndexResult."""
        es = ElasticsearchSearch()
        
        result = await es.reindex(index=SearchIndex.USERS)
        
        assert isinstance(result, BulkIndexResult)
        assert result.indexed == 0
        assert result.failed == 0


class TestElasticsearchSearchCreateIndex:
    """Tests for create_index method."""

    @pytest.mark.asyncio
    async def test_create_index_success(self):
        """Test successful index creation."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.indices = AsyncMock()
        mock_client.indices.exists = AsyncMock(return_value=False)
        mock_client.indices.create = AsyncMock()
        es._client = mock_client
        
        result = await es.create_index(index=SearchIndex.USERS)
        
        assert result is True
        mock_client.indices.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_index_already_exists(self):
        """Test index creation when index already exists."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.indices = AsyncMock()
        mock_client.indices.exists = AsyncMock(return_value=True)
        es._client = mock_client
        
        result = await es.create_index(index=SearchIndex.USERS)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_create_index_failure(self):
        """Test index creation failure."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.indices = AsyncMock()
        mock_client.indices.exists = AsyncMock(return_value=False)
        mock_client.indices.create = AsyncMock(side_effect=Exception("Create failed"))
        es._client = mock_client
        
        result = await es.create_index(index=SearchIndex.USERS)
        
        assert result is False


class TestElasticsearchSearchDeleteIndex:
    """Tests for delete_index method."""

    @pytest.mark.asyncio
    async def test_delete_index_success(self):
        """Test successful index deletion."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.indices = AsyncMock()
        mock_client.indices.delete = AsyncMock()
        es._client = mock_client
        
        result = await es.delete_index(index=SearchIndex.USERS)
        
        assert result is True
        mock_client.indices.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_index_failure(self):
        """Test index deletion failure."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.indices = AsyncMock()
        mock_client.indices.delete = AsyncMock(side_effect=Exception("Delete failed"))
        es._client = mock_client
        
        result = await es.delete_index(index=SearchIndex.USERS)
        
        assert result is False


class TestElasticsearchSearchHealthCheck:
    """Tests for health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test healthy cluster status."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.cluster = AsyncMock()
        mock_client.cluster.health = AsyncMock(return_value={
            "status": "green",
            "cluster_name": "test-cluster",
            "number_of_nodes": 1,
            "active_shards": 5,
        })
        es._client = mock_client
        
        result = await es.health_check()
        
        assert result["status"] == "green"
        assert result["backend"] == "elasticsearch"
        assert result["cluster_name"] == "test-cluster"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test unhealthy cluster status."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.cluster = AsyncMock()
        mock_client.cluster.health = AsyncMock(side_effect=Exception("Connection failed"))
        es._client = mock_client
        
        result = await es.health_check()
        
        assert result["status"] == "unhealthy"
        assert result["backend"] == "elasticsearch"
        assert "error" in result


class TestElasticsearchSearchClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_with_client(self):
        """Test closing client."""
        es = ElasticsearchSearch()
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        es._client = mock_client
        
        await es.close()
        
        mock_client.close.assert_called_once()
        assert es._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self):
        """Test closing when no client exists."""
        es = ElasticsearchSearch()
        
        # Should not raise
        await es.close()


class TestElasticsearchSearchGetSearchFields:
    """Tests for _get_search_fields method."""

    def test_get_search_fields_users(self):
        """Test getting search fields for users."""
        es = ElasticsearchSearch()
        
        fields = es._get_search_fields(SearchIndex.USERS)
        
        assert "email^2" in fields
        assert "full_name^3" in fields

    def test_get_search_fields_posts(self):
        """Test getting search fields for posts."""
        es = ElasticsearchSearch()
        
        fields = es._get_search_fields(SearchIndex.POSTS)
        
        assert "title^3" in fields
        assert "content" in fields

    def test_get_search_fields_with_boost(self):
        """Test getting search fields with custom boost."""
        es = ElasticsearchSearch()
        
        boost_fields = {"email": 5.0, "full_name": 10.0}
        fields = es._get_search_fields(SearchIndex.USERS, boost_fields)
        
        assert "email^5.0" in fields
        assert "full_name^10.0" in fields


class TestElasticsearchSearchBuildFilter:
    """Tests for _build_filter method."""

    def test_build_eq_filter(self):
        """Test building equality filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="status", value="active", operator="eq")
        result = es._build_filter(filter)
        
        assert result == {"term": {"status": "active"}}

    def test_build_ne_filter(self):
        """Test building not-equal filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="status", value="deleted", operator="ne")
        result = es._build_filter(filter)
        
        assert "bool" in result
        assert "must_not" in result["bool"]

    def test_build_gt_filter(self):
        """Test building greater-than filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="count", value=10, operator="gt")
        result = es._build_filter(filter)
        
        assert result == {"range": {"count": {"gt": 10}}}

    def test_build_gte_filter(self):
        """Test building greater-than-or-equal filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="count", value=10, operator="gte")
        result = es._build_filter(filter)
        
        assert result == {"range": {"count": {"gte": 10}}}

    def test_build_lt_filter(self):
        """Test building less-than filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="count", value=10, operator="lt")
        result = es._build_filter(filter)
        
        assert result == {"range": {"count": {"lt": 10}}}

    def test_build_lte_filter(self):
        """Test building less-than-or-equal filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="count", value=10, operator="lte")
        result = es._build_filter(filter)
        
        assert result == {"range": {"count": {"lte": 10}}}

    def test_build_in_filter(self):
        """Test building IN filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="status", value=["a", "b"], operator="in")
        result = es._build_filter(filter)
        
        assert result == {"terms": {"status": ["a", "b"]}}

    def test_build_contains_filter(self):
        """Test building contains filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="name", value="test", operator="contains")
        result = es._build_filter(filter)
        
        assert result == {"wildcard": {"name": "*test*"}}

    def test_build_startswith_filter(self):
        """Test building startswith filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="name", value="test", operator="startswith")
        result = es._build_filter(filter)
        
        assert result == {"prefix": {"name": "test"}}

    def test_build_endswith_filter(self):
        """Test building endswith filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="name", value="test", operator="endswith")
        result = es._build_filter(filter)
        
        assert result == {"wildcard": {"name": "*test"}}

    def test_build_unknown_filter_defaults_to_term(self):
        """Test unknown operator defaults to term filter."""
        es = ElasticsearchSearch()
        
        filter = SearchFilter(field="name", value="test", operator="unknown")
        result = es._build_filter(filter)
        
        assert result == {"term": {"name": "test"}}


class TestGetElasticsearchSearch:
    """Tests for factory function."""

    def test_get_elasticsearch_search_defaults(self):
        """Test factory with defaults."""
        es = get_elasticsearch_search()
        
        assert isinstance(es, ElasticsearchSearch)
        assert es._url == "http://localhost:9200"
        assert es._index_prefix == "app"

    def test_get_elasticsearch_search_custom(self):
        """Test factory with custom parameters."""
        es = get_elasticsearch_search(
            url="http://custom:9200",
            index_prefix="myapp",
            username="user",
            password="pass",
        )
        
        assert isinstance(es, ElasticsearchSearch)
        assert es._url == "http://custom:9200"
        assert es._index_prefix == "myapp"
        assert es._username == "user"
        assert es._password == "pass"
