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
import api from '../services/api';

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  category?: string;
  metadata?: Record<string, unknown>;
  action_url?: string;
  is_read: boolean;
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
    const notification = payload as unknown as Notification;
    
    // Add to beginning of list
    setNotifications((prev) => [notification, ...prev]);
    
    // Increment unread count
    if (!notification.is_read) {
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
      const params = new URLSearchParams();
      if (opts?.unreadOnly) params.append('unread_only', 'true');
      params.append('limit', String(opts?.limit ?? limit));
      
      const response = await api.get<{ items: Notification[]; total: number }>(
        `/api/v1/notifications?${params}`
      );
      
      setNotifications(response.data.items);
    } catch (err) {
      setError('Failed to fetch notifications');
      console.error('Error fetching notifications:', err);
    } finally {
      setIsLoading(false);
    }
  }, [limit]);
  
  // Fetch unread count
  const fetchUnreadCount = useCallback(async () => {
    try {
      const response = await api.get<{ count: number }>(
        '/api/v1/notifications/unread-count'
      );
      setUnreadCount(response.data.count);
    } catch (err) {
      console.error('Error fetching unread count:', err);
    }
  }, []);
  
  // Mark as read
  const markAsRead = useCallback(async (notificationId: string) => {
    try {
      await api.post(`/api/v1/notifications/${notificationId}/read`);
      
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === notificationId ? { ...n, is_read: true } : n
        )
      );
      
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Error marking notification as read:', err);
    }
  }, []);
  
  // Mark all as read
  const markAllAsRead = useCallback(async () => {
    try {
      await api.post('/api/v1/notifications/read-all');
      
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, is_read: true }))
      );
      
      setUnreadCount(0);
    } catch (err) {
      console.error('Error marking all as read:', err);
    }
  }, []);
  
  // Delete notification
  const deleteNotification = useCallback(async (notificationId: string) => {
    try {
      await api.delete(`/api/v1/notifications/${notificationId}`);
      
      setNotifications((prev) => {
        const notification = prev.find((n) => n.id === notificationId);
        if (notification && !notification.is_read) {
          setUnreadCount((count) => Math.max(0, count - 1));
        }
        return prev.filter((n) => n.id !== notificationId);
      });
    } catch (err) {
      console.error('Error deleting notification:', err);
    }
  }, []);
  
  // Clear all read notifications
  const clearRead = useCallback(async () => {
    try {
      await api.delete('/api/v1/notifications/read');
      
      setNotifications((prev) => prev.filter((n) => !n.is_read));
    } catch (err) {
      console.error('Error clearing read notifications:', err);
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
