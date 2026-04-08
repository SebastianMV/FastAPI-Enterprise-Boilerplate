import { AlertModal, ConfirmModal } from "@/components/common/Modal";
import { sessionsService, type UserSession } from "@/services/api";
import { formatRelativeTime as formatRelativeTimeShared } from "@/utils/formatRelativeTime";
import { maskIpAddress, sanitizeText } from "@/utils/security";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle,
  Clock,
  Globe,
  LogOut,
  Monitor,
  Shield,
  Smartphone,
  Tablet,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

/**
 * Get device icon based on device type
 */
function DeviceIcon({ type }: { type: string }) {
  switch (type.toLowerCase()) {
    case "mobile":
      return <Smartphone className="w-5 h-5" />;
    case "tablet":
      return <Tablet className="w-5 h-5" />;
    default:
      return <Monitor className="w-5 h-5" />;
  }
}

/**
 * Format relative time
 */
function formatRelativeTime(
  dateStr: string,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  return formatRelativeTimeShared(dateStr, {
    justNow: t("sessions.timeAgo.justNow"),
    minutesAgo: (count: number) => t("sessions.timeAgo.minutesAgo", { count }),
    hoursAgo: (count: number) => t("sessions.timeAgo.hoursAgo", { count }),
    daysAgo: (count: number) => t("sessions.timeAgo.daysAgo", { count }),
  });
}

/**
 * Sessions management page component.
 */
export default function SessionsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showRevokeAllModal, setShowRevokeAllModal] = useState(false);
  const [sessionToRevoke, setSessionToRevoke] = useState<UserSession | null>(
    null,
  );
  const [alertModal, setAlertModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    variant: "success" | "error";
  }>({ isOpen: false, title: "", message: "", variant: "success" });

  // Fetch sessions
  const { data, isLoading, error } = useQuery({
    queryKey: ["sessions"],
    queryFn: sessionsService.list,
  });

  // Revoke single session mutation
  const revokeMutation = useMutation({
    mutationFn: (sessionId: string) => sessionsService.revoke(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      setSessionToRevoke(null);
      setAlertModal({
        isOpen: true,
        title: t("sessions.sessionRevoked"),
        message: t("sessions.sessionRevokedMessage"),
        variant: "success",
      });
    },
    onError: () => {
      setSessionToRevoke(null);
      setAlertModal({
        isOpen: true,
        title: t("common.error"),
        message: t("sessions.revokeError"),
        variant: "error",
      });
    },
  });

  // Revoke all sessions mutation
  const revokeAllMutation = useMutation({
    mutationFn: sessionsService.revokeAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      setShowRevokeAllModal(false);
      setAlertModal({
        isOpen: true,
        title: t("sessions.sessionsRevoked"),
        message: t("sessions.allSessionsRevokedMessage"),
        variant: "success",
      });
    },
    onError: () => {
      setShowRevokeAllModal(false);
      setAlertModal({
        isOpen: true,
        title: t("common.error"),
        message: t("sessions.revokeAllError"),
        variant: "error",
      });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6">
        <div className="text-center text-red-600">
          {t("sessions.loadError")}
        </div>
      </div>
    );
  }

  const sessions = data?.items || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {t("sessions.title")}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            {t("sessions.subtitle")}
          </p>
        </div>
        {sessions.length > 1 && (
          <button
            onClick={() => setShowRevokeAllModal(true)}
            className="btn-danger flex items-center space-x-2"
          >
            <LogOut className="w-4 h-4" />
            <span>{t("sessions.signOutAll")}</span>
          </button>
        )}
      </div>

      {/* Info card */}
      <div className="card p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <div className="flex items-start space-x-3">
          <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
          <div>
            <h3 className="font-medium text-blue-900 dark:text-blue-100">
              {t("sessions.securityTip")}
            </h3>
            <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
              {t("sessions.securityTipMessage")}
            </p>
          </div>
        </div>
      </div>

      {/* Sessions list */}
      <div className="card divide-y divide-slate-200 dark:divide-slate-700">
        {sessions.length === 0 ? (
          <div className="p-6 text-center text-slate-500">
            {t("sessions.noSessions")}
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`p-6 flex items-center justify-between ${
                session.is_current ? "bg-green-50 dark:bg-green-900/10" : ""
              }`}
            >
              <div className="flex items-center space-x-4">
                {/* Device icon */}
                <div
                  className={`p-3 rounded-full ${
                    session.is_current
                      ? "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                  }`}
                >
                  <DeviceIcon type={session.device_type} />
                </div>

                {/* Session info */}
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="font-medium text-slate-900 dark:text-white">
                      {sanitizeText(session.device_name)}
                    </h3>
                    {session.is_current && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        {t("sessions.currentSession")}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-4 mt-1 text-sm text-slate-500 dark:text-slate-400">
                    <span className="flex items-center">
                      <Globe className="w-4 h-4 mr-1" />
                      {maskIpAddress(session.ip_address)}
                      {session.location &&
                        ` • ${sanitizeText(session.location)}`}
                    </span>
                    <span className="flex items-center">
                      <Clock className="w-4 h-4 mr-1" />
                      {formatRelativeTime(session.last_activity, t)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                    {t("sessions.browserOnOs", {
                      browser: sanitizeText(session.browser),
                      os: sanitizeText(session.os),
                    })}{" "}
                    • {t("sessions.started")}{" "}
                    {new Date(session.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              {/* Revoke button */}
              {!session.is_current && (
                <button
                  onClick={() => setSessionToRevoke(session)}
                  className="btn-ghost text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                  aria-label={t("sessions.revokeSession")}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          ))
        )}
      </div>

      {/* Revoke single session modal */}
      <ConfirmModal
        isOpen={!!sessionToRevoke}
        onClose={() => setSessionToRevoke(null)}
        onConfirm={() =>
          sessionToRevoke && revokeMutation.mutate(sessionToRevoke.id)
        }
        title={t("sessions.revokeSession")}
        message={t("sessions.revokeMessage", {
          device: sessionToRevoke?.device_name,
        })}
        confirmText={t("apiKeys.revoke")}
        variant="danger"
        isLoading={revokeMutation.isPending}
      />

      {/* Revoke all modal */}
      <ConfirmModal
        isOpen={showRevokeAllModal}
        onClose={() => setShowRevokeAllModal(false)}
        onConfirm={() => revokeAllMutation.mutate()}
        title={t("sessions.revokeAllTitle")}
        message={t("sessions.revokeAllMessage")}
        confirmText={t("sessions.revokeAllConfirm")}
        variant="danger"
        isLoading={revokeAllMutation.isPending}
      />

      {/* Alert modal */}
      <AlertModal
        isOpen={alertModal.isOpen}
        onClose={() => setAlertModal({ ...alertModal, isOpen: false })}
        title={alertModal.title}
        message={alertModal.message}
        variant={alertModal.variant}
      />
    </div>
  );
}
