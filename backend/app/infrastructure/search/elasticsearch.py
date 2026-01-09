# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Elasticsearch/OpenSearch Full-Text Search implementation.

Uses Elasticsearch for advanced search capabilities:
- Distributed search
- Complex queries (bool, multi-match, etc.)
- Aggregations and analytics
- Advanced highlighting
- Fuzzy matching
- Auto-suggestions
"""

import logging
import time
from typing import Any
from uuid import UUID

from app.domain.ports.search import (
    SearchPort,
    SearchQuery,
    SearchResult,
    SearchHit,
    SearchFilter,
    SearchIndex,
    IndexDocument,
    BulkIndexResult,
    SortOrder,
)


logger = logging.getLogger(__name__)


# Index mappings for Elasticsearch
INDEX_MAPPINGS: dict[SearchIndex, dict[str, Any]] = {
    SearchIndex.USERS: {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "email_analyzer": {
                        "type": "custom",
                        "tokenizer": "uax_url_email",
                        "filter": ["lowercase"],
                    },
                },
            },
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "tenant_id": {"type": "keyword"},
                "email": {
                    "type": "text",
                    "analyzer": "email_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"},
                    },
                },
                "full_name": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"},
                        "suggest": {
                            "type": "completion",
                        },
                    },
                },
                "username": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"},
                    },
                },
                "is_active": {"type": "boolean"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "deleted_at": {"type": "date"},
            },
        },
    },
    SearchIndex.POSTS: {
        "settings": {
            "number_of_shards": 2,
            "number_of_replicas": 1,
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "tenant_id": {"type": "keyword"},
                "author_id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"},
                        "suggest": {"type": "completion"},
                    },
                },
                "content": {"type": "text"},
                "tags": {"type": "keyword"},
                "status": {"type": "keyword"},
                "published_at": {"type": "date"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "deleted_at": {"type": "date"},
            },
        },
    },
    SearchIndex.MESSAGES: {
        "settings": {
            "number_of_shards": 2,
            "number_of_replicas": 1,
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "tenant_id": {"type": "keyword"},
                "room_id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "content": {"type": "text"},
                "type": {"type": "keyword"},
                "created_at": {"type": "date"},
                "deleted_at": {"type": "date"},
            },
        },
    },
    SearchIndex.DOCUMENTS: {
        "settings": {
            "number_of_shards": 2,
            "number_of_replicas": 1,
            "analysis": {
                "analyzer": {
                    "content_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "stop", "snowball"],
                    },
                },
            },
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "tenant_id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"},
                        "suggest": {"type": "completion"},
                    },
                },
                "content": {
                    "type": "text",
                    "analyzer": "content_analyzer",
                },
                "description": {"type": "text"},
                "tags": {"type": "keyword"},
                "file_type": {"type": "keyword"},
                "size": {"type": "long"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "deleted_at": {"type": "date"},
            },
        },
    },
    SearchIndex.AUDIT_LOGS: {
        "settings": {
            "number_of_shards": 2,
            "number_of_replicas": 1,
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "tenant_id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "action": {"type": "keyword"},
                "resource_type": {"type": "keyword"},
                "resource_id": {"type": "keyword"},
                "details": {"type": "text"},
                "ip_address": {"type": "ip"},
                "user_agent": {"type": "text"},
                "timestamp": {"type": "date"},
            },
        },
    },
}


class ElasticsearchSearch(SearchPort):
    """
    Elasticsearch Full-Text Search implementation.
    
    Features:
    - Advanced querying (bool, multi-match, fuzzy)
    - Highlighting with customization
    - Aggregations for analytics
    - Auto-complete suggestions
    - Distributed and scalable
    """
    
    def __init__(
        self,
        elasticsearch_url: str = "http://localhost:9200",
        index_prefix: str = "app",
        username: str | None = None,
        password: str | None = None,
        verify_certs: bool = True,
    ) -> None:
        """
        Initialize Elasticsearch client.
        
        Args:
            elasticsearch_url: Elasticsearch server URL
            index_prefix: Prefix for index names
            username: Authentication username
            password: Authentication password
            verify_certs: Verify SSL certificates
        """
        self._url = elasticsearch_url
        self._index_prefix = index_prefix
        self._client: Any = None
        self._username = username
        self._password = password
        self._verify_certs = verify_certs
    
    async def _get_client(self) -> Any:
        """Get or create Elasticsearch client."""
        if self._client is None:
            try:
                from elasticsearch import AsyncElasticsearch  # type: ignore[import-not-found]
                
                auth = None
                if self._username and self._password:
                    auth = (self._username, self._password)
                
                self._client = AsyncElasticsearch(
                    hosts=[self._url],
                    basic_auth=auth,
                    verify_certs=self._verify_certs,
                )
            except ImportError:
                raise RuntimeError(
                    "elasticsearch package not installed. "
                    "Install with: pip install elasticsearch[async]"
                )
        
        return self._client
    
    def _get_index_name(self, index: SearchIndex) -> str:
        """Get full index name with prefix."""
        return f"{self._index_prefix}_{index.value}"
    
    async def search(
        self,
        query: SearchQuery,
    ) -> SearchResult[dict[str, Any]]:
        """Execute search using Elasticsearch."""
        start_time = time.perf_counter()
        client = await self._get_client()
        
        index_name = self._get_index_name(query.index)
        
        # Build query
        must_clauses: list[dict[str, Any]] = []
        filter_clauses: list[dict[str, Any]] = []
        should_clauses: list[dict[str, Any]] = []
        
        # Main text query
        if query.query:
            if query.fuzzy:
                must_clauses.append({
                    "multi_match": {
                        "query": query.query,
                        "fields": self._get_search_fields(query.index, query.boost_fields),
                        "fuzziness": query.fuzzy_max_edits,
                        "prefix_length": 2,
                    }
                })
            else:
                must_clauses.append({
                    "multi_match": {
                        "query": query.query,
                        "fields": self._get_search_fields(query.index, query.boost_fields),
                    }
                })
        
        # Tenant filter
        if query.tenant_id:
            filter_clauses.append({
                "term": {"tenant_id": str(query.tenant_id)}
            })
        
        # Soft delete filter
        if not query.include_deleted:
            filter_clauses.append({
                "bool": {
                    "must_not": {
                        "exists": {"field": "deleted_at"}
                    }
                }
            })
        
        # Additional filters
        for f in query.filters:
            filter_clauses.append(self._build_filter(f))
        
        # Build final query
        es_query: dict[str, Any] = {
            "bool": {}
        }
        
        if must_clauses:
            es_query["bool"]["must"] = must_clauses
        if filter_clauses:
            es_query["bool"]["filter"] = filter_clauses
        if should_clauses:
            es_query["bool"]["should"] = should_clauses
        
        if query.minimum_should_match:
            es_query["bool"]["minimum_should_match"] = query.minimum_should_match
        
        # Build search body
        body: dict[str, Any] = {
            "query": es_query if es_query["bool"] else {"match_all": {}},
            "from": (query.page - 1) * query.page_size,
            "size": query.page_size,
            "track_total_hits": True,
        }
        
        # Sort
        if query.sort:
            body["sort"] = [
                {s.field: {"order": s.order.value}}
                for s in query.sort
            ]
            body["sort"].append({"_score": {"order": "desc"}})
        else:
            body["sort"] = [{"_score": {"order": "desc"}}]
        
        # Highlighting
        if query.highlight:
            body["highlight"] = {
                "fields": {
                    field: {
                        "fragment_size": query.highlight.fragment_size,
                        "number_of_fragments": query.highlight.number_of_fragments,
                    }
                    for field in query.highlight.fields
                },
                "pre_tags": [query.highlight.pre_tag],
                "post_tags": [query.highlight.post_tag],
            }
        else:
            # Default highlighting
            body["highlight"] = {
                "fields": {"*": {}},
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
            }
        
        # Execute search
        response = await client.search(
            index=index_name,
            body=body,
        )
        
        # Parse response
        hits_data = response.get("hits", {})
        total = hits_data.get("total", {}).get("value", 0)
        max_score = hits_data.get("max_score")
        
        hits: list[SearchHit[dict[str, Any]]] = []
        for hit in hits_data.get("hits", []):
            highlights: dict[str, list[str]] = {}
            if "highlight" in hit:
                highlights = hit["highlight"]
            
            hits.append(
                SearchHit(
                    id=hit["_id"],
                    score=hit.get("_score", 0.0),
                    source=hit["_source"],
                    highlights=highlights,
                    matched_fields=list(highlights.keys()),
                )
            )
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # Get suggestions if no results
        suggestions: list[str] = []
        if not hits and query.query:
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
            max_score=max_score,
            suggestions=suggestions,
        )
    
    async def index_document(
        self,
        document: IndexDocument,
    ) -> bool:
        """Index a document in Elasticsearch."""
        client = await self._get_client()
        index_name = self._get_index_name(document.index)
        
        try:
            await client.index(
                index=index_name,
                id=document.id,
                body=document.data,
                routing=document.routing,
                refresh="wait_for",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False
    
    async def bulk_index(
        self,
        documents: list[IndexDocument],
    ) -> BulkIndexResult:
        """Bulk index documents."""
        start_time = time.perf_counter()
        client = await self._get_client()
        
        from elasticsearch.helpers import async_bulk  # type: ignore[import-not-found]
        
        actions = []
        for doc in documents:
            action = {
                "_index": self._get_index_name(doc.index),
                "_id": doc.id,
                "_source": doc.data,
            }
            if doc.routing:
                action["_routing"] = doc.routing
            actions.append(action)
        
        try:
            success, errors = await async_bulk(
                client,
                actions,
                raise_on_error=False,
            )
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            error_messages = []
            if isinstance(errors, list):
                error_messages = [str(e) for e in errors[:10]]  # Limit errors
            
            return BulkIndexResult(
                indexed=success,
                failed=len(documents) - success,
                errors=error_messages,
                took_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Bulk index failed: {e}")
            
            return BulkIndexResult(
                indexed=0,
                failed=len(documents),
                errors=[str(e)],
                took_ms=elapsed_ms,
            )
    
    async def delete_document(
        self,
        index: SearchIndex,
        document_id: str,
        tenant_id: UUID | None = None,
    ) -> bool:
        """Delete document from Elasticsearch."""
        client = await self._get_client()
        index_name = self._get_index_name(index)
        
        try:
            await client.delete(
                index=index_name,
                id=document_id,
                refresh="wait_for",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    async def update_document(
        self,
        document: IndexDocument,
        upsert: bool = True,
    ) -> bool:
        """Update document in Elasticsearch."""
        client = await self._get_client()
        index_name = self._get_index_name(document.index)
        
        try:
            body: dict[str, Any] = {
                "doc": document.data,
            }
            
            if upsert:
                body["doc_as_upsert"] = True
            
            await client.update(
                index=index_name,
                id=document.id,
                body=body,
                routing=document.routing,
                refresh="wait_for",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return False
    
    async def get_document(
        self,
        index: SearchIndex,
        document_id: str,
        tenant_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        """Get document by ID."""
        client = await self._get_client()
        index_name = self._get_index_name(index)
        
        try:
            response = await client.get(
                index=index_name,
                id=document_id,
            )
            return response["_source"]
        except Exception:
            return None
    
    async def suggest(
        self,
        query: str,
        index: SearchIndex,
        field: str = "title",
        size: int = 5,
        tenant_id: UUID | None = None,
    ) -> list[str]:
        """Get search suggestions using completion suggester."""
        client = await self._get_client()
        index_name = self._get_index_name(index)
        
        # Try completion suggester
        suggest_field = f"{field}.suggest"
        
        body = {
            "suggest": {
                "suggestions": {
                    "prefix": query,
                    "completion": {
                        "field": suggest_field,
                        "size": size,
                        "skip_duplicates": True,
                    }
                }
            }
        }
        
        # Add tenant context if available
        if tenant_id:
            body["suggest"]["suggestions"]["completion"]["contexts"] = {
                "tenant_id": str(tenant_id)
            }
        
        try:
            response = await client.search(
                index=index_name,
                body=body,
            )
            
            suggestions = []
            for suggestion in response.get("suggest", {}).get("suggestions", [{}])[0].get("options", []):
                text = suggestion.get("text")
                if text:
                    suggestions.append(text)
            
            return suggestions
        except Exception as e:
            logger.warning(f"Completion suggest failed: {e}")
            
            # Fallback to prefix query
            try:
                body = {
                    "query": {
                        "prefix": {
                            field: {
                                "value": query.lower(),
                            }
                        }
                    },
                    "size": size,
                    "_source": [field],
                }
                
                response = await client.search(
                    index=index_name,
                    body=body,
                )
                
                suggestions = []
                for hit in response.get("hits", {}).get("hits", []):
                    value = hit.get("_source", {}).get(field)
                    if value and value not in suggestions:
                        suggestions.append(value)
                
                return suggestions
            except Exception as e2:
                logger.error(f"Prefix suggest failed: {e2}")
                return []
    
    async def reindex(
        self,
        index: SearchIndex,
        tenant_id: UUID | None = None,
    ) -> BulkIndexResult:
        """Reindex documents (placeholder - actual implementation depends on source)."""
        start_time = time.perf_counter()
        
        # This would typically:
        # 1. Create a new index with updated mappings
        # 2. Reindex all documents from the database
        # 3. Swap aliases
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(f"Reindex requested for {index.value}")
        
        return BulkIndexResult(
            indexed=0,
            failed=0,
            took_ms=elapsed_ms,
        )
    
    async def create_index(
        self,
        index: SearchIndex,
    ) -> bool:
        """Create Elasticsearch index with mappings."""
        client = await self._get_client()
        index_name = self._get_index_name(index)
        
        mapping = INDEX_MAPPINGS.get(index)
        if not mapping:
            logger.warning(f"No mapping defined for index: {index}")
            mapping = {}
        
        try:
            # Check if index exists
            if await client.indices.exists(index=index_name):
                logger.info(f"Index already exists: {index_name}")
                return True
            
            await client.indices.create(
                index=index_name,
                body=mapping,
            )
            logger.info(f"Created index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False
    
    async def delete_index(
        self,
        index: SearchIndex,
    ) -> bool:
        """Delete Elasticsearch index."""
        client = await self._get_client()
        index_name = self._get_index_name(index)
        
        try:
            await client.indices.delete(index=index_name)
            logger.info(f"Deleted index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False
    
    async def health_check(self) -> dict[str, Any]:
        """Check Elasticsearch cluster health."""
        try:
            client = await self._get_client()
            health = await client.cluster.health()
            
            return {
                "status": health.get("status", "unknown"),
                "backend": "elasticsearch",
                "cluster_name": health.get("cluster_name"),
                "number_of_nodes": health.get("number_of_nodes"),
                "active_shards": health.get("active_shards"),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "elasticsearch",
                "error": str(e),
            }
    
    async def close(self) -> None:
        """Close Elasticsearch client."""
        if self._client:
            await self._client.close()
            self._client = None
    
    def _get_search_fields(
        self,
        index: SearchIndex,
        boost_fields: dict[str, float] | None = None,
    ) -> list[str]:
        """Get searchable fields for an index with optional boosting."""
        # Default search fields by index
        default_fields = {
            SearchIndex.USERS: ["email^2", "full_name^3", "username"],
            SearchIndex.POSTS: ["title^3", "content", "tags^2"],
            SearchIndex.MESSAGES: ["content"],
            SearchIndex.DOCUMENTS: ["title^3", "content", "description^2", "tags"],
            SearchIndex.AUDIT_LOGS: ["action^2", "resource_type", "details"],
        }
        
        fields = default_fields.get(index, ["*"])
        
        # Apply custom boosts
        if boost_fields:
            boosted = []
            for field in fields:
                base_field = field.split("^")[0]
                if base_field in boost_fields:
                    boosted.append(f"{base_field}^{boost_fields[base_field]}")
                else:
                    boosted.append(field)
            return boosted
        
        return fields
    
    def _build_filter(self, filter: SearchFilter) -> dict[str, Any]:
        """Build Elasticsearch filter clause."""
        field = filter.field
        value = filter.value
        op = filter.operator.lower()
        
        if op == "eq":
            return {"term": {field: value}}
        elif op == "ne":
            return {"bool": {"must_not": {"term": {field: value}}}}
        elif op == "gt":
            return {"range": {field: {"gt": value}}}
        elif op == "gte":
            return {"range": {field: {"gte": value}}}
        elif op == "lt":
            return {"range": {field: {"lt": value}}}
        elif op == "lte":
            return {"range": {field: {"lte": value}}}
        elif op == "in":
            return {"terms": {field: value if isinstance(value, list) else [value]}}
        elif op == "contains":
            return {"wildcard": {field: f"*{value}*"}}
        elif op == "startswith":
            return {"prefix": {field: value}}
        elif op == "endswith":
            return {"wildcard": {field: f"*{value}"}}
        else:
            return {"term": {field: value}}


# Factory function
def get_elasticsearch_search(
    url: str = "http://localhost:9200",
    index_prefix: str = "app",
    username: str | None = None,
    password: str | None = None,
) -> ElasticsearchSearch:
    """Get Elasticsearch search instance."""
    return ElasticsearchSearch(
        elasticsearch_url=url,
        index_prefix=index_prefix,
        username=username,
        password=password,
    )
