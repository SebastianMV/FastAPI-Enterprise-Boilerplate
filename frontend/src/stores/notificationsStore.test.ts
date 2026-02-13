/**
 * Tests for notificationsStore.
 */
import type { Notification } from '@/services/api';
import { act } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { useNotificationsStore } from './notificationsStore';

const createMockNotification = (overrides: Partial<Notification> = {}): Notification => ({
  id: `notification-${Math.random().toString(36).substr(2, 9)}`,
  type: 'info',
  title: 'Test Notification',
  message: 'This is a test notification',
  read: false,
  created_at: new Date().toISOString(),
  ...overrides,
});

describe('notificationsStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    act(() => {
      useNotificationsStore.setState({
        notifications: [],
        unreadCount: 0,
        isConnected: false,
      });
    });
  });

  describe('initial state', () => {
    it('should have empty notifications array', () => {
      const state = useNotificationsStore.getState();
      expect(state.notifications).toEqual([]);
    });

    it('should have unreadCount of 0', () => {
      const state = useNotificationsStore.getState();
      expect(state.unreadCount).toBe(0);
    });

    it('should not be connected initially', () => {
      const state = useNotificationsStore.getState();
      expect(state.isConnected).toBe(false);
    });
  });

  describe('setNotifications', () => {
    it('should set notifications array', () => {
      const notifications = [
        createMockNotification({ id: '1' }),
        createMockNotification({ id: '2' }),
      ];

      act(() => {
        useNotificationsStore.getState().setNotifications(notifications);
      });

      expect(useNotificationsStore.getState().notifications).toEqual(notifications);
    });

    it('should replace existing notifications', () => {
      const initial = [createMockNotification({ id: 'old' })];
      const replacement = [createMockNotification({ id: 'new' })];

      act(() => {
        useNotificationsStore.setState({ notifications: initial });
      });

      act(() => {
        useNotificationsStore.getState().setNotifications(replacement);
      });

      expect(useNotificationsStore.getState().notifications).toEqual(replacement);
    });
  });

  describe('addNotification', () => {
    it('should add notification to the beginning of the list', () => {
      const existing = createMockNotification({ id: '1', title: 'First' });
      const newNotification = createMockNotification({ id: '2', title: 'Second' });

      act(() => {
        useNotificationsStore.setState({ notifications: [existing] });
      });

      act(() => {
        useNotificationsStore.getState().addNotification(newNotification);
      });

      const notifications = useNotificationsStore.getState().notifications;
      expect(notifications[0].id).toBe('2');
      expect(notifications[1].id).toBe('1');
    });

    it('should increment unreadCount for unread notifications', () => {
      const notification = createMockNotification({ read: false });

      act(() => {
        useNotificationsStore.getState().addNotification(notification);
      });

      expect(useNotificationsStore.getState().unreadCount).toBe(1);
    });

    it('should not increment unreadCount for read notifications', () => {
      const notification = createMockNotification({ read: true });

      act(() => {
        useNotificationsStore.getState().addNotification(notification);
      });

      expect(useNotificationsStore.getState().unreadCount).toBe(0);
    });

    it('should limit notifications to 50', () => {
      // Add 50 notifications
      act(() => {
        for (let i = 0; i < 50; i++) {
          useNotificationsStore.getState().addNotification(
            createMockNotification({ id: `notification-${i}`, read: true })
          );
        }
      });

      // Add one more
      act(() => {
        useNotificationsStore.getState().addNotification(
          createMockNotification({ id: 'notification-51', read: true })
        );
      });

      expect(useNotificationsStore.getState().notifications).toHaveLength(50);
      expect(useNotificationsStore.getState().notifications[0].id).toBe('notification-51');
    });
  });

  describe('removeNotification', () => {
    it('should remove notification by id', () => {
      const notifications = [
        createMockNotification({ id: '1' }),
        createMockNotification({ id: '2' }),
        createMockNotification({ id: '3' }),
      ];

      act(() => {
        useNotificationsStore.setState({ notifications });
      });

      act(() => {
        useNotificationsStore.getState().removeNotification('2');
      });

      const result = useNotificationsStore.getState().notifications;
      expect(result).toHaveLength(2);
      expect(result.find((n) => n.id === '2')).toBeUndefined();
    });

    it('should decrement unreadCount when removing unread notification', () => {
      const notification = createMockNotification({ id: '1', read: false });

      act(() => {
        useNotificationsStore.setState({ notifications: [notification], unreadCount: 1 });
      });

      act(() => {
        useNotificationsStore.getState().removeNotification('1');
      });

      expect(useNotificationsStore.getState().unreadCount).toBe(0);
    });

    it('should not decrement unreadCount when removing read notification', () => {
      const notification = createMockNotification({ id: '1', read: true });

      act(() => {
        useNotificationsStore.setState({ notifications: [notification], unreadCount: 1 });
      });

      act(() => {
        useNotificationsStore.getState().removeNotification('1');
      });

      expect(useNotificationsStore.getState().unreadCount).toBe(1);
    });

    it('should not go below 0 for unreadCount', () => {
      const notification = createMockNotification({ id: '1', read: false });

      act(() => {
        useNotificationsStore.setState({ notifications: [notification], unreadCount: 0 });
      });

      act(() => {
        useNotificationsStore.getState().removeNotification('1');
      });

      expect(useNotificationsStore.getState().unreadCount).toBe(0);
    });
  });

  describe('markAsRead', () => {
    it('should mark notification as read', () => {
      const notification = createMockNotification({ id: '1', read: false });

      act(() => {
        useNotificationsStore.setState({ notifications: [notification], unreadCount: 1 });
      });

      act(() => {
        useNotificationsStore.getState().markAsRead('1');
      });

      expect(useNotificationsStore.getState().notifications[0].read).toBe(true);
    });

    it('should decrement unreadCount', () => {
      const notification = createMockNotification({ id: '1', read: false });

      act(() => {
        useNotificationsStore.setState({ notifications: [notification], unreadCount: 1 });
      });

      act(() => {
        useNotificationsStore.getState().markAsRead('1');
      });

      expect(useNotificationsStore.getState().unreadCount).toBe(0);
    });

    it('should not affect already read notifications', () => {
      const notification = createMockNotification({ id: '1', read: true });

      act(() => {
        useNotificationsStore.setState({ notifications: [notification], unreadCount: 5 });
      });

      act(() => {
        useNotificationsStore.getState().markAsRead('1');
      });

      expect(useNotificationsStore.getState().unreadCount).toBe(5);
    });
  });

  describe('markAllAsRead', () => {
    it('should mark all notifications as read', () => {
      const notifications = [
        createMockNotification({ id: '1', read: false }),
        createMockNotification({ id: '2', read: false }),
        createMockNotification({ id: '3', read: true }),
      ];

      act(() => {
        useNotificationsStore.setState({ notifications, unreadCount: 2 });
      });

      act(() => {
        useNotificationsStore.getState().markAllAsRead();
      });

      const result = useNotificationsStore.getState().notifications;
      expect(result.every((n) => n.read)).toBe(true);
    });

    it('should reset unreadCount to 0', () => {
      const notifications = [
        createMockNotification({ id: '1', read: false }),
        createMockNotification({ id: '2', read: false }),
      ];

      act(() => {
        useNotificationsStore.setState({ notifications, unreadCount: 2 });
      });

      act(() => {
        useNotificationsStore.getState().markAllAsRead();
      });

      expect(useNotificationsStore.getState().unreadCount).toBe(0);
    });
  });

  describe('setUnreadCount', () => {
    it('should set unreadCount', () => {
      act(() => {
        useNotificationsStore.getState().setUnreadCount(10);
      });

      expect(useNotificationsStore.getState().unreadCount).toBe(10);
    });
  });

  describe('setConnected', () => {
    it('should set isConnected to true', () => {
      act(() => {
        useNotificationsStore.getState().setConnected(true);
      });

      expect(useNotificationsStore.getState().isConnected).toBe(true);
    });

    it('should set isConnected to false', () => {
      act(() => {
        useNotificationsStore.setState({ isConnected: true });
      });

      act(() => {
        useNotificationsStore.getState().setConnected(false);
      });

      expect(useNotificationsStore.getState().isConnected).toBe(false);
    });
  });

  describe('clearNotifications', () => {
    it('should clear all notifications', () => {
      const notifications = [
        createMockNotification({ id: '1' }),
        createMockNotification({ id: '2' }),
      ];

      act(() => {
        useNotificationsStore.setState({ notifications, unreadCount: 2 });
      });

      act(() => {
        useNotificationsStore.getState().clearNotifications();
      });

      expect(useNotificationsStore.getState().notifications).toEqual([]);
      expect(useNotificationsStore.getState().unreadCount).toBe(0);
    });
  });
});
