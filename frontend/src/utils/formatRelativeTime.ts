/**
 * Shared formatRelativeTime utility.
 *
 * Each call-site provides its own i18n keys via the `keys` parameter,
 * so every component can keep its existing translation namespace.
 *
 * @example
 * formatRelativeTime(timestamp, {
 *   justNow: t('notifications.timeAgo.justNow'),
 *   minutesAgo: (count) => t('notifications.timeAgo.minutesAgo', { count }),
 *   hoursAgo:   (count) => t('notifications.timeAgo.hoursAgo', { count }),
 *   daysAgo:    (count) => t('notifications.timeAgo.daysAgo', { count }),
 * });
 */

export interface RelativeTimeKeys {
  justNow: string;
  minutesAgo: (count: number) => string;
  hoursAgo: (count: number) => string;
  daysAgo: (count: number) => string;
}

export function formatRelativeTime(
  timestamp: string,
  keys: RelativeTimeKeys,
): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return keys.justNow;
    if (diffMins < 60) return keys.minutesAgo(diffMins);
    if (diffHours < 24) return keys.hoursAgo(diffHours);
    if (diffDays < 7) return keys.daysAgo(diffDays);
    return date.toLocaleDateString();
  } catch {
    return keys.justNow;
  }
}
