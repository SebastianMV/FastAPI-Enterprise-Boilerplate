import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AuditLogPage from './AuditLogPage';

const mockAuditList = vi.fn();
const mockGetActions = vi.fn();
const mockGetResourceTypes = vi.fn();

vi.mock('@/services/api', () => ({
  auditLogsService: {
    list: (...args: unknown[]) => mockAuditList(...args),
    getActions: (...args: unknown[]) => mockGetActions(...args),
    getResourceTypes: (...args: unknown[]) => mockGetResourceTypes(...args),
  },
}));

vi.mock('@/components/common/Modal', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  Modal: ({ isOpen, children, title }: any) =>
    isOpen ? <div data-testid="modal"><h2>{title}</h2>{children}</div> : null,
}));

const mockLogs = {
  items: [
    {
      id: 'log1',
      action: 'LOGIN',
      resource_type: 'auth',
      resource_name: null,
      actor_email: 'admin@test.com',
      actor_ip: '192.168.1.1',
      actor_user_agent: 'Mozilla/5.0',
      timestamp: '2024-06-01T12:00:00Z',
      reason: null,
      old_value: null,
      new_value: null,
      metadata: {},
    },
    {
      id: 'log2',
      action: 'CREATE',
      resource_type: 'user',
      resource_name: 'John Doe',
      actor_email: 'admin@test.com',
      actor_ip: '10.0.0.1',
      actor_user_agent: null,
      timestamp: '2024-06-01T11:00:00Z',
      reason: 'New employee',
      old_value: null,
      new_value: { email: 'john@test.com' },
      metadata: { source: 'admin_panel' },
    },
  ],
  total: 2,
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuditLogPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AuditLogPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuditList.mockResolvedValue(mockLogs);
    mockGetActions.mockResolvedValue(['LOGIN', 'CREATE', 'UPDATE', 'DELETE']);
    mockGetResourceTypes.mockResolvedValue(['auth', 'user', 'role']);
  });

  it('renders page title', () => {
    renderPage();
    expect(screen.getByText('audit.title')).toBeInTheDocument();
  });

  it('displays audit logs after loading', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getAllByText('ad***@test.com').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows action badges', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('audit.actions.LOGIN')).toBeInTheDocument();
    });
    expect(screen.getByText('audit.actions.CREATE')).toBeInTheDocument();
  });

  it('shows resource type', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('audit.resourceTypes.auth')).toBeInTheDocument();
    });
    expect(screen.getByText('audit.resourceTypes.user')).toBeInTheDocument();
  });

  it('shows IP addresses', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('192.168.x.x')).toBeInTheDocument();
    });
    expect(screen.getByText('10.0.x.x')).toBeInTheDocument();
  });

  it('toggles filter panel', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getAllByText('ad***@test.com').length).toBeGreaterThanOrEqual(1);
    });
    fireEvent.click(screen.getByText('audit.filters'));
    expect(screen.getByText('audit.filter.actionType')).toBeInTheDocument();
    expect(screen.getByText('audit.filter.resourceType')).toBeInTheDocument();
  });

  it('shows pagination when there are results', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/audit.pagination.range/)).toBeInTheDocument();
    });
  });

  it('shows error state on query failure', async () => {
    mockAuditList.mockRejectedValue(new Error('Failed'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('audit.loadError')).toBeInTheDocument();
    });
  });

  it('opens detail modal on view click', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getAllByText('ad***@test.com').length).toBeGreaterThanOrEqual(1);
    });
    const viewButtons = screen.getAllByTitle('audit.viewDetails');
    fireEvent.click(viewButtons[0]);
    expect(screen.getByTestId('modal')).toBeInTheDocument();
  });

  it('shows resource name when present', async () => {
    renderPage();
    await waitFor(() => {
      // resource_type is 'user' so maskEmail('John Doe') → '***' (no @ sign)
      expect(screen.getAllByText('***').length).toBeGreaterThanOrEqual(1);
    });
  });
});
