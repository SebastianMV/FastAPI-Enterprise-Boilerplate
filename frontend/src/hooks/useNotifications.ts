/**
 * Notifications hook for real-time and persistent notifications.
 * 
 * **Delegates all state to the Zustand ``useNotificationsStore``** so
 * that a single source of truth is shared by every consumer
 * (``NotificationsDropdown``, ``NotificationsPage``, etc.).
 * 
 * The hook is responsible only for:
 * 1. Connecting WebSocket → pushing events into the store.
 * 2. Initial REST fetch → seeding the store on mount.
 * 3. Exposing convenience methods that wrap API calls + store updates.
 * 
 * @example
 * ```tsx
 * const { notifications, unreadCount, markAsRead } = useNotifications();
 * ```
 */

import { useCallback, useEffect, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { notificationsService } from '../services/notificationsService';
import { validateActionUrl, sanitizeText } from '../utils/security';
import { useNotificationsStore } from '../stores/notificationsStore';
import type { Notification } from '../stores/notificationsStore';

export type { Notification } from '../stores/notificationsStore';

export interface UseNotificationsOptions {
  /** Auto-fetch on mount */
  autoFetch?: boolean;
  /** Limit for initial fetch */
  limit?: number;
  /** Poll interval for unread count (ms, 0 to disable) */
  pollInterval?: number;
}

export interface UseNotificationsReturn {
  /** List of notifications */
  notifications: Notification[];
  /** Unread count */
  unreadCount: number;
  /** Loading state */
  isLoading: boolean;
  /** Error message */
  error: string | null;
  /** WebSocket connected */
  isConnected: boolean;
  /** Fetch notifications */
  fetchNotifications: (options?: { unreadOnly?: boolean; limit?: number }) => Promise<void>;
  /** Mark notification as read */
  markAsRead: (notificationId: string) => Promise<void>;
  /** Mark all as read */
  markAllAsRead: () => Promise<void>;
  /** Delete notification */
  deleteNotification: (notificationId: string) => Promise<void>;
  /** Clear all read notifications */
  clearRead: () => Promise<void>;
}

export function useNotifications(
  options: UseNotificationsOptions = {}
): UseNotificationsReturn {
  const { autoFetch = true, limit = 50, pollInterval = 0 } = options;

  // ── Zustand store (single source of truth) ──
  const notifications = useNotificationsStore((s) => s.notifications);
  const unreadCount = useNotificationsStore((s) => s.unreadCount);
  const isConnected = useNotificationsStore((s) => s.isConnected);
  const storeAdd = useNotificationsStore((s) => s.addNotification);
  const storeSet = useNotificationsStore((s) => s.setNotifications);
  const storeMarkRead = useNotificationsStore((s) => s.markAsRead);
  const storeMarkAllRead = useNotificationsStore((s) => s.markAllAsRead);
  const storeRemove = useNotificationsStore((s) => s.removeNotification);
  const storeSetCount = useNotificationsStore((s) => s.setUnreadCount);

  // ── Local loading / error state (not shared) ──
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── WebSocket → store bridge ──
  const handleNotification = useCallback((payload: Record<string, unknown>) => {
    if (
      typeof payload !== 'object' ||
      payload === null ||
      typeof payload.id !== 'string' ||
      typeof payload.type !== 'string' ||
      typeof payload.title !== 'string' ||
      typeof payload.message !== 'string'
    ) {
      return;
    }

    const notification: Notification = {
      id: payload.id as string,
      type: payload.type as string,
      title: sanitizeText(payload.title as string),
      message: sanitizeText(payload.message as string),
      priority: (['low', 'normal', 'high', 'urgent'].includes(payload.priority as string)
        ? payload.priority
        : 'normal') as Notification['priority'],
      category: typeof payload.category === 'string' ? payload.category : undefined,
      metadata: typeof payload.metadata === 'object' && payload.metadata !== null
        && !Array.isArray(payload.metadata)
        ? payload.metadata as Record<string, unknown>
        : undefined,
      action_url: validateActionUrl(payload.action_url),
      read: typeof payload.read === 'boolean' ? payload.read : false,
      created_at: typeof payload.created_at === 'string' ? payload.created_at : new Date().toISOString(),
    };

    storeAdd(notification);
  }, [storeAdd]);

  // Single WebSocket connection shared via the store's `isConnected`
  useWebSocket({ onNotification: handleNotification });

  // ── REST operations ──
  const fetchNotifications = useCallback(async (opts?: {
    unreadOnly?: boolean;
    limit?: number;
  }) => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await notificationsService.list({
        unread_only: opts?.unreadOnly,
        limit: opts?.limit ?? limit,
      });

      if (Array.isArray(data.items)) {
        storeSet(data.items as Notification[]);
      }
    } catch {
      setError('notifications.fetchError');
    } finally {
      setIsLoading(false);
    }
  }, [limit, storeSet]);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const count = await notificationsService.getUnreadCount();
      storeSetCount(count);
    } catch {
      // Non-critical
    }
  }, [storeSetCount]);

  const markAsRead = useCallback(async (notificationId: string) => {
    try {
      await notificationsService.markAsRead(notificationId);
      storeMarkRead(notificationId);
    } catch {
      setError('notifications.markAsReadError');
    }
  }, [storeMarkRead]);

  const markAllAsRead = useCallback(async () => {
    try {
      await notificationsService.markAllAsRead();
      storeMarkAllRead();
    } catch {
      setError('notifications.markAllAsReadError');
    }
  }, [storeMarkAllRead]);

  const deleteNotification = useCallback(async (notificationId: string) => {
    try {
      await notificationsService.delete(notificationId);
      storeRemove(notificationId);
    } catch {
      setError('notifications.deleteError');
    }
  }, [storeRemove]);

  const clearRead = useCallback(async () => {
    try {
      await notificationsService.list({ unread_only: true });
      // Remove read notifications from store
      const current = useNotificationsStore.getState().notifications;
      const unreadOnly = current.filter((n) => !n.read);
      storeSet(unreadOnly);
    } catch {
      setError('notifications.clearReadError');
    }
  }, [storeSet]);

  // ── Auto-fetch ──
  useEffect(() => {
    if (autoFetch) {
      fetchNotifications();
      fetchUnreadCount();
    }
  }, [autoFetch, fetchNotifications, fetchUnreadCount]);

  // ── Poll unread count ──
  useEffect(() => {
    const safePollInterval = pollInterval > 0 ? Math.max(5000, pollInterval) : 0;
    if (safePollInterval > 0) {
      const interval = setInterval(fetchUnreadCount, safePollInterval);
      return () => clearInterval(interval);
    }
  }, [pollInterval, fetchUnreadCount]);

  return {
    notifications,
    unreadCount,
    isLoading,
    error,
    isConnected,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearRead,
  };
}
