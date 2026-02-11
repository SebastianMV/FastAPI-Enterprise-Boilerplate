import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Notification } from '@/services/api';

// Re-export Notification type for convenience
export type { Notification } from '@/services/api';

interface NotificationsState {
  notifications: Notification[];
  unreadCount: number;
  isConnected: boolean;
  
  // Actions
  setNotifications: (notifications: Notification[]) => void;
  addNotification: (notification: Notification) => void;
  removeNotification: (id: string) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  setUnreadCount: (count: number) => void;
  setConnected: (connected: boolean) => void;
  clearNotifications: () => void;
}

/**
 * Zustand store for notifications state.
 * 
 * Persists unread count to localStorage.
 */
export const useNotificationsStore = create<NotificationsState>()(
  persist(
    (set, _get) => ({
      notifications: [],
      unreadCount: 0,
      isConnected: false,

      setNotifications: (notifications) => {
        set({ notifications });
      },

      addNotification: (notification) => {
        set((state) => {
          // F-04: Dedup by ID to prevent duplicate notifications from WebSocket replays
          if (state.notifications.some((n) => n.id === notification.id)) {
            return state;
          }
          return {
            notifications: [notification, ...state.notifications].slice(0, 50),
            unreadCount: state.unreadCount + (notification.read ? 0 : 1),
          };
        });
      },

      removeNotification: (id) => {
        set((state) => {
          const notification = state.notifications.find((n) => n.id === id);
          const wasUnread = notification && !notification.read;
          return {
            notifications: state.notifications.filter((n) => n.id !== id),
            unreadCount: wasUnread ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
          };
        });
      },

      markAsRead: (id) => {
        set((state) => {
          const notification = state.notifications.find((n) => n.id === id);
          if (notification && !notification.read) {
            return {
              notifications: state.notifications.map((n) =>
                n.id === id ? { ...n, read: true } : n
              ),
              unreadCount: Math.max(0, state.unreadCount - 1),
            };
          }
          return state;
        });
      },

      markAllAsRead: () => {
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, read: true })),
          unreadCount: 0,
        }));
      },

      setUnreadCount: (count) => {
        set({ unreadCount: count });
      },

      setConnected: (connected) => {
        set({ isConnected: connected });
      },

      clearNotifications: () => {
        set({ notifications: [], unreadCount: 0 });
      },
    }),
    {
      name: 'notifications-storage',
      partialize: (state) => ({ unreadCount: state.unreadCount }),
    }
  )
);
