import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useConfigStore } from '@/stores/configStore';

// Layouts
import AuthLayout from '@/components/layouts/AuthLayout';
import DashboardLayout from '@/components/layouts/DashboardLayout';

// Pages
import LoginPage from '@/pages/auth/LoginPage';
import RegisterPage from '@/pages/auth/RegisterPage';
import ForgotPasswordPage from '@/pages/auth/ForgotPasswordPage';
import ResetPasswordPage from '@/pages/auth/ResetPasswordPage';
import OAuthCallbackPage from '@/pages/auth/OAuthCallbackPage';
import DashboardPage from '@/pages/dashboard/DashboardPage';
import UsersPage from '@/pages/users/UsersPage';
import SettingsPage from '@/pages/settings/SettingsPage';
import ApiKeysPage from '@/pages/settings/ApiKeysPage';
import ProfilePage from '@/pages/profile/ProfilePage';
import MFASettingsPage from '@/pages/security/MFASettingsPage';
import SearchPage from '@/pages/search/SearchPage';
import NotificationsPage from '@/pages/notifications/NotificationsPage';
import ChatPage from '@/pages/chat/ChatPage';

/**
 * Protected route wrapper.
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

/**
 * Chat feature route wrapper (requires chat to be enabled).
 */
function ChatRoute({ children }: { children: React.ReactNode }) {
  const chat_enabled = useConfigStore((state) => state.chat_enabled);

  if (!chat_enabled) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

/**
 * Main application component.
 */
export default function App() {
  return (
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
        <Route path="/users" element={<UsersPage />} />
        
        {/* Chat routes (protected by feature flag) */}
        <Route path="/chat" element={<ChatRoute><ChatPage /></ChatRoute>} />
        <Route path="/chat/:conversationId" element={<ChatRoute><ChatPage /></ChatRoute>} />
        
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/api-keys" element={<ApiKeysPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/security/mfa" element={<MFASettingsPage />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
