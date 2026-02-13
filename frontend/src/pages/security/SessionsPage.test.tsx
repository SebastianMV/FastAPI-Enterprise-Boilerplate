import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import SessionsPage from './SessionsPage';

const mockList = vi.fn();
const mockRevoke = vi.fn();
const mockRevokeAll = vi.fn();

vi.mock('@/services/api', () => ({
  sessionsService: {
    list: (...args: unknown[]) => mockList(...args),
    revoke: (...args: unknown[]) => mockRevoke(...args),
    revokeAll: (...args: unknown[]) => mockRevokeAll(...args),
  },
}));

vi.mock('@/components/common/Modal', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  Modal: ({ isOpen, children, title }: any) =>
    isOpen ? <div data-testid="modal"><h2>{title}</h2>{children}</div> : null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  ConfirmModal: ({ isOpen, onConfirm, title, message }: any) =>
    isOpen ? (
      <div data-testid="confirm-modal">
        <h2>{title}</h2>
        <p>{message}</p>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  AlertModal: ({ isOpen, title, message }: any) =>
    isOpen ? (
      <div data-testid="alert-modal">
        <h2>{title}</h2>
        <p>{message}</p>
      </div>
    ) : null,
}));

const mockSessions = {
  sessions: [
    {
      id: 's1',
      device_name: 'Chrome on Windows',
      device_type: 'desktop',
      ip_address: '192.168.1.1',
      location: 'Madrid, Spain',
      browser: 'Chrome 120',
      os: 'Windows 11',
      is_current: true,
      last_activity: new Date().toISOString(),
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 's2',
      device_name: 'Safari on iPhone',
      device_type: 'mobile',
      ip_address: '10.0.0.1',
      location: 'Barcelona',
      browser: 'Safari 17',
      os: 'iOS 17',
      is_current: false,
      last_activity: new Date(Date.now() - 3600000).toISOString(),
      created_at: '2024-01-02T00:00:00Z',
    },
    {
      id: 's3',
      device_name: 'Firefox on iPad',
      device_type: 'tablet',
      ip_address: '172.16.0.1',
      location: null,
      browser: 'Firefox 121',
      os: 'iPadOS 17',
      is_current: false,
      last_activity: new Date(Date.now() - 86400000).toISOString(),
      created_at: '2024-01-03T00:00:00Z',
    },
  ],
};

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SessionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('SessionsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue(mockSessions);
    mockRevoke.mockResolvedValue({ message: 'Session revoked' });
    mockRevokeAll.mockResolvedValue({ message: 'All sessions revoked' });
  });

  it('renders page title', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('sessions.title')).toBeInTheDocument();
    });
  });

  it('shows subtitle', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('sessions.subtitle')).toBeInTheDocument();
    });
  });

  it('displays sessions', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Chrome on Windows')).toBeInTheDocument();
    });
    expect(screen.getByText('Safari on iPhone')).toBeInTheDocument();
    expect(screen.getByText('Firefox on iPad')).toBeInTheDocument();
  });

  it('shows current session badge', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('sessions.currentSession')).toBeInTheDocument();
    });
  });

  it('shows IP addresses and locations', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/192\.168\.x\.x/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Madrid, Spain/)).toBeInTheDocument();
  });

  it('shows browser and OS info', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('sessions.title')).toBeInTheDocument();
    });
    // After data loads, browser/OS info uses i18n key
    const browserInfoElements = screen.getAllByText(/browserOnOs/);
    expect(browserInfoElements.length).toBeGreaterThan(0);
  });

  it('shows security tip card', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('sessions.securityTip')).toBeInTheDocument();
    });
    expect(screen.getByText('sessions.securityTipMessage')).toBeInTheDocument();
  });

  it('shows sign out all button when multiple sessions', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('sessions.signOutAll')).toBeInTheDocument();
    });
  });

  it('opens revoke all modal', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('sessions.signOutAll')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('sessions.signOutAll'));
    await waitFor(() => {
      expect(screen.getByTestId('confirm-modal')).toBeInTheDocument();
    });
    expect(screen.getByText('sessions.revokeAllTitle')).toBeInTheDocument();
  });

  it('shows error state', async () => {
    mockList.mockRejectedValue(new Error('Network error'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('sessions.loadError')).toBeInTheDocument();
    });
  });

  it('shows empty state when no sessions', async () => {
    mockList.mockResolvedValue({ sessions: [] });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('sessions.noSessions')).toBeInTheDocument();
    });
  });
});
