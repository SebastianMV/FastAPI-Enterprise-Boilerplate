import {
  dashboardService,
  type SystemHealth,
} from "@/services/dashboardService";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  Database,
  Loader2,
  RefreshCw,
  Server,
  XCircle,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

/** Auto-refresh interval in milliseconds (30s). */
const AUTO_REFRESH_INTERVAL = 30_000;

/**
 * Dedicated System Health page for superadmins.
 *
 * Shows database, cache, response time, uptime, and active sessions
 * with auto-refresh and manual refresh capabilities.
 */
export default function SystemHealthPage() {
  const { t } = useTranslation();
  const [autoRefresh, setAutoRefresh] = useState(true);

  const {
    data: health,
    isLoading,
    isError,
    refetch,
    dataUpdatedAt,
  } = useQuery<SystemHealth>({
    queryKey: ["admin", "system-health"],
    queryFn: () => dashboardService.getHealth(),
    refetchInterval: autoRefresh ? AUTO_REFRESH_INTERVAL : false,
    staleTime: 10_000,
  });

  // Format the "last updated" timestamp
  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : null;

  const handleRefresh = useCallback(() => {
    void refetch();
  }, [refetch]);

  // Keyboard shortcut: R to refresh
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "r" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const target = e.target as HTMLElement;
        if (target.tagName !== "INPUT" && target.tagName !== "TEXTAREA") {
          handleRefresh();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleRefresh]);

  const getStatusIcon = (status: string) => {
    if (status === "healthy") {
      return <CheckCircle className="w-6 h-6 text-green-500" />;
    }
    if (status === "degraded") {
      return <AlertCircle className="w-6 h-6 text-yellow-500" />;
    }
    return <XCircle className="w-6 h-6 text-red-500" />;
  };

  const getStatusColor = (status: string) => {
    if (status === "healthy") return "text-green-600 dark:text-green-400";
    if (status === "degraded") return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getStatusLabel = (status: string) => {
    if (status === "healthy") return t("systemHealth.healthy");
    if (status === "degraded") return t("systemHealth.degraded");
    return t("systemHealth.unhealthy");
  };

  const getUptimeColor = (pct: number) => {
    if (pct >= 99.9) return "text-green-600 dark:text-green-400";
    if (pct >= 99.0) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getResponseTimeColor = (ms: number) => {
    if (ms <= 100) return "text-green-600 dark:text-green-400";
    if (ms <= 500) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t("systemHealth.loading")}
          </p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-center space-y-4">
          <XCircle className="w-12 h-12 text-red-500 mx-auto" />
          <p className="text-lg text-slate-600 dark:text-slate-400">
            {t("systemHealth.failedToLoad")}
          </p>
          <button onClick={handleRefresh} className="btn btn-primary">
            {t("common.retry")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {t("systemHealth.title")}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t("systemHealth.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-slate-400 dark:text-slate-500">
              {t("dashboard.lastUpdated")}: {lastUpdated}
            </span>
          )}
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
            />
            {t("systemHealth.autoRefresh")}
          </label>
          <button
            onClick={handleRefresh}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            {t("dashboard.refreshData")}
          </button>
        </div>
      </div>

      {/* Overall Status Banner */}
      {health && (
        <div
          className={`card p-6 border-l-4 ${
            health.database_status === "healthy" &&
            health.cache_status === "healthy"
              ? "border-l-green-500 bg-green-50 dark:bg-green-900/10"
              : health.database_status === "unhealthy"
                ? "border-l-red-500 bg-red-50 dark:bg-red-900/10"
                : "border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/10"
          }`}
        >
          <div className="flex items-center gap-3">
            <Server className="w-6 h-6 text-slate-600 dark:text-slate-400" />
            <div>
              <p className="font-semibold text-slate-900 dark:text-white">
                {health.database_status === "healthy" &&
                health.cache_status === "healthy"
                  ? t("systemHealth.allSystemsOperational")
                  : t("systemHealth.issuesDetected")}
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t("systemHealth.uptimeLabel", {
                  value: health.uptime_percentage,
                })}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Service Cards Grid */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Database */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <Database className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <h3 className="font-semibold text-slate-900 dark:text-white">
                  {t("systemHealth.database")}
                </h3>
              </div>
              {getStatusIcon(health.database_status)}
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {t("systemHealth.status")}
                </span>
                <span
                  className={`text-sm font-medium ${getStatusColor(health.database_status)}`}
                >
                  {getStatusLabel(health.database_status)}
                </span>
              </div>
            </div>
          </div>

          {/* Cache (Redis) */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                  <Zap className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                </div>
                <h3 className="font-semibold text-slate-900 dark:text-white">
                  {t("systemHealth.cache")}
                </h3>
              </div>
              {getStatusIcon(health.cache_status)}
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {t("systemHealth.status")}
                </span>
                <span
                  className={`text-sm font-medium ${getStatusColor(health.cache_status)}`}
                >
                  {getStatusLabel(health.cache_status)}
                </span>
              </div>
            </div>
          </div>

          {/* Active Sessions */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                  <Activity className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="font-semibold text-slate-900 dark:text-white">
                  {t("systemHealth.activeSessions")}
                </h3>
              </div>
            </div>
            <div className="text-3xl font-bold text-slate-900 dark:text-white">
              {health.active_sessions}
            </div>
          </div>
        </div>
      )}

      {/* Metrics Row */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Response Time */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-cyan-100 dark:bg-cyan-900/30 rounded-lg">
                <Clock className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              </div>
              <h3 className="font-semibold text-slate-900 dark:text-white">
                {t("systemHealth.avgResponseTime")}
              </h3>
            </div>
            <div className="flex items-baseline gap-2">
              <span
                className={`text-3xl font-bold ${getResponseTimeColor(health.avg_response_time_ms)}`}
              >
                {health.avg_response_time_ms}
              </span>
              <span className="text-sm text-slate-500 dark:text-slate-400">
                {t("common.ms")}
              </span>
            </div>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
              {health.avg_response_time_ms <= 100
                ? t("systemHealth.responseExcellent")
                : health.avg_response_time_ms <= 500
                  ? t("systemHealth.responseAcceptable")
                  : t("systemHealth.responseSlow")}
            </p>
          </div>

          {/* Uptime */}
          <div className="card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <h3 className="font-semibold text-slate-900 dark:text-white">
                {t("systemHealth.uptime")}
              </h3>
            </div>
            <div className="flex items-baseline gap-1">
              <span
                className={`text-3xl font-bold ${getUptimeColor(health.uptime_percentage)}`}
              >
                {health.uptime_percentage}
              </span>
              <span
                className={`text-xl font-bold ${getUptimeColor(health.uptime_percentage)}`}
              >
                %
              </span>
            </div>
            {/* Visual bar */}
            <div className="mt-3 w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${
                  health.uptime_percentage >= 99.9
                    ? "bg-green-500"
                    : health.uptime_percentage >= 99.0
                      ? "bg-yellow-500"
                      : "bg-red-500"
                }`}
                style={{ width: `${Math.min(100, health.uptime_percentage)}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
