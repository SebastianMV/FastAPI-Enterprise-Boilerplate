import api from './api';

// Search Types
export interface SearchFilter {
  field: string;
  value: string | number | boolean;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'contains' | 'startswith' | 'endswith';
}

export interface SearchSort {
  field: string;
  order: 'asc' | 'desc';
}

export interface SearchRequest {
  query: string;
  index: 'users' | 'posts' | 'messages' | 'documents' | 'audit_logs';
  filters?: SearchFilter[];
  sort?: SearchSort[];
  highlight_fields?: string[];
  page?: number;
  page_size?: number;
  fuzzy?: boolean;
}

export interface SearchHit {
  id: string;
  score: number;
  source: Record<string, unknown>;
  highlights: Record<string, string[]>;
  matched_fields: string[];
}

export interface SearchResponse {
  hits: SearchHit[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  took_ms: number;
  max_score: number | null;
  suggestions: string[];
}

export interface SearchSuggestion {
  suggestions: string[];
}

export const searchService = {
  search: async (request: SearchRequest, signal?: AbortSignal): Promise<SearchResponse> => {
    const response = await api.post<SearchResponse>('/search', request, { signal });
    return response.data;
  },

  suggest: async (
    query: string,
    index: string = 'users'
  ): Promise<string[]> => {
    const response = await api.get<SearchSuggestion>('/search/suggest', {
      params: { query, index },
    });
    return response.data.suggestions;
  },

  quickSearch: async (query: string, signal?: AbortSignal): Promise<SearchResponse> => {
    const response = await api.get<SearchResponse>('/search/quick', {
      params: { q: query },
      signal,
    });
    return response.data;
  },
};
