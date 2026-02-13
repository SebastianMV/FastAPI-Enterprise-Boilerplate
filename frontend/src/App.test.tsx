/**
 * Unit tests for App component — route wiring, ProtectedRoute, AdminRoute.
 */
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock all lazy-loaded pages to simple stubs
vi.mock('@/pages/auth/LoginPage', () => ({
  default: () => <div data-testid="login-page">Login Page</div>,
}));
vi.mock('@/pages/auth/RegisterPage', () => ({
  default: () => <div data-testid="register-page">Register Page</div>,
}));
vi.mock('@/pages/auth/ForgotPasswordPage', () => ({
  default: () => <div data-testid="forgot-password-page">Forgot Password</div>,
}));
vi.mock('@/pages/auth/ResetPasswordPage', () => ({
  default: () => <div data-testid="reset-password-page">Reset Password</div>,
}));
vi.mock('@/pages/auth/OAuthCallbackPage', () => ({
  default: () => <div data-testid="oauth-callback-page">OAuth Callback</div>,
}));
vi.mock('@/pages/auth/VerifyEmailPage', () => ({
  default: () => <div data-testid="verify-email-page">Verify Email</div>,
}));
vi.mock('@/pages/dashboard/DashboardPage', () => ({
  default: () => <div data-testid="dashboard-page">Dashboard</div>,
}));
vi.mock('@/pages/users/UsersPage', () => ({
  default: () => <div data-testid="users-page">Users</div>,
}));
vi.mock('@/pages/settings/SettingsPage', () => ({
  default: () => <div data-testid="settings-page">Settings</div>,
}));
vi.mock('@/pages/settings/ApiKeysPage', () => ({
  default: () => <div data-testid="apikeys-page">API Keys</div>,
}));
vi.mock('@/pages/profile/ProfilePage', () => ({
  default: () => <div data-testid="profile-page">Profile</div>,
}));
vi.mock('@/pages/security/MFASettingsPage', () => ({
  default: () => <div data-testid="mfa-page">MFA Settings</div>,
}));
vi.mock('@/pages/security/SessionsPage', () => ({
  default: () => <div data-testid="sessions-page">Sessions</div>,
}));
vi.mock('@/pages/search/SearchPage', () => ({
  default: () => <div data-testid="search-page">Search</div>,
}));
vi.mock('@/pages/notifications/NotificationsPage', () => ({
  default: () => <div data-testid="notifications-page">Notifications</div>,
}));
vi.mock('@/pages/roles/RolesPage', () => ({
  default: () => <div data-testid="roles-page">Roles</div>,
}));
vi.mock('@/pages/audit/AuditLogPage', () => ({
  default: () => <div data-testid="audit-page">Audit Log</div>,
}));
vi.mock('@/pages/admin/TenantsPage', () => ({
  default: () => <div data-testid="tenants-page">Tenants</div>,
}));
vi.mock('@/pages/data/DataExchangePage', () => ({
  default: () => <div data-testid="data-exchange-page">Data Exchange</div>,
}));

// Mock DashboardLayout to simply render children
vi.mock('@/components/layouts/DashboardLayout', () => ({
  default: () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports -- vitest mock factory requires synchronous imports
    // @ts-expect-error -- vitest mock factory: require() is untyped but works at runtime
    const { Outlet } = require('react-router-dom');
    return <div data-testid="dashboard-layout"><Outlet /></div>;
  },
}));

// Mock store
const mockAuthState = {
  isAuthenticated: false,
  user: null,
  fetchUser: vi.fn().mockResolvedValue(undefined),
};

vi.mock('@/stores/authStore', () => ({
  useAuthStore: (selector: (state: typeof mockAuthState) => unknown) => selector(mockAuthState),
}));

import App from './App';

function renderApp(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>
  );
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthState.isAuthenticated = false;
    mockAuthState.user = null;
  });

  describe('Public routes', () => {
    it('should render login page at /login', async () => {
      renderApp('/login');
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });

    it('should render register page at /register', async () => {
      renderApp('/register');
      await waitFor(() => {
        expect(screen.getByTestId('register-page')).toBeInTheDocument();
      });
    });

    it('should render forgot password page', async () => {
      renderApp('/forgot-password');
      await waitFor(() => {
        expect(screen.getByTestId('forgot-password-page')).toBeInTheDocument();
      });
    });

    it('should render reset password page', async () => {
      renderApp('/reset-password');
      await waitFor(() => {
        expect(screen.getByTestId('reset-password-page')).toBeInTheDocument();
      });
    });

    it('should render OAuth callback page', async () => {
      renderApp('/auth/oauth/callback');
      await waitFor(() => {
        expect(screen.getByTestId('oauth-callback-page')).toBeInTheDocument();
      });
    });

    it('should render verify email page', async () => {
      renderApp('/verify-email');
      await waitFor(() => {
        expect(screen.getByTestId('verify-email-page')).toBeInTheDocument();
      });
    });
  });

  describe('ProtectedRoute', () => {
    it('should redirect to /login when not authenticated', async () => {
      mockAuthState.isAuthenticated = false;
      renderApp('/dashboard');
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });

    it('should render dashboard when authenticated', async () => {
      mockAuthState.isAuthenticated = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- partial mock user
      mockAuthState.user = { id: '1', email: 'a@b.com', is_superuser: false } as any;
      renderApp('/dashboard');
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
    });

    it('should render users page when authenticated', async () => {
      mockAuthState.isAuthenticated = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- partial mock user
      mockAuthState.user = { id: '1', email: 'a@b.com', is_superuser: true } as any;
      renderApp('/users');
      await waitFor(() => {
        expect(screen.getByTestId('users-page')).toBeInTheDocument();
      });
    });
  });

  describe('AdminRoute', () => {
    it('should show access denied for non-superuser on admin routes', async () => {
      mockAuthState.isAuthenticated = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- partial mock user
      mockAuthState.user = { id: '1', email: 'a@b.com', is_superuser: false } as any;
      renderApp('/roles');
      await waitFor(() => {
        expect(screen.getByText('common.accessDenied')).toBeInTheDocument();
      });
    });

    it('should render admin page for superuser', async () => {
      mockAuthState.isAuthenticated = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- partial mock user
      mockAuthState.user = { id: '1', email: 'admin@b.com', is_superuser: true } as any;
      renderApp('/roles');
      await waitFor(() => {
        expect(screen.getByTestId('roles-page')).toBeInTheDocument();
      });
    });

    it('should redirect unauthenticated to login for admin routes', async () => {
      mockAuthState.isAuthenticated = false;
      renderApp('/admin/tenants');
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });
  });

  describe('Root redirect', () => {
    it('should redirect / to /dashboard when authenticated', async () => {
      mockAuthState.isAuthenticated = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- partial mock user
      mockAuthState.user = { id: '1', email: 'a@b.com', is_superuser: false } as any;
      renderApp('/');
      await waitFor(() => {
        expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
      });
    });
  });

  describe('404 redirect', () => {
    it('should redirect unknown routes to /', async () => {
      mockAuthState.isAuthenticated = false;
      renderApp('/this-does-not-exist');
      // Will redirect to / which redirects to /login (unauthenticated)
      await waitFor(() => {
        expect(screen.getByTestId('login-page')).toBeInTheDocument();
      });
    });
  });

  describe('fetchUser on init', () => {
    it('should call fetchUser when authenticated but no user', async () => {
      mockAuthState.isAuthenticated = true;
      mockAuthState.user = null;
      renderApp('/login');
      await waitFor(() => {
        expect(mockAuthState.fetchUser).toHaveBeenCalled();
      });
    });

    it('should not call fetchUser when user exists', async () => {
      mockAuthState.isAuthenticated = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- partial mock user
      mockAuthState.user = { id: '1', email: 'a@b.com' } as any;
      renderApp('/login');
      await waitFor(() => {
        expect(mockAuthState.fetchUser).not.toHaveBeenCalled();
      });
    });
  });
});
