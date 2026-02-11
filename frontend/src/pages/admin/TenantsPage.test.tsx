import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import TenantsPage from './TenantsPage';

// Mock services
const mockList = vi.fn();
const mockCreate = vi.fn();
const mockUpdate = vi.fn();
const mockDelete = vi.fn();
const mockActivate = vi.fn();
const mockDeactivate = vi.fn();

vi.mock('@/services/api', () => ({
  tenantsService: {
    list: (...args: unknown[]) => mockList(...args),
    create: (...args: unknown[]) => mockCreate(...args),
    update: (...args: unknown[]) => mockUpdate(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
    activate: (...args: unknown[]) => mockActivate(...args),
    deactivate: (...args: unknown[]) => mockDeactivate(...args),
  },
}));

// Mock auth store
let mockUser = { is_superuser: true, first_name: 'Admin', last_name: 'User', email: 'admin@test.com' };

vi.mock('@/stores/authStore', () => ({
  useAuthStore: (selector?: (s: any) => any) => {
    const state = { user: mockUser };
    return selector ? selector(state) : state;
  },
}));

// Mock Modal components
vi.mock('@/components/common/Modal', () => ({
  Modal: ({ isOpen, children, title }: any) =>
    isOpen ? <div data-testid="modal"><h2>{title}</h2>{children}</div> : null,
  ConfirmModal: ({ isOpen, onConfirm, title, message }: any) =>
    isOpen ? (
      <div data-testid="confirm-modal">
        <h2>{title}</h2>
        <p>{message}</p>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null,
  AlertModal: ({ isOpen, title, message }: any) =>
    isOpen ? <div data-testid="alert-modal"><h2>{title}</h2><p>{message}</p></div> : null,
}));

const mockTenants = {
  items: [
    {
      id: '1',
      name: 'Acme Corp',
      slug: 'acme-corp',
      email: 'admin@acme.com',
      phone: null,
      domain: 'acme.com',
      timezone: 'UTC',
      locale: 'en',
      plan: 'professional',
      is_active: true,
      is_verified: true,
      created_at: '2024-01-15T00:00:00Z',
      settings: {
        max_users: 50,
        enable_2fa: true,
        enable_api_keys: true,
        enable_webhooks: false,
        max_api_keys_per_user: 5,
        max_storage_mb: 1024,
        password_min_length: 8,
        session_timeout_minutes: 30,
        require_email_verification: true,
        primary_color: '#3B82F6',
      },
    },
    {
      id: '2',
      name: 'Beta Inc',
      slug: 'beta-inc',
      email: null,
      phone: null,
      domain: null,
      timezone: 'UTC',
      locale: 'es',
      plan: 'free',
      is_active: false,
      is_verified: false,
      created_at: '2024-02-01T00:00:00Z',
      settings: {
        max_users: 5,
        enable_2fa: false,
        enable_api_keys: false,
        enable_webhooks: false,
        max_api_keys_per_user: 2,
        max_storage_mb: 256,
        password_min_length: 8,
        session_timeout_minutes: 30,
        require_email_verification: false,
        primary_color: '#3B82F6',
      },
    },
  ],
  total: 2,
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TenantsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('TenantsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = { is_superuser: true, first_name: 'Admin', last_name: 'User', email: 'admin@test.com' };
    mockList.mockResolvedValue(mockTenants);
  });

  it('renders access denied for non-superuser', () => {
    mockUser = { is_superuser: false, first_name: 'Normal', last_name: 'User', email: 'user@test.com' };
    renderPage();
    expect(screen.getByText('tenants.accessDenied')).toBeInTheDocument();
  });

  it('renders page title for superuser', async () => {
    renderPage();
    expect(screen.getByText('tenants.title')).toBeInTheDocument();
  });

  it('displays tenants after loading', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    expect(screen.getByText('Beta Inc')).toBeInTheDocument();
  });

  it('filters tenants by search', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('tenants.searchPlaceholder');
    fireEvent.change(searchInput, { target: { value: 'Beta' } });
    expect(screen.queryByText('Acme Corp')).not.toBeInTheDocument();
    expect(screen.getByText('Beta Inc')).toBeInTheDocument();
  });

  it('opens create modal on button click', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('tenants.createTenant'));
    expect(screen.getByTestId('modal')).toBeInTheDocument();
  });

  it('shows active/inactive status badges', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    const activeBadges = screen.getAllByText('tenants.active');
    const inactiveBadges = screen.getAllByText('tenants.inactive');
    expect(activeBadges.length).toBeGreaterThanOrEqual(1);
    expect(inactiveBadges.length).toBeGreaterThanOrEqual(1);
  });

  it('shows plan badges', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('tenants.plans.professional')).toBeInTheDocument();
    });
    expect(screen.getByText('tenants.plans.free')).toBeInTheDocument();
  });

  it('shows error state when query fails', async () => {
    mockList.mockRejectedValue(new Error('Network error'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('tenants.loadError')).toBeInTheDocument();
    });
  });

  it('shows empty state when no tenants match search', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('tenants.searchPlaceholder');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });
    expect(screen.getByText('tenants.noTenantsFound')).toBeInTheDocument();
  });

  it('displays tenant email and domain when present', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('admin@acme.com')).toBeInTheDocument();
    });
    expect(screen.getByText('acme.com')).toBeInTheDocument();
  });

  it('changes status filter', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
    const select = screen.getByDisplayValue('tenants.allStatus');
    fireEvent.change(select, { target: { value: 'active' } });
    expect(mockList).toHaveBeenCalledWith(expect.objectContaining({ is_active: true }));
  });
});
