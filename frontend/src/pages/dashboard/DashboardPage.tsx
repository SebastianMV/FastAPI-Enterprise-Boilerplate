import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import {
  dashboardService,
  type DashboardStats,
  type RecentActivity,
  type SystemHealth,
  type StatItem,
} from '@/services/api';
import {
  Users,
  Activity,
  Shield,
  Clock,
  Key,
  Settings,
  UserPlus,
  RefreshCw,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Database,
  Zap,
  Loader2,
  AlertCircle,
} from 'lucide-react';

/**
 * Dashboard overview page with real-time statistics and activity.
 */
export default function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<RecentActivity | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Prevent duplicate API calls
  const isFetchingRef = useRef(false);
  const hasFetchedRef = useRef(false);

  const fetchDashboardData = useCallback(async (showRefreshing = false) => {
    // Prevent duplicate calls
    if (isFetchingRef.current) {
      return;
    }
    
    isFetchingRef.current = true;
    
    try {
      if (showRefreshing) {
        setIsRefreshing(true);
      }
      setError(null);

      const [statsData, activityData, healthData] = await Promise.all([
        dashboardService.getStats(),
        dashboardService.getActivity(10),
        dashboardService.getHealth(),
      ]);

      setStats(statsData);
      setActivity(activityData);
      setHealth(healthData);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
      isFetchingRef.current = false;
    }
  }, []);

  useEffect(() => {
    // Only fetch once on mount
    if (!hasFetchedRef.current) {
      hasFetchedRef.current = true;
      fetchDashboardData();
    }

    // Auto-refresh every 60 seconds (reduced from 30 to avoid rate limiting)
    const interval = setInterval(() => {
      fetchDashboardData(false);
    }, 60000);

    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  const getStatIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case 'total users':
        return Users;
      case 'active users':
        return Activity;
      case 'api keys':
        return Key;
      case 'roles':
        return Shield;
      default:
        return Activity;
    }
  };

  const getChangeIcon = (changeType: string) => {
    switch (changeType) {
      case 'positive':
        return TrendingUp;
      case 'negative':
        return TrendingDown;
      default:
        return Minus;
    }
  };

  const formatRelativeTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getActivityIcon = (action: string) => {
    switch (action) {
      case 'user_registered':
        return UserPlus;
      case 'api_key_created':
        return Key;
      case 'settings_updated':
        return Settings;
      default:
        return Activity;
    }
  };

  const quickActions = [
    {
      label: 'Add User',
      icon: UserPlus,
      onClick: () => navigate('/users'),
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    },
    {
      label: 'API Keys',
      icon: Key,
      onClick: () => navigate('/settings/api-keys'),
      color: 'text-purple-600 dark:text-purple-400',
      bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    },
    {
      label: 'Settings',
      icon: Settings,
      onClick: () => navigate('/settings'),
      color: 'text-slate-600 dark:text-slate-400',
      bgColor: 'bg-slate-50 dark:bg-slate-800',
    },
    {
      label: 'Security',
      icon: Shield,
      onClick: () => navigate('/security/mfa'),
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-50 dark:bg-green-900/20',
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600 mx-auto mb-4" />
          <p className="text-slate-500 dark:text-slate-400">{t('dashboard.loadingDashboard')}</p>
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-slate-700 dark:text-slate-300 mb-4">{error}</p>
          <button
            onClick={() => fetchDashboardData()}
            className="btn-primary"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            {t('dashboard.refreshData')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {t('dashboard.welcome', { name: user?.first_name })}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Here's what's happening with your application today.
          </p>
        </div>
        <button
          onClick={() => fetchDashboardData(true)}
          disabled={isRefreshing}
          className="btn-secondary"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? `${t('common.loading')}` : t('dashboard.refreshData')}
        </button>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats?.stats.map((stat: StatItem) => {
          const IconComponent = getStatIcon(stat.name);
          const ChangeIcon = getChangeIcon(stat.change_type);
          return (
            <div key={stat.name} className="card p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {stat.name}
                  </p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                    {stat.value}
                  </p>
                </div>
                <div className="p-3 bg-primary-50 dark:bg-primary-900/20 rounded-xl">
                  <IconComponent className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <ChangeIcon
                  className={`w-4 h-4 mr-1 ${
                    stat.change_type === 'positive'
                      ? 'text-green-600 dark:text-green-400'
                      : stat.change_type === 'negative'
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-slate-500'
                  }`}
                />
                <span
                  className={`text-sm font-medium ${
                    stat.change_type === 'positive'
                      ? 'text-green-600 dark:text-green-400'
                      : stat.change_type === 'negative'
                        ? 'text-red-600 dark:text-red-400'
                        : 'text-slate-500'
                  }`}
                >
                  {stat.change}
                </span>
                <span className="text-sm text-slate-500 dark:text-slate-400 ml-2">
                  vs last month
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* System Health Banner */}
      {health && (
        <div className="card p-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-slate-500" />
                <span className="text-sm text-slate-600 dark:text-slate-400">Database:</span>
                {health.database_status === 'healthy' ? (
                  <span className="flex items-center text-green-600 dark:text-green-400 text-sm font-medium">
                    <CheckCircle className="w-4 h-4 mr-1" />
                    {t('dashboard.healthy')}
                  </span>
                ) : (
                  <span className="flex items-center text-red-600 dark:text-red-400 text-sm font-medium">
                    <XCircle className="w-4 h-4 mr-1" />
                    {t('dashboard.unhealthy')}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-slate-500" />
                <span className="text-sm text-slate-600 dark:text-slate-400">Cache:</span>
                {health.cache_status === 'healthy' ? (
                  <span className="flex items-center text-green-600 dark:text-green-400 text-sm font-medium">
                    <CheckCircle className="w-4 h-4 mr-1" />
                    {t('dashboard.healthy')}
                  </span>
                ) : (
                  <span className="flex items-center text-yellow-600 dark:text-yellow-400 text-sm font-medium">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {t('dashboard.degraded')}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-slate-500" />
                <span className="text-sm text-slate-600 dark:text-slate-400">Avg Response:</span>
                <span className="text-sm font-medium text-slate-900 dark:text-white">
                  {health.avg_response_time_ms}ms
                </span>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-slate-500" />
                <span className="text-sm text-slate-600 dark:text-slate-400">Active Sessions:</span>
                <span className="text-sm font-medium text-slate-900 dark:text-white">
                  {health.active_sessions}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600 dark:text-slate-400">Uptime:</span>
                <span className="text-sm font-medium text-green-600 dark:text-green-400">
                  {health.uptime_percentage}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent activity */}
        <div className="card">
          <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Recent Activity
            </h2>
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {activity?.total || 0} events
            </span>
          </div>
          <div className="p-6">
            {activity && activity.items.length > 0 ? (
              <div className="space-y-4">
                {activity.items.map((item) => {
                  const ActivityIcon = getActivityIcon(item.action);
                  return (
                    <div
                      key={item.id}
                      className="flex items-start gap-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg px-2 -mx-2 transition-colors"
                    >
                      <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg mt-0.5">
                        <ActivityIcon className="w-4 h-4 text-slate-600 dark:text-slate-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-700 dark:text-slate-300 truncate">
                          {item.description}
                        </p>
                        {item.user_email && (
                          <p className="text-xs text-slate-500 dark:text-slate-500 truncate">
                            {item.user_email}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap">
                        {formatRelativeTime(item.timestamp)}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <Activity className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  No recent activity
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Quick actions */}
        <div className="card">
          <div className="p-6 border-b border-slate-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Quick Actions
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-2 gap-4">
              {quickActions.map((action) => (
                <button
                  key={action.label}
                  onClick={action.onClick}
                  className="flex items-center gap-3 p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-primary-500 dark:hover:border-primary-500 hover:shadow-md transition-all group"
                >
                  <div className={`p-2 rounded-lg ${action.bgColor}`}>
                    <action.icon className={`w-5 h-5 ${action.color}`} />
                  </div>
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300 group-hover:text-primary-600 dark:group-hover:text-primary-400">
                    {action.label}
                  </span>
                </button>
              ))}
            </div>

            {/* Additional Stats */}
            {stats && (
              <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700">
                <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-4">
                  User Overview
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                      New users (last 7 days)
                    </span>
                    <span className="text-sm font-semibold text-slate-900 dark:text-white">
                      {stats.users_created_last_7_days}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                      New users (last 30 days)
                    </span>
                    <span className="text-sm font-semibold text-slate-900 dark:text-white">
                      {stats.users_created_last_30_days}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                      Active / Inactive
                    </span>
                    <span className="text-sm font-semibold text-slate-900 dark:text-white">
                      {stats.active_users} / {stats.inactive_users}
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 mt-2">
                    <div
                      className="bg-green-500 h-2 rounded-full transition-all"
                      style={{
                        width: `${stats.total_users > 0 ? (stats.active_users / stats.total_users) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
