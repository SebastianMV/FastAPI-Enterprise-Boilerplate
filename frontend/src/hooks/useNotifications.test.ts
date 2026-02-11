/**
 * Tests for useNotifications hook.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useNotifications, type Notification } from './useNotifications';

// Mock the useWebSocket hook
vi.mock('./useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: true,
    sendMessage: vi.fn(),
    lastMessage: null,
  })),
}));

// Mock notifications data
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'info',
    title: 'Test Notification',
    message: 'This is a test',
    priority: 'normal',
    is_read: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '2',
    type: 'warning',
    title: 'Warning',
    message: 'This is a warning',
    priority: 'high',
    is_read: true,
    created_at: new Date().toISOString(),
  },
];

// Mock the api module
vi.mock('../services/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: { items: [], total: 0 } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

describe('useNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial state', () => {
    it('should return initial state', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false }));

      expect(result.current.notifications).toEqual([]);
      expect(result.current.unreadCount).toBe(0);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should return isConnected from WebSocket', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false }));

      expect(result.current.isConnected).toBe(true);
    });

    it('should have fetchNotifications function', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false }));

      expect(typeof result.current.fetchNotifications).toBe('function');
    });

    it('should have markAsRead function', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false }));

      expect(typeof result.current.markAsRead).toBe('function');
    });

    it('should have markAllAsRead function', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false }));

      expect(typeof result.current.markAllAsRead).toBe('function');
    });

    it('should have deleteNotification function', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false }));

      expect(typeof result.current.deleteNotification).toBe('function');
    });

    it('should have clearRead function', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false }));

      expect(typeof result.current.clearRead).toBe('function');
    });
  });

  describe('Options', () => {
    it('should accept autoFetch option', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false }));

      // Should not start loading if autoFetch is false
      expect(result.current.isLoading).toBe(false);
    });

    it('should accept limit option', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false, limit: 50 }));

      expect(result.current).toBeDefined();
    });

    it('should accept pollInterval option', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false, pollInterval: 30000 }));

      expect(result.current).toBeDefined();
    });
  });
});
