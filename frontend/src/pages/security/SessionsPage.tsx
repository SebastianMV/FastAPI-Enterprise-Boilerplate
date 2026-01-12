import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sessionsService, type UserSession } from '@/services/api';
import { ConfirmModal, AlertModal } from '@/components/common/Modal';
import {
  Monitor,
  Smartphone,
  Tablet,
  Globe,
  Clock,
  Trash2,
  LogOut,
  Shield,
  CheckCircle,
} from 'lucide-react';

/**
 * Get device icon based on device type
 */
function DeviceIcon({ type }: { type: string }) {
  switch (type.toLowerCase()) {
    case 'mobile':
      return <Smartphone className="w-5 h-5" />;
    case 'tablet':
      return <Tablet className="w-5 h-5" />;
    default:
      return <Monitor className="w-5 h-5" />;
  }
}

/**
 * Format relative time
 */
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hours ago`;
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

/**
 * Sessions management page component.
 */
export default function SessionsPage() {
  const queryClient = useQueryClient();
  const [showRevokeAllModal, setShowRevokeAllModal] = useState(false);
  const [sessionToRevoke, setSessionToRevoke] = useState<UserSession | null>(null);
  const [alertModal, setAlertModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    variant: 'success' | 'error';
  }>({ isOpen: false, title: '', message: '', variant: 'success' });

  // Fetch sessions
  const { data, isLoading, error } = useQuery({
    queryKey: ['sessions'],
    queryFn: sessionsService.list,
  });

  // Revoke single session mutation
  const revokeMutation = useMutation({
    mutationFn: (sessionId: string) => sessionsService.revoke(sessionId),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setSessionToRevoke(null);
      setAlertModal({
        isOpen: true,
        title: 'Session Revoked',
        message: response.message,
        variant: 'success',
      });
    },
    onError: (error: Error) => {
      setSessionToRevoke(null);
      setAlertModal({
        isOpen: true,
        title: 'Error',
        message: error.message || 'Failed to revoke session',
        variant: 'error',
      });
    },
  });

  // Revoke all sessions mutation
  const revokeAllMutation = useMutation({
    mutationFn: sessionsService.revokeAll,
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setShowRevokeAllModal(false);
      setAlertModal({
        isOpen: true,
        title: 'Sessions Revoked',
        message: response.message,
        variant: 'success',
      });
    },
    onError: (error: Error) => {
      setShowRevokeAllModal(false);
      setAlertModal({
        isOpen: true,
        title: 'Error',
        message: error.message || 'Failed to revoke sessions',
        variant: 'error',
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
          Failed to load sessions. Please try again.
        </div>
      </div>
    );
  }

  const sessions = data?.sessions || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Active Sessions
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Manage your active sessions across devices
          </p>
        </div>
        {sessions.length > 1 && (
          <button
            onClick={() => setShowRevokeAllModal(true)}
            className="btn-danger flex items-center space-x-2"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign out all other devices</span>
          </button>
        )}
      </div>

      {/* Info card */}
      <div className="card p-4 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <div className="flex items-start space-x-3">
          <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
          <div>
            <h3 className="font-medium text-blue-900 dark:text-blue-100">
              Security Tip
            </h3>
            <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
              If you see any unfamiliar sessions, revoke them immediately and change your password.
            </p>
          </div>
        </div>
      </div>

      {/* Sessions list */}
      <div className="card divide-y divide-slate-200 dark:divide-slate-700">
        {sessions.length === 0 ? (
          <div className="p-6 text-center text-slate-500">
            No active sessions found.
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`p-6 flex items-center justify-between ${
                session.is_current ? 'bg-green-50 dark:bg-green-900/10' : ''
              }`}
            >
              <div className="flex items-center space-x-4">
                {/* Device icon */}
                <div className={`p-3 rounded-full ${
                  session.is_current 
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                }`}>
                  <DeviceIcon type={session.device_type} />
                </div>

                {/* Session info */}
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="font-medium text-slate-900 dark:text-white">
                      {session.device_name}
                    </h3>
                    {session.is_current && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Current session
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-4 mt-1 text-sm text-slate-500 dark:text-slate-400">
                    <span className="flex items-center">
                      <Globe className="w-4 h-4 mr-1" />
                      {session.ip_address}
                      {session.location && ` • ${session.location}`}
                    </span>
                    <span className="flex items-center">
                      <Clock className="w-4 h-4 mr-1" />
                      {formatRelativeTime(session.last_activity)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                    {session.browser} on {session.os} • Started {new Date(session.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              {/* Revoke button */}
              {!session.is_current && (
                <button
                  onClick={() => setSessionToRevoke(session)}
                  className="btn-ghost text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
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
        onConfirm={() => sessionToRevoke && revokeMutation.mutate(sessionToRevoke.id)}
        title="Revoke Session"
        message={`Are you sure you want to sign out from "${sessionToRevoke?.device_name}"? This device will need to log in again.`}
        confirmText="Revoke"
        variant="danger"
        isLoading={revokeMutation.isPending}
      />

      {/* Revoke all modal */}
      <ConfirmModal
        isOpen={showRevokeAllModal}
        onClose={() => setShowRevokeAllModal(false)}
        onConfirm={() => revokeAllMutation.mutate()}
        title="Sign Out All Other Devices"
        message="This will sign you out from all other devices. Only your current session will remain active."
        confirmText="Sign Out All"
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
