/**
 * Notifications page component.
 * 
 * Displays full history of notifications with filtering and pagination.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
  Bell, 
  Check, 
  CheckCheck, 
  Trash2, 
  Filter,
  Info, 
  AlertTriangle, 
  AlertCircle, 
  CheckCircle,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { useNotificationsStore, type Notification } from '@/stores/notificationsStore';
import { notificationsService } from '@/services/api';
import { formatRelativeTime as formatRelativeTimeShared } from '@/utils/formatRelativeTime';

type FilterType = 'all' | 'unread' | 'read';

/**
 * Format a timestamp as relative time.
 */
function formatRelativeTime(timestamp: string, t: (key: string, options?: Record<string, unknown>) => string): string {
  return formatRelativeTimeShared(timestamp, {
    justNow: t('notifications.timeAgo.justNow'),
    minutesAgo: (count: number) => t('notifications.timeAgo.minutesAgo', { count }),
    hoursAgo: (count: number) => t('notifications.timeAgo.hoursAgo', { count }),
    daysAgo: (count: number) => t('notifications.timeAgo.daysAgo', { count }),
  });
}

/**
 * Get icon for notification type.
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

/**
 * Validate that an action URL is a safe relative path (not an external redirect).
 */
function isSafeActionUrl(url: string): boolean {
  // Only allow relative paths starting with /
  if (!url.startsWith('/')) return false;
  // Block protocol-relative URLs (//evil.com)
  if (url.startsWith('//')) return false;
  // Block URLs with protocol schemes
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(url)) return false;
  return true;
}

/**
 * Notifications page with full history.
 */
export default function NotificationsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [filter, setFilter] = useState<FilterType>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    removeNotification,
    setNotifications,
  } = useNotificationsStore();

  // Fetch notifications from API
  const fetchNotifications = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await notificationsService.getAll({ page: 1, page_size: 100 });
      setNotifications(response.items);
    } catch {
      // Fetch failed — non-critical
    } finally {
      setIsLoading(false);
    }
  }, [setNotifications]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // Filter notifications
  const filteredNotifications = notifications.filter((n) => {
    if (filter === 'unread') return !n.read;
    if (filter === 'read') return n.read;
    return true;
  });

  // Paginate
  const paginatedNotifications = filteredNotifications.slice(
    (page - 1) * pageSize,
    page * pageSize
  );
  const totalPages = Math.ceil(filteredNotifications.length / pageSize);

  const handleNotificationClick = async (notification: Notification) => {
    if (!notification.read) {
      // Sync to backend so read state persists across sessions/devices
      try {
        await notificationsService.markAsRead(notification.id);
      } catch {
        // API call failed — still mark locally
      }
      markAsRead(notification.id);
    }
    if (notification.action_url && isSafeActionUrl(notification.action_url)) {
      navigate(notification.action_url);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationsService.delete(id);
      removeNotification(id);
    } catch {
      // Delete failed — non-critical
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsService.markAllAsRead();
      markAllAsRead();
    } catch {
      // API call failed but still mark locally
      markAllAsRead();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {t('notifications.title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {unreadCount > 0 
              ? t(unreadCount === 1 ? 'notifications.unreadCount' : 'notifications.unreadCount_plural', { count: unreadCount })
              : t('notifications.allCaughtUp')
            }
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchNotifications}
            disabled={isLoading}
            className="btn-secondary"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            {t('notifications.refresh')}
          </button>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="btn-primary"
            >
              <CheckCheck className="w-4 h-4 mr-2" />
              {t('notifications.markAllRead')}
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2">
        <Filter className="w-4 h-4 text-slate-500" />
        <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
          {(['all', 'unread', 'read'] as FilterType[]).map((f) => (
            <button
              key={f}
              onClick={() => { setFilter(f); setPage(1); }}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                filter === f
                  ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {t(`notifications.${f}`)}
              {f === 'unread' && unreadCount > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-red-500 text-white rounded-full">
                  {unreadCount}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Notifications List */}
      <div className="card overflow-hidden">
        {isLoading && notifications.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
          </div>
        ) : paginatedNotifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Bell className="w-12 h-12 text-slate-300 dark:text-slate-600 mb-3" />
            <h3 className="text-lg font-medium text-slate-900 dark:text-white">
              {t('notifications.noNotifications')}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {filter === 'unread' 
                ? t('notifications.noUnread') 
                : filter === 'read'
                ? t('notifications.noRead')
                : t('notifications.noNotificationsYet')
              }
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-200 dark:divide-slate-700">
            {paginatedNotifications.map((notification) => (
              <div
                key={notification.id}
                role="button"
                tabIndex={0}
                onClick={() => handleNotificationClick(notification)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleNotificationClick(notification); } }}
                className={`flex items-start gap-4 p-4 cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50 ${
                  !notification.read ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''
                }`}
              >
                <div className="flex-shrink-0 mt-0.5">
                  {getNotificationIcon(notification.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className={`text-sm ${!notification.read ? 'font-medium' : ''} text-slate-900 dark:text-white`}>
                      {notification.title}
                    </p>
                    <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                      {formatRelativeTime(notification.created_at, t)}
                    </span>
                  </div>
                  {notification.message && (
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                      {notification.message}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {!notification.read && (
                    <button
                      onClick={async (e) => { e.stopPropagation(); try { await notificationsService.markAsRead(notification.id); } catch { /* non-critical */ } markAsRead(notification.id); }}
                      className="p-1.5 text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 rounded transition-colors"
                      title={t('notificationsDropdown.markAsRead')}
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={(e) => handleDelete(notification.id, e)}
                    className="p-1.5 text-slate-400 hover:text-red-600 dark:hover:text-red-400 rounded transition-colors"
                    title={t('common.delete')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-700">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t('notifications.showingRange', { from: (page - 1) * pageSize + 1, to: Math.min(page * pageSize, filteredNotifications.length), total: filteredNotifications.length })}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                {t('notifications.previous')}
              </button>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                {t('notifications.pageOf', { current: page, total: totalPages })}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages}
                className="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                {t('notifications.next')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
