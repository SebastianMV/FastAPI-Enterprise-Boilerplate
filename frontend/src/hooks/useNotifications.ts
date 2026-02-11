/**
 * Notifications hook for real-time and persistent notifications.
 * 
 * Combines WebSocket for real-time delivery with REST API for
 * persistence and history.
 * 
 * @example
 * ```tsx
 * const { notifications, unreadCount, markAsRead } = useNotifications();
 * ```
 */

import { useCallback, useEffect, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { notificationsService } from '../services/notificationsService';

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  category?: string;
  metadata?: Record<string, unknown>;
  action_url?: string;
  read: boolean;
  created_at: string;
}

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
  
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Handle real-time notifications
  const handleNotification = useCallback((payload: Record<string, unknown>) => {
    // Runtime validation: ensure payload has required Notification fields
    if (
      typeof payload !== 'object' ||
      payload === null ||
      typeof payload.id !== 'string' ||
      typeof payload.type !== 'string' ||
      typeof payload.title !== 'string' ||
      typeof payload.message !== 'string'
    ) {
      return; // Silently drop malformed payloads
    }

    const notification: Notification = {
      id: payload.id as string,
      type: payload.type as string,
      title: payload.title as string,
      message: payload.message as string,
      priority: (['low', 'normal', 'high', 'urgent'].includes(payload.priority as string)
        ? payload.priority
        : 'normal') as Notification['priority'],
      category: typeof payload.category === 'string' ? payload.category : undefined,
      metadata: typeof payload.metadata === 'object' && payload.metadata !== null
        ? payload.metadata as Record<string, unknown>
        : undefined,
      action_url: typeof payload.action_url === 'string' ? payload.action_url : undefined,
      read: typeof payload.read === 'boolean' ? payload.read : false,
      created_at: typeof payload.created_at === 'string' ? payload.created_at : new Date().toISOString(),
    };
    
    // Add to beginning of list
    setNotifications((prev) => [notification, ...prev]);
    
    // Increment unread count
    if (!notification.read) {
      setUnreadCount((prev) => prev + 1);
    }
  }, []);
  
  // WebSocket connection
  const { isConnected } = useWebSocket({
    onNotification: handleNotification,
  });
  
  // Fetch notifications from API
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
      
      setNotifications(data.items as Notification[]);
    } catch (err) {
      setError('notifications.fetchError');
    } finally {
      setIsLoading(false);
    }
  }, [limit]);
  
  // Fetch unread count
  const fetchUnreadCount = useCallback(async () => {
    try {
      const count = await notificationsService.getUnreadCount();
      setUnreadCount(count);
    } catch {
      // Unread count fetch failed — non-critical
    }
  }, []);
  
  // Mark as read
  const markAsRead = useCallback(async (notificationId: string) => {
    try {
      await notificationsService.markAsRead(notificationId);
      
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === notificationId ? { ...n, read: true } : n
        )
      );
      
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Mark as read failed — non-critical
    }
  }, []);
  
  // Mark all as read
  const markAllAsRead = useCallback(async () => {
    try {
      await notificationsService.markAllAsRead();
      
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, read: true }))
      );
      
      setUnreadCount(0);
    } catch {
      // Mark all as read failed — non-critical
    }
  }, []);
  
  // Delete notification
  const deleteNotification = useCallback(async (notificationId: string) => {
    try {
      await notificationsService.delete(notificationId);
      
      setNotifications((prev) => {
        const notification = prev.find((n) => n.id === notificationId);
        if (notification && !notification.read) {
          setUnreadCount((count) => Math.max(0, count - 1));
        }
        return prev.filter((n) => n.id !== notificationId);
      });
    } catch {
      // Delete notification failed — non-critical
    }
  }, []);
  
  // Clear all read notifications
  const clearRead = useCallback(async () => {
    try {
      // Clear read: no dedicated service method; use raw list re-fetch
      await notificationsService.list({ unread_only: true });
      
      setNotifications((prev) => prev.filter((n) => !n.read));
    } catch {
      // Clear read failed — non-critical
    }
  }, []);
  
  // Auto-fetch on mount
  useEffect(() => {
    if (autoFetch) {
      fetchNotifications();
      fetchUnreadCount();
    }
  }, [autoFetch, fetchNotifications, fetchUnreadCount]);
  
  // Poll for unread count
  useEffect(() => {
    if (pollInterval > 0) {
      const interval = setInterval(fetchUnreadCount, pollInterval);
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
