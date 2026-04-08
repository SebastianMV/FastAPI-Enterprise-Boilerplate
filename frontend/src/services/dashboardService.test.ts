/**
 * Unit tests for dashboardService.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockGet = vi.fn();

vi.mock('./api', () => ({
  default: { get: (...args: unknown[]) => mockGet(...args) },
}));

import { dashboardService } from './dashboardService';

describe('dashboardService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should get stats', async () => {
    const stats = { total_users: 42, active_users: 30, stats: [] };
    mockGet.mockResolvedValueOnce({ data: stats });
    const result = await dashboardService.getStats();
    expect(mockGet).toHaveBeenCalledWith('/dashboard/stats');
    expect(result.total_users).toBe(42);
  });

  it('should get activity with default limit', async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    const result = await dashboardService.getActivity();
    expect(mockGet).toHaveBeenCalledWith('/dashboard/activity', { params: { limit: 10 } });
    expect(result.items).toEqual([]);
  });

  it('should get activity with custom limit', async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0 } });
    await dashboardService.getActivity(25);
    expect(mockGet).toHaveBeenCalledWith('/dashboard/activity', { params: { limit: 25 } });
  });

  it('should get health', async () => {
    const health = { database_status: 'ok', cache_status: 'ok', uptime_percentage: 99.9 };
    mockGet.mockResolvedValueOnce({ data: health });
    const result = await dashboardService.getHealth();
    expect(mockGet).toHaveBeenCalledWith('/dashboard/health-metrics');
    expect(result.uptime_percentage).toBe(99.9);
  });
});
