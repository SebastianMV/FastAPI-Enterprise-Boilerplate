import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import SettingsPage from './SettingsPage';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockDeleteUser = vi.fn();
vi.mock('@/services/api', () => ({
  usersService: {
    delete: (...args: unknown[]) => mockDeleteUser(...args),
  },
}));

const mockLogout = vi.fn();
let mockUser: any = { first_name: 'John', last_name: 'Doe', email: 'john@test.com', is_superuser: false, id: 'u1' };

vi.mock('@/stores/authStore', () => ({
  useAuthStore: (selector: (s: any) => any) =>
    selector({ user: mockUser, logout: mockLogout }),
}));

vi.mock('@/stores/configStore', () => ({
  useConfigStore: () => ({ websocket_enabled: true, websocket_notifications: false }),
}));

vi.mock('@/hooks/useDarkMode', () => ({
  useDarkMode: () => ({ theme: 'light', setTheme: vi.fn() }),
}));

vi.mock('@/i18n', () => ({
  SUPPORTED_LANGUAGES: [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
  ],
}));

vi.mock('@/components/common/Modal', () => ({
  ConfirmModal: ({ isOpen, onConfirm, title }: any) =>
    isOpen ? (
      <div data-testid="confirm-modal">
        <h2>{title}</h2>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null,
  AlertModal: ({ isOpen, title, message }: any) =>
    isOpen ? <div data-testid="alert-modal"><h2>{title}</h2><p>{message}</p></div> : null,
}));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = { first_name: 'John', last_name: 'Doe', email: 'john@test.com', is_superuser: false, id: 'u1' };
  });

  it('renders page title', () => {
    renderPage();
    expect(screen.getByText('settings.title')).toBeInTheDocument();
  });

  it('shows user profile card', () => {
    renderPage();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john@test.com')).toBeInTheDocument();
  });

  it('shows user role', () => {
    renderPage();
    expect(screen.getByText('settings.user')).toBeInTheDocument();
  });

  it('shows admin role for superuser', () => {
    mockUser = { ...mockUser, is_superuser: true };
    renderPage();
    expect(screen.getByText('settings.administrator')).toBeInTheDocument();
  });

  it('shows notifications section', () => {
    renderPage();
    expect(screen.getByText('settings.notifications')).toBeInTheDocument();
    expect(screen.getByText('settings.emailNotifications')).toBeInTheDocument();
  });

  it('shows appearance section with theme options', () => {
    renderPage();
    expect(screen.getByText('settings.appearance')).toBeInTheDocument();
    expect(screen.getByText('settings.lightMode')).toBeInTheDocument();
    expect(screen.getByText('settings.darkMode')).toBeInTheDocument();
    expect(screen.getByText('settings.systemTheme')).toBeInTheDocument();
  });

  it('shows language section', () => {
    renderPage();
    expect(screen.getByText('settings.language')).toBeInTheDocument();
  });

  it('shows features section', () => {
    renderPage();
    expect(screen.getByText('settings.features')).toBeInTheDocument();
    expect(screen.getByText('settings.websocketConnection')).toBeInTheDocument();
    expect(screen.getByText('settings.realtimeNotifications')).toBeInTheDocument();
  });

  it('shows websocket status', () => {
    renderPage();
    expect(screen.getByText('settings.enabled')).toBeInTheDocument();
    expect(screen.getByText('settings.disabled')).toBeInTheDocument();
  });

  it('shows security section with navigation', () => {
    renderPage();
    expect(screen.getByText('settings.twoFactorAuth')).toBeInTheDocument();
    expect(screen.getByText('settings.activeSessions')).toBeInTheDocument();
  });

  it('shows danger zone', () => {
    renderPage();
    expect(screen.getByText('settings.dangerZone')).toBeInTheDocument();
    expect(screen.getAllByText('settings.deleteAccount').length).toBeGreaterThanOrEqual(1);
  });

  it('navigates to profile on edit button click', () => {
    renderPage();
    fireEvent.click(screen.getByText('profile.editProfile'));
    expect(mockNavigate).toHaveBeenCalledWith('/profile');
  });
});
