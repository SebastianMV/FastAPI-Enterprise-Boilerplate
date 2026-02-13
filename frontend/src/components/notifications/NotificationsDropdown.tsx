/**
 * Notifications dropdown component.
 *
 * Displays a bell icon with unread count badge and dropdown
 * showing recent notifications with real-time updates via WebSocket.
 */

import { useWebSocket } from '@/hooks/useWebSocket';
import { notificationsService } from '@/services/api';
import { useNotificationsStore, type Notification } from '@/stores/notificationsStore';
import { formatRelativeTime } from '@/utils/formatRelativeTime';
import { isSafeRedirectUrl, sanitizeText } from '@/utils/security';
import { AlertCircle, AlertTriangle, Bell, Check, CheckCheck, CheckCircle, Info, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

/**
 * Validate that an action URL is a safe relative path (not an external redirect).
 */
function isSafeActionUrl(url: string): boolean {
  return isSafeRedirectUrl(url);
}

/**
 * Get icon component based on notification type.
 */
function getNotificationIcon(type: Notification['type']) {
  switch (type) {
    case 'success':
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    case 'warning':
      return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
    case 'error':
      return <AlertCircle className="w-5 h-5 text-red-500" />;
    default:
      return <Info className="w-5 h-5 text-blue-500" />;
  }
}

interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onClick?: () => void;
  t: (key: string, options?: Record<string, unknown>) => string;
}

/**
 * Single notification item in the dropdown.
 */
function NotificationItem({ notification, onMarkAsRead, onClick, t }: NotificationItemProps) {
  return (
    <div
      className={`flex items-start gap-3 p-3 border-b border-slate-100 dark:border-slate-700 last:border-0 transition-colors cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 ${
        !notification.read ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''
      }`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      <div className="flex-shrink-0 mt-0.5">
        {getNotificationIcon(notification.type)}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm ${!notification.read ? 'font-medium' : ''} text-slate-900 dark:text-white`}>
          {sanitizeText(notification.title)}
        </p>
        {notification.message && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
            {sanitizeText(notification.message)}
          </p>
        )}
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
          {formatRelativeTime(notification.created_at, {
            justNow: t('notificationsDropdown.justNow'),
            minutesAgo: (count) => t(count === 1 ? 'notificationsDropdown.minuteAgo' : 'notificationsDropdown.minutesAgo', { count }),
            hoursAgo: (count) => t(count === 1 ? 'notificationsDropdown.hourAgo' : 'notificationsDropdown.hoursAgo', { count }),
            daysAgo: (count) => t(count === 1 ? 'notificationsDropdown.dayAgo' : 'notificationsDropdown.daysAgo', { count }),
          })}
        </p>
      </div>
      {!notification.read && (
        <button
          onClick={async (e) => {
            e.stopPropagation();
            try { await notificationsService.markAsRead(notification.id); } catch { /* non-critical */ }
            onMarkAsRead(notification.id);
          }}
          className="flex-shrink-0 p-1 text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 rounded"
          title={t('notificationsDropdown.markAsRead')}
        >
          <Check className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

/**
 * Notifications dropdown with bell icon and unread badge.
 */
export default function NotificationsDropdown() {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const {
    notifications,
    unreadCount,
    isConnected,
    addNotification,
    markAsRead,
    markAllAsRead,
    setConnected,
  } = useNotificationsStore();

  // WebSocket connection for real-time notifications
  useWebSocket({
    autoConnect: true,
    onConnected: () => setConnected(true),
    onDisconnected: () => setConnected(false),
    onNotification: (payload) => {
      // Runtime payload validation (F-03)
      if (typeof payload !== 'object' || payload === null) return;

      // Require server-generated ID — drop payloads without one
      if (typeof payload.id !== 'string' || !payload.id) return;

      const id = payload.id as string;
      // Validate type against allowed enum values
      const VALID_TYPES: Notification['type'][] = ['info', 'success', 'warning', 'error'];
      const type = VALID_TYPES.includes(payload.type as Notification['type'])
        ? (payload.type as Notification['type'])
        : 'info';
      const title = typeof payload.title === 'string' ? sanitizeText(payload.title.slice(0, 200)) : t('notificationsDropdown.defaultTitle');
      const message = typeof payload.message === 'string' ? sanitizeText(payload.message.slice(0, 1000)) : '';
      const created_at = typeof payload.timestamp === 'string' ? payload.timestamp : new Date().toISOString();
      const rawActionUrl = typeof payload.action_url === 'string' ? payload.action_url : undefined;
      const action_url = rawActionUrl && isSafeRedirectUrl(rawActionUrl) ? rawActionUrl : undefined;

      const notification: Notification = {
        id,
        type,
        title,
        message,
        read: false,
        created_at,
        action_url,
      };
      addNotification(notification);
    },
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && event.target instanceof Node && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle notification click
  const handleNotificationClick = useCallback(async (notification: Notification) => {
    if (!notification.read) {
      try { await notificationsService.markAsRead(notification.id); } catch { /* non-critical */ }
      markAsRead(notification.id);
    }
    if (notification.action_url && isSafeActionUrl(notification.action_url)) {
      navigate(notification.action_url);
      setIsOpen(false);
    }
  }, [markAsRead, navigate]);

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        aria-label={t('notificationsDropdown.title')}
        aria-expanded={isOpen}
      >
        <Bell className="w-5 h-5" />

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] text-xs font-medium text-white bg-red-500 rounded-full px-1">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}

        {/* Connection indicator */}
        <span
          className={`absolute bottom-1 right-1 w-2 h-2 rounded-full border border-white dark:border-slate-800 ${
            isConnected ? 'bg-green-500' : 'bg-slate-400'
          }`}
          title={isConnected ? t('notificationsDropdown.connected') : t('notificationsDropdown.disconnected')}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div role="region" aria-live="polite" aria-label={t('notificationsDropdown.title')} className="absolute right-0 mt-2 w-80 max-h-[480px] bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 overflow-hidden z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              {t('notificationsDropdown.title')}
            </h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={async () => { try { await notificationsService.markAllAsRead(); } catch { /* non-critical */ } markAllAsRead(); }}
                  className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 flex items-center gap-1"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  {t('notificationsDropdown.markAllRead')}
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Notifications list */}
          <div className="max-h-[360px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
                <Bell className="w-10 h-10 text-slate-300 dark:text-slate-600 mb-2" />
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {t('notificationsDropdown.noNotifications')}
                </p>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                  {t('notificationsDropdown.emptyDescription')}
                </p>
              </div>
            ) : (
              notifications.slice(0, 20).map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkAsRead={markAsRead}
                  onClick={() => handleNotificationClick(notification)}
                  t={t}
                />
              ))
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="border-t border-slate-200 dark:border-slate-700 px-4 py-2">
              <button
                onClick={() => {
                  navigate('/notifications');
                  setIsOpen(false);
                }}
                className="w-full text-center text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 py-1"
              >
                {t('notificationsDropdown.viewAll')}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
