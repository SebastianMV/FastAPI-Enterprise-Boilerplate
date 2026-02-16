import { dashboardService, type StatItem } from "@/services/api";
import { useAuthStore } from "@/stores/authStore";
import { formatRelativeTime } from "@/utils/formatRelativeTime";
import { maskEmail, sanitizeText } from "@/utils/security";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  Database,
  Key,
  Loader2,
  Minus,
  RefreshCw,
  Settings,
  Shield,
  TrendingDown,
  TrendingUp,
  UserPlus,
  Users,
  XCircle,
  Zap,
} from "lucide-react";
import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

/** Map API stat names to i18n keys for localized display. */
const STAT_NAME_I18N: Record<string, string> = {
  "Total Users": "dashboard.statTotalUsers",
  "Active Users": "dashboard.statActiveUsers",
  "API Keys": "dashboard.statApiKeys",
  Roles: "dashboard.statRoles",
};

/**
 * Dashboard overview page with real-time statistics and activity.
 */
export default function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const queryClient = useQueryClient();

  // ── React Query: stats, activity, health ──
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
    isFetching: statsRefreshing,
  } = useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: () => dashboardService.getStats(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const { data: activity } = useQuery({
    queryKey: ["dashboard", "activity"],
    queryFn: () => dashboardService.getActivity(10),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const { data: health } = useQuery({
    queryKey: ["dashboard", "health"],
    queryFn: () => dashboardService.getHealth(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const isLoading = statsLoading;
  const isRefreshing = statsRefreshing && !statsLoading;
  const error = statsError ? t("dashboard.failedToLoad") : null;

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }, [queryClient]);

  const getStatIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case "total users":
        return Users;
      case "active users":
        return Activity;
      case "api keys":
        return Key;
      case "roles":
        return Shield;
      default:
        return Activity;
    }
  };

  const getChangeIcon = (changeType: string) => {
    switch (changeType) {
      case "positive":
        return TrendingUp;
      case "negative":
        return TrendingDown;
      default:
        return Minus;
    }
  };

  const formatTime = (timestamp: string) =>
    formatRelativeTime(timestamp, {
      justNow: t("dashboard.justNow"),
      minutesAgo: (count) => t("dashboard.minAgo", { count }),
      hoursAgo: (count) => t("dashboard.hAgo", { count }),
      daysAgo: (count) => t("dashboard.dAgo", { count }),
    });

  const getActivityIcon = (action: string) => {
    switch (action) {
      case "user_registered":
        return UserPlus;
      case "api_key_created":
        return Key;
      case "settings_updated":
        return Settings;
      default:
        return Activity;
    }
  };

  const quickActions = useMemo(
    () => [
      {
        label: t("dashboard.addUser"),
        icon: UserPlus,
        onClick: () => navigate("/users"),
        color: "text-blue-600 dark:text-blue-400",
        bgColor: "bg-blue-50 dark:bg-blue-900/20",
      },
      {
        label: t("dashboard.apiKeys"),
        icon: Key,
        onClick: () => navigate("/settings/api-keys"),
        color: "text-purple-600 dark:text-purple-400",
        bgColor: "bg-purple-50 dark:bg-purple-900/20",
      },
      {
        label: t("dashboard.settings"),
        icon: Settings,
        onClick: () => navigate("/settings"),
        color: "text-slate-600 dark:text-slate-400",
        bgColor: "bg-slate-50 dark:bg-slate-800",
      },
      {
        label: t("dashboard.security"),
        icon: Shield,
        onClick: () => navigate("/security/mfa"),
        color: "text-green-600 dark:text-green-400",
        bgColor: "bg-green-50 dark:bg-green-900/20",
      },
    ],
    [t, navigate],
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600 mx-auto mb-4" />
          <p className="text-slate-500 dark:text-slate-400">
            {t("dashboard.loadingDashboard")}
          </p>
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
          <button onClick={handleRefresh} className="btn-primary">
            <RefreshCw className="w-4 h-4 mr-2" />
            {t("dashboard.refreshData")}
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
            {t("dashboard.welcome", { name: sanitizeText(user?.first_name ?? "") })}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {t("dashboard.overview")}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="btn-secondary"
        >
          <RefreshCw
            className={`w-4 h-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`}
          />
          {isRefreshing ? `${t("common.loading")}` : t("dashboard.refreshData")}
        </button>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats?.stats.map((stat: StatItem) => {
          const IconComponent = getStatIcon(stat.name);
          const ChangeIcon = getChangeIcon(stat.change_type);
          return (
            <div
              key={stat.name}
              className="card p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {STAT_NAME_I18N[stat.name]
                      ? t(STAT_NAME_I18N[stat.name])
                      : sanitizeText(stat.name)}
                  </p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                    {sanitizeText(String(stat.value))}
                  </p>
                </div>
                <div className="p-3 bg-primary-50 dark:bg-primary-900/20 rounded-xl">
                  <IconComponent className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                </div>
              </div>
              <div className="mt-4 flex items-center">
                <ChangeIcon
                  className={`w-4 h-4 mr-1 ${
                    stat.change_type === "positive"
                      ? "text-green-600 dark:text-green-400"
                      : stat.change_type === "negative"
                        ? "text-red-600 dark:text-red-400"
                        : "text-slate-500"
                  }`}
                />
                <span
                  className={`text-sm font-medium ${
                    stat.change_type === "positive"
                      ? "text-green-600 dark:text-green-400"
                      : stat.change_type === "negative"
                        ? "text-red-600 dark:text-red-400"
                        : "text-slate-500"
                  }`}
                >
                  {sanitizeText(String(stat.change))}
                </span>
                <span className="text-sm text-slate-500 dark:text-slate-400 ml-2">
                  {t("dashboard.vsLastMonth")}
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
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  {t("dashboard.database")}:
                </span>
                {health.database_status === "healthy" ? (
                  <span className="flex items-center text-green-600 dark:text-green-400 text-sm font-medium">
                    <CheckCircle className="w-4 h-4 mr-1" />
                    {t("dashboard.healthy")}
                  </span>
                ) : (
                  <span className="flex items-center text-red-600 dark:text-red-400 text-sm font-medium">
                    <XCircle className="w-4 h-4 mr-1" />
                    {t("dashboard.unhealthy")}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-slate-500" />
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  {t("dashboard.cache")}:
                </span>
                {health.cache_status === "healthy" ? (
                  <span className="flex items-center text-green-600 dark:text-green-400 text-sm font-medium">
                    <CheckCircle className="w-4 h-4 mr-1" />
                    {t("dashboard.healthy")}
                  </span>
                ) : (
                  <span className="flex items-center text-yellow-600 dark:text-yellow-400 text-sm font-medium">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {t("dashboard.degraded")}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-slate-500" />
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  {t("dashboard.avgResponseTime")}:
                </span>
                <span className="text-sm font-medium text-slate-900 dark:text-white">
                  {health.avg_response_time_ms}
                  {t("common.ms")}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-slate-500" />
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  {t("dashboard.activeSessions")}:
                </span>
                <span className="text-sm font-medium text-slate-900 dark:text-white">
                  {health.active_sessions}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  {t("dashboard.uptime")}:
                </span>
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
              {t("dashboard.recentActivity")}
            </h2>
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {activity?.total || 0} {t("dashboard.events")}
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
                          {sanitizeText(item.description)}
                        </p>
                        {item.user_email && (
                          <p className="text-xs text-slate-500 dark:text-slate-500 truncate">
                            {maskEmail(item.user_email)}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap">
                        {formatTime(item.timestamp)}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <Activity className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {t("dashboard.noRecentActivity")}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Quick actions */}
        <div className="card">
          <div className="p-6 border-b border-slate-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              {t("dashboard.quickActions")}
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
                  {t("dashboard.userOverview")}
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                      {t("dashboard.newUsersLast7Days")}
                    </span>
                    <span className="text-sm font-semibold text-slate-900 dark:text-white">
                      {stats.users_created_last_7_days}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                      {t("dashboard.newUsersLast30Days")}
                    </span>
                    <span className="text-sm font-semibold text-slate-900 dark:text-white">
                      {stats.users_created_last_30_days}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                      {t("dashboard.activeInactive")}
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
