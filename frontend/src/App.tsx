import ErrorBoundary from '@/components/common/ErrorBoundary';
import { AUTH_LOGOUT_EVENT } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { Loader2 } from 'lucide-react';
import { Suspense, lazy, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { useShallow } from 'zustand/react/shallow';

// Layouts - loaded immediately (used on all pages)
import AuthLayout from '@/components/layouts/AuthLayout';
import DashboardLayout from '@/components/layouts/DashboardLayout';

// Lazy loaded pages for code splitting
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('@/pages/auth/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('@/pages/auth/ResetPasswordPage'));
const OAuthCallbackPage = lazy(() => import('@/pages/auth/OAuthCallbackPage'));
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));
const UsersPage = lazy(() => import('@/pages/users/UsersPage'));
const SettingsPage = lazy(() => import('@/pages/settings/SettingsPage'));
const ApiKeysPage = lazy(() => import('@/pages/settings/ApiKeysPage'));
const ProfilePage = lazy(() => import('@/pages/profile/ProfilePage'));
const MFASettingsPage = lazy(() => import('@/pages/security/MFASettingsPage'));
const SessionsPage = lazy(() => import('@/pages/security/SessionsPage'));
const VerifyEmailPage = lazy(() => import('@/pages/auth/VerifyEmailPage'));
const SearchPage = lazy(() => import('@/pages/search/SearchPage'));
const NotificationsPage = lazy(() => import('@/pages/notifications/NotificationsPage'));
const RolesPage = lazy(() => import('@/pages/roles/RolesPage'));
const AuditLogPage = lazy(() => import('@/pages/audit/AuditLogPage'));
const TenantsPage = lazy(() => import('@/pages/admin/TenantsPage'));
const DataExchangePage = lazy(() => import('@/pages/data/DataExchangePage'));

/**
 * Loading fallback component for lazy loaded pages.
 */
function PageLoader() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="flex flex-col items-center space-y-4">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        <p className="text-sm text-slate-500 dark:text-slate-400">{t('common.loading')}</p>
      </div>
    </div>
  );
}

/**
 * Protected route wrapper — requires authentication.
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isInitializing } = useAuthStore(
    useShallow((s) => ({ isAuthenticated: s.isAuthenticated, isInitializing: s.isInitializing }))
  );

  // Wait for session restoration before redirecting
  if (isInitializing) {
    return <PageLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

/**
 * Admin route wrapper — requires superuser privileges.
 * Shows a toast notification and redirects non-superusers to /dashboard.
 */
function AdminRoute({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const { isAuthenticated, user } = useAuthStore(
    useShallow((s) => ({ isAuthenticated: s.isAuthenticated, user: s.user }))
  );

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!user?.is_superuser) {
    // Show an inline access-denied message instead of a silent redirect
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="text-center space-y-4">
          <p className="text-lg text-slate-600 dark:text-slate-400">{t('common.accessDenied')}</p>
          <Link to="/dashboard" className="text-primary-600 hover:underline">{t('navigation.dashboard')}</Link>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Main application component.
 */
export default function App() {
  const { user, fetchUser, logout } = useAuthStore(
    useShallow((s) => ({
      user: s.user,
      fetchUser: s.fetchUser,
      logout: s.logout,
    }))
  );
  const navigate = useNavigate();

  // SPA-friendly redirect on 401 (fired by api.ts interceptor)
  const handleAuthLogout = useCallback(() => {
    logout();
    navigate('/login', { replace: true });
  }, [logout, navigate]);

  useEffect(() => {
    window.addEventListener(AUTH_LOGOUT_EVENT, handleAuthLogout);
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, handleAuthLogout);
  }, [handleAuthLogout]);

  // Attempt to restore session from HttpOnly cookies on app load.
  // Since we no longer persist user/isAuthenticated to localStorage,
  // we always try fetchUser() once to check if valid cookies exist.
  useEffect(() => {
    let cancelled = false;
    if (!user) {
      (async () => {
        try { await fetchUser(); } catch {
          if (!cancelled) {
            useAuthStore.setState({ isInitializing: false });
          }
        }
      })();
    }
    return () => { cancelled = true; };
  }, [user, fetchUser]);

  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Routes>
        {/* Public routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
        </Route>

        {/* OAuth callback - no layout */}
        <Route path="/auth/oauth/callback" element={<OAuthCallbackPage />} />

        {/* Email verification - no layout */}
        <Route path="/verify-email" element={<VerifyEmailPage />} />

        {/* Protected routes */}
        <Route
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/users" element={<AdminRoute><UsersPage /></AdminRoute>} />

          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/settings/api-keys" element={<ApiKeysPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/security/mfa" element={<MFASettingsPage />} />
          <Route path="/security/sessions" element={<SessionsPage />} />
          <Route path="/security/audit" element={<AdminRoute><AuditLogPage /></AdminRoute>} />

          {/* Admin-only routes — require superuser */}
          <Route path="/admin/tenants" element={<AdminRoute><TenantsPage /></AdminRoute>} />
          <Route path="/admin/data" element={<AdminRoute><DataExchangePage /></AdminRoute>} />
          <Route path="/roles" element={<AdminRoute><RolesPage /></AdminRoute>} />
        </Route>

        {/* 404 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
    </ErrorBoundary>
  );
}
