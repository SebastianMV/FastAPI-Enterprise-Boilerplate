/**
 * Unit tests for sessionsService.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockGet = vi.fn();
const mockDelete = vi.fn();

vi.mock('./api', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

import { sessionsService } from './sessionsService';

describe('sessionsService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should list sessions', async () => {
    const data = { sessions: [{ id: 's1', device_name: 'Chrome' }], total: 1 };
    mockGet.mockResolvedValueOnce({ data });
    const result = await sessionsService.list();
    expect(mockGet).toHaveBeenCalledWith('/sessions');
    expect(result.sessions).toHaveLength(1);
  });

  it('should revoke a session', async () => {
    mockDelete.mockResolvedValueOnce({ data: { message: 'Revoked', revoked_count: 1 } });
    const result = await sessionsService.revoke('s1');
    expect(mockDelete).toHaveBeenCalledWith('/sessions/s1');
    expect(result.revoked_count).toBe(1);
  });

  it('should revoke all sessions', async () => {
    mockDelete.mockResolvedValueOnce({ data: { message: 'All revoked', revoked_count: 5 } });
    const result = await sessionsService.revokeAll();
    expect(mockDelete).toHaveBeenCalledWith('/sessions');
    expect(result.revoked_count).toBe(5);
  });
});
