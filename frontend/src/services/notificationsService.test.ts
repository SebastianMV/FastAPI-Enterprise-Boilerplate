/**
 * Unit tests for notificationsService.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('./api', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

import { notificationsService } from './notificationsService';

describe('notificationsService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should list notifications', async () => {
    const data = { items: [], total: 0, unread_count: 0 };
    mockGet.mockResolvedValueOnce({ data });
    const result = await notificationsService.list({ skip: 0, limit: 10, unread_only: false });
    expect(mockGet).toHaveBeenCalledWith('/notifications', { params: { skip: 0, limit: 10, unread_only: false } });
    expect(result.total).toBe(0);
  });

  it('should list without params', async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0, unread_count: 0 } });
    await notificationsService.list();
    expect(mockGet).toHaveBeenCalledWith('/notifications', { params: undefined });
  });

  it('should getAll notifications', async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [], total: 0, unread_count: 0 } });
    await notificationsService.getAll({ page: 1, page_size: 20, unread_only: true });
    expect(mockGet).toHaveBeenCalledWith('/notifications', { params: { page: 1, page_size: 20, unread_only: true } });
  });

  it('should mark as read', async () => {
    mockPatch.mockResolvedValueOnce({ data: undefined });
    await notificationsService.markAsRead('n1');
    expect(mockPatch).toHaveBeenCalledWith('/notifications/n1/read');
  });

  it('should mark all as read', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined });
    await notificationsService.markAllAsRead();
    expect(mockPost).toHaveBeenCalledWith('/notifications/mark-all-read');
  });

  it('should delete a notification', async () => {
    mockDelete.mockResolvedValueOnce({ data: undefined });
    await notificationsService.delete('n1');
    expect(mockDelete).toHaveBeenCalledWith('/notifications/n1');
  });

  it('should get unread count', async () => {
    mockGet.mockResolvedValueOnce({ data: { count: 7 } });
    const result = await notificationsService.getUnreadCount();
    expect(mockGet).toHaveBeenCalledWith('/notifications/unread-count');
    expect(result).toBe(7);
  });
});
