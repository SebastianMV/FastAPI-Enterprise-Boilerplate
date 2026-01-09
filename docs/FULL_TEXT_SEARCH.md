# Full-Text Search

This document describes the Full-Text Search capabilities available in the FastAPI Enterprise Boilerplate.

## Overview

The boilerplate provides a pluggable search architecture with two backend options:

| Backend | Best For | Features |
| --- | --- | --- |
| PostgreSQL FTS | Simple deployments, existing PostgreSQL | Built-in, no extra infrastructure, GIN indexes |
| Elasticsearch | High volume, complex queries | Distributed, aggregations, fuzzy matching |

## Quick Start

### PostgreSQL FTS (Default)

No additional setup required. PostgreSQL's built-in full-text search is used by default.

```bash
# Configuration in .env
SEARCH_BACKEND=postgres
SEARCH_PG_LANGUAGE=english
```

### Elasticsearch (Optional)

```bash
# Start Elasticsearch
docker-compose -f docker-compose.yml up -d elasticsearch

# Configuration in .env
SEARCH_BACKEND=elasticsearch
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=changeme
```

## API Reference

### Search Endpoints

#### POST Search

```http
POST /api/v1/search
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "query": "search terms",
  "index": "posts",
  "filters": [
    {"field": "status", "value": "published", "operator": "eq"}
  ],
  "sort": [
    {"field": "created_at", "order": "desc"}
  ],
  "highlight_fields": ["title", "content"],
  "page": 1,
  "page_size": 20,
  "fuzzy": true
}
```

Response:

```json
{
  "hits": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "score": 0.85,
      "source": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Introduction to Search",
        "content": "Full-text search is a powerful feature..."
      },
      "highlights": {
        "title": ["Introduction to <mark>Search</mark>"],
        "content": ["Full-text <mark>search</mark> is a powerful..."]
      },
      "matched_fields": ["title", "content"]
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "has_next": true,
  "has_previous": false,
  "took_ms": 12.5,
  "max_score": 0.85,
  "suggestions": []
}
```

#### Simple Search (GET)

```http
GET /api/v1/search/simple?q=search+terms&index=posts&page=1&page_size=20
Authorization: Bearer {access_token}
```

#### Search Suggestions / Autocomplete

```http
GET /api/v1/search/suggest?q=intro&index=posts&field=title&size=5
Authorization: Bearer {access_token}
```

Response:

```json
{
  "suggestions": [
    "Introduction to Search",
    "Introduction to FastAPI",
    "Introduction to Python"
  ]
}
```

#### Health Check

```http
GET /api/v1/search/health
```

Response:

```json
{
  "status": "healthy",
  "backend": "postgres",
  "details": {
    "fts_available": true,
    "trigram_available": true,
    "language": "english"
  }
}
```

### Available Search Indices

| Index | Description | Searchable Fields |
| ----- | ----------- | ----------------- |
| `users` | User accounts | email, full_name, username |
| `posts` | Blog posts/articles | title, content, tags |
| `messages` | Chat messages | content |
| `documents` | Uploaded documents | title, content, description, tags |
| `audit_logs` | Audit trail | action, resource_type, details |

### Filter Operators

| Operator | Description | Example |
| -------- | ----------- | ------- |
| `eq` | Equals | `{"field": "status", "value": "active", "operator": "eq"}` |
| `ne` | Not equals | `{"field": "status", "value": "deleted", "operator": "ne"}` |
| `gt` | Greater than | `{"field": "age", "value": 18, "operator": "gt"}` |
| `gte` | Greater or equal | `{"field": "price", "value": 100, "operator": "gte"}` |
| `lt` | Less than | `{"field": "stock", "value": 10, "operator": "lt"}` |
| `lte` | Less or equal | `{"field": "rating", "value": 5, "operator": "lte"}` |
| `in` | In list | `{"field": "category", "value": ["tech", "science"], "operator": "in"}` |
| `contains` | Contains substring | `{"field": "name", "value": "john", "operator": "contains"}` |
| `startswith` | Starts with | `{"field": "code", "value": "PRD-", "operator": "startswith"}` |
| `endswith` | Ends with | `{"field": "email", "value": "@company.com", "operator": "endswith"}` |

## Search Syntax

### Basic Search

```text
hello world
```

Searches for documents containing both "hello" AND "world".

### Phrase Search

```text
"hello world"
```

Searches for the exact phrase "hello world".

### OR Search

```text
hello | goodbye
```

Searches for documents containing "hello" OR "goodbye".

### Exclude Terms

```text
hello -world
```

Searches for "hello" but excludes documents containing "world".

### Prefix Search

```text
intro*
```

Searches for words starting with "intro" (introduction, introducing, etc.).

## PostgreSQL FTS Details

### How It Works

PostgreSQL Full-Text Search uses:

1. **tsvector** - Document representation with weighted terms
2. **tsquery** - Query representation
3. **GIN Index** - Fast lookup with inverted index

### Weighted Search

Fields are assigned weights for relevance ranking:

| Weight | Priority | Example Fields |
| --- | --- | --- |
| A | Highest | title, email |
| B | High | username, content |
| C | Medium | tags, description |
| D | Low | metadata |

### Multi-Language Support

Configure the language for stemming and stop words:

```bash
# English (default)
SEARCH_PG_LANGUAGE=english

# Spanish
SEARCH_PG_LANGUAGE=spanish

# Simple (no stemming)
SEARCH_PG_LANGUAGE=simple
```

Available configurations: `simple`, `arabic`, `danish`, `dutch`, `english`, `finnish`, `french`, `german`, `hungarian`, `indonesian`, `irish`, `italian`, `lithuanian`, `nepali`, `norwegian`, `portuguese`, `romanian`, `russian`, `spanish`, `swedish`, `tamil`, `turkish`.

### Fuzzy Search with Trigrams

Fuzzy matching uses the `pg_trgm` extension for typo tolerance.

```sql
-- Enable extension (done in migration)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Create Search Index

```http
POST /api/v1/search/indices/posts/create
Authorization: Bearer {admin_token}
```

This creates a GIN index for the specified table.

## Elasticsearch Details

### Index Mappings

Each search index has predefined mappings optimized for search:

```json
{
  "settings": {
    "number_of_shards": 2,
    "number_of_replicas": 1,
    "analysis": {
      "analyzer": {
        "content_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "stop", "snowball"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "fields": {
          "keyword": {"type": "keyword"},
          "suggest": {"type": "completion"}
        }
      },
      "content": {
        "type": "text",
        "analyzer": "content_analyzer"
      }
    }
  }
}
```

### Boosting Fields

Customize field importance:

```json
{
  "query": "search terms",
  "index": "posts",
  "boost_fields": {
    "title": 3.0,
    "content": 1.0,
    "tags": 2.0
  }
}
```

### Fuzzy Matching

Configure fuzzy parameters:

```json
{
  "query": "introdution",
  "fuzzy": true,
  "fuzzy_max_edits": 2
}
```

## Frontend Integration

### React Search Component

```tsx
import { useState, useEffect, useCallback } from 'react';
import { debounce } from 'lodash';
import api from '@/services/api';

interface SearchResult {
  id: string;
  score: number;
  source: Record<string, any>;
  highlights: Record<string, string[]>;
}

const SearchComponent = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // Debounced search
  const debouncedSearch = useCallback(
    debounce(async (q: string) => {
      if (!q.trim()) {
        setResults([]);
        return;
      }

      setLoading(true);
      try {
        const response = await api.post('/search', {
          query: q,
          index: 'posts',
          page: 1,
          page_size: 10,
        });
        setResults(response.data.hits);
        setSuggestions(response.data.suggestions);
      } catch (error) {
        console.error('Search error:', error);
      }
      setLoading(false);
    }, 300),
    []
  );

  useEffect(() => {
    debouncedSearch(query);
  }, [query, debouncedSearch]);

  return (
    <div className="search-container">
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
        className="search-input"
      />
      
      {loading && <div className="loading">Searching...</div>}
      
      {suggestions.length > 0 && (
        <div className="suggestions">
          Did you mean: {suggestions.map((s, i) => (
            <button key={i} onClick={() => setQuery(s)}>{s}</button>
          ))}
        </div>
      )}
      
      <div className="results">
        {results.map((result) => (
          <div key={result.id} className="result-item">
            <h3
              dangerouslySetInnerHTML={{
                __html: result.highlights.title?.[0] || result.source.title,
              }}
            />
            <p
              dangerouslySetInnerHTML={{
                __html: result.highlights.content?.[0] || result.source.content?.substring(0, 200),
              }}
            />
            <span className="score">Relevance: {(result.score * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### Autocomplete Hook

```tsx
import { useState, useEffect, useCallback } from 'react';
import { debounce } from 'lodash';
import api from '@/services/api';

export const useAutocomplete = (index: string, field: string = 'title') => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSuggestions = useCallback(
    debounce(async (q: string) => {
      if (q.length < 2) {
        setSuggestions([]);
        return;
      }

      setLoading(true);
      try {
        const response = await api.get('/search/suggest', {
          params: { q, index, field, size: 5 },
        });
        setSuggestions(response.data.suggestions);
      } catch (error) {
        console.error('Autocomplete error:', error);
      }
      setLoading(false);
    }, 150),
    [index, field]
  );

  useEffect(() => {
    fetchSuggestions(query);
  }, [query, fetchSuggestions]);

  return { query, setQuery, suggestions, loading };
};
```

## Performance Tips

### PostgreSQL FTS

1. **Create GIN indexes** on frequently searched tables
2. **Use `ts_headline` sparingly** - it's CPU intensive
3. **Limit result set size** before applying highlights
4. **Consider materialized views** for complex aggregated searches

### Elasticsearch

1. **Tune shard count** based on data volume
2. **Use scroll API** for large result sets
3. **Implement request coalescing** for autocomplete
4. **Configure circuit breakers** to prevent OOM

## Troubleshooting

### "No results found"

- Check if the table has a GIN index (PostgreSQL)
- Verify the index exists (Elasticsearch)
- Try simpler search terms
- Check if documents are properly indexed

### "Search is slow"

- Ensure GIN indexes exist (PostgreSQL)
- Check cluster health (Elasticsearch)
- Reduce result set size
- Disable highlighting for large result sets

### "Trigram extension not available"

```sql
-- Install pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### "Elasticsearch connection refused"

- Check Elasticsearch is running: `curl http://localhost:9200`
- Verify credentials in configuration
- Check firewall/network settings

## Admin Operations

### Create Index

```http
POST /api/v1/search/indices/{index}/create
Authorization: Bearer {admin_token}
```

### Reindex Documents

```http
POST /api/v1/search/indices/{index}/reindex
Authorization: Bearer {admin_token}
```

### Delete Index

```http
DELETE /api/v1/search/indices/{index}
Authorization: Bearer {admin_token}
```

## Extending Search

### Add New Index

1. Define index configuration in `postgres_fts.py` or `elasticsearch.py`:

```python
INDEX_CONFIGS[SearchIndex.PRODUCTS] = {
    "table": "products",
    "id_column": "id",
    "tenant_column": "tenant_id",
    "search_columns": {
        "name": "A",
        "description": "B",
        "sku": "A",
    },
    "highlight_columns": ["name", "description"],
}
```

1. Add enum value:

```python
class SearchIndex(str, Enum):
    # ... existing
    PRODUCTS = "products"
```

1. Create migration with GIN index:

```sql
CREATE INDEX idx_products_fts ON products
USING GIN ((
    setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(sku, '')), 'A')
));
```
