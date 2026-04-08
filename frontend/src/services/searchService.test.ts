/**
 * Unit tests for searchService.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('./api', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

import { searchService } from './searchService';

describe('searchService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should search with request', async () => {
    const response = { hits: [], total: 0, page: 1, page_size: 10, total_pages: 0, has_next: false, has_previous: false, took_ms: 5, max_score: null, suggestions: [] };
    mockPost.mockResolvedValueOnce({ data: response });
    const result = await searchService.search({ query: 'test', index: 'users' });
    expect(mockPost).toHaveBeenCalledWith('/search', { query: 'test', index: 'users', page: 1, page_size: 20 }, { signal: undefined });
    expect(result.hits).toEqual([]);
  });

  it('should search with filters and sort', async () => {
    const req = {
      query: 'admin',
      index: 'users' as const,
      filters: [{ field: 'is_active', value: true, operator: 'eq' as const }],
      sort: [{ field: 'created_at', order: 'desc' as const }],
      page: 2,
      page_size: 5,
      fuzzy: true,
    };
    mockPost.mockResolvedValueOnce({ data: { hits: [], total: 0 } });
    await searchService.search(req);
    expect(mockPost).toHaveBeenCalledWith('/search', req, { signal: undefined });
  });

  it('should suggest with default index', async () => {
    mockGet.mockResolvedValueOnce({ data: { suggestions: ['admin', 'administrator'] } });
    const result = await searchService.suggest('adm');
    expect(mockGet).toHaveBeenCalledWith('/search/suggest', { params: { query: 'adm', index: 'users' } });
    expect(result).toEqual(['admin', 'administrator']);
  });

  it('should suggest with custom index', async () => {
    mockGet.mockResolvedValueOnce({ data: { suggestions: [] } });
    await searchService.suggest('test', 'audit_logs');
    expect(mockGet).toHaveBeenCalledWith('/search/suggest', { params: { query: 'test', index: 'audit_logs' } });
  });

  it('should quick search', async () => {
    const response = { hits: [{ id: '1', score: 0.9 }], total: 1 };
    mockGet.mockResolvedValueOnce({ data: response });
    const result = await searchService.quickSearch('hello');
    expect(mockGet).toHaveBeenCalledWith('/search/quick', { params: { q: 'hello' } });
    expect(result.total).toBe(1);
  });
});
