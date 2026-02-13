/**
 * Tests for useNotifications hook.
 */
import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNotifications } from './useNotifications';

// Mock the useWebSocket hook
vi.mock('./useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: true,
    sendMessage: vi.fn(),
    lastMessage: null,
  })),
}));

// Mock the notifications store — isConnected now comes from the Zustand store
vi.mock('@/stores/notificationsStore', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock store selector
    useNotificationsStore: (selector: (s: any) => any) =>
      selector({
        notifications: [],
        unreadCount: 0,
        isConnected: false,
        addNotification: vi.fn(),
        setNotifications: vi.fn(),
        markAsRead: vi.fn(),
        markAllAsRead: vi.fn(),
        removeNotification: vi.fn(),
        setUnreadCount: vi.fn(),
      }),
  };
});



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

    it('should return isConnected from store', () => {
      const { result } = renderHook(() => useNotifications({ autoFetch: false }));

      expect(result.current.isConnected).toBe(false);
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
