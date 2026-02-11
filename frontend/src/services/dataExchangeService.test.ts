/**
 * Unit tests for dataExchangeService.
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

import { dataExchangeService } from './dataExchangeService';

describe('dataExchangeService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should list entities', async () => {
    mockGet.mockResolvedValueOnce({ data: [{ name: 'users', exportable: true }] });
    const result = await dataExchangeService.listEntities();
    expect(mockGet).toHaveBeenCalledWith('/data/entities');
    expect(result).toHaveLength(1);
  });

  it('should get entity', async () => {
    const entity = { name: 'users', display_name: 'Users', fields: [] };
    mockGet.mockResolvedValueOnce({ data: entity });
    const result = await dataExchangeService.getEntity('users');
    expect(mockGet).toHaveBeenCalledWith('/data/entities/users');
    expect(result.name).toBe('users');
  });

  it('should preview export', async () => {
    mockGet.mockResolvedValueOnce({ data: { rows: [], total_count: 0 } });
    const result = await dataExchangeService.previewExport('users', 5);
    expect(mockGet).toHaveBeenCalledWith('/data/export/users/preview', { params: { limit: 5 } });
    expect(result.total_count).toBe(0);
  });

  it('should preview export with default limit', async () => {
    mockGet.mockResolvedValueOnce({ data: { rows: [], total_count: 0 } });
    await dataExchangeService.previewExport('users');
    expect(mockGet).toHaveBeenCalledWith('/data/export/users/preview', { params: { limit: 10 } });
  });

  it('should export data as CSV', async () => {
    const blob = new Blob(['data'], { type: 'text/csv' });
    mockGet.mockResolvedValueOnce({ data: blob });
    const result = await dataExchangeService.exportData('users', 'csv');
    expect(mockGet).toHaveBeenCalledWith('/data/export/users', {
      params: { format: 'csv', columns: undefined },
      responseType: 'blob',
    });
    expect(result).toBeInstanceOf(Blob);
  });

  it('should export data with specific columns', async () => {
    mockGet.mockResolvedValueOnce({ data: new Blob() });
    await dataExchangeService.exportData('users', 'excel', ['email', 'name']);
    expect(mockGet).toHaveBeenCalledWith('/data/export/users', {
      params: { format: 'excel', columns: 'email,name' },
      responseType: 'blob',
    });
  });

  it('should download template', async () => {
    mockGet.mockResolvedValueOnce({ data: new Blob() });
    await dataExchangeService.downloadTemplate('users', 'csv');
    expect(mockGet).toHaveBeenCalledWith('/data/import/users/template', {
      params: { format: 'csv' },
      responseType: 'blob',
    });
  });

  it('should validate import', async () => {
    const file = new File(['data'], 'users.csv', { type: 'text/csv' });
    mockPost.mockResolvedValueOnce({ data: { total_rows: 5, inserted: 0, dry_run: true, success: true } });
    const result = await dataExchangeService.validateImport('users', file);
    expect(mockPost).toHaveBeenCalledWith('/data/import/users?dry_run=true', expect.any(FormData), {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    expect(result.dry_run).toBe(true);
  });

  it('should import data', async () => {
    const file = new File(['data'], 'users.csv');
    mockPost.mockResolvedValueOnce({ data: { total_rows: 10, inserted: 10, success: true } });
    const result = await dataExchangeService.importData('users', file, 'upsert');
    expect(mockPost).toHaveBeenCalledWith('/data/import/users?mode=upsert&dry_run=false', expect.any(FormData), {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    expect(result.inserted).toBe(10);
  });

  it('should import data with default mode', async () => {
    const file = new File(['data'], 'users.csv');
    mockPost.mockResolvedValueOnce({ data: { total_rows: 1, inserted: 1, success: true } });
    await dataExchangeService.importData('users', file);
    expect(mockPost).toHaveBeenCalledWith('/data/import/users?mode=upsert&dry_run=false', expect.any(FormData), {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  });

  it('should generate report', async () => {
    mockPost.mockResolvedValueOnce({ data: new Blob(['pdf']) });
    const result = await dataExchangeService.generateReport('users', { format: 'pdf', include_summary: true });
    expect(mockPost).toHaveBeenCalledWith('/data/reports/users', { format: 'pdf', include_summary: true }, { responseType: 'blob' });
    expect(result).toBeInstanceOf(Blob);
  });

  it('should generate report with defaults', async () => {
    mockPost.mockResolvedValueOnce({ data: new Blob() });
    await dataExchangeService.generateReport('users');
    expect(mockPost).toHaveBeenCalledWith('/data/reports/users', {}, { responseType: 'blob' });
  });

  it('should get report summary', async () => {
    const summary = { total_records: 42, grouped_counts: { admin: 5, user: 37 } };
    mockPost.mockResolvedValueOnce({ data: summary });
    const filters = [{ field: 'is_active', operator: 'eq', value: true }];
    const result = await dataExchangeService.getReportSummary('users', filters);
    expect(mockPost).toHaveBeenCalledWith('/data/reports/users/summary', { filters });
    expect(result.total_records).toBe(42);
  });

  it('should get report summary without filters', async () => {
    mockPost.mockResolvedValueOnce({ data: { total_records: 0, grouped_counts: {} } });
    await dataExchangeService.getReportSummary('users');
    expect(mockPost).toHaveBeenCalledWith('/data/reports/users/summary', { filters: undefined });
  });
});
