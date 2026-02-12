import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import UsersPage from './UsersPage';

const mockUsersList = vi.fn();
const mockUsersCreate = vi.fn();
const mockUsersUpdate = vi.fn();
const mockUsersDelete = vi.fn();
const mockRolesList = vi.fn();

vi.mock('@/services/api', () => ({
  usersService: {
    list: (...args: unknown[]) => mockUsersList(...args),
    create: (...args: unknown[]) => mockUsersCreate(...args),
    update: (...args: unknown[]) => mockUsersUpdate(...args),
    delete: (...args: unknown[]) => mockUsersDelete(...args),
  },
  rolesService: {
    list: (...args: unknown[]) => mockRolesList(...args),
  },
}));

vi.mock('@/components/common/Modal', () => ({
  Modal: ({ isOpen, children, title }: any) =>
    isOpen ? <div data-testid="modal"><h2>{title}</h2>{children}</div> : null,
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

const mockUsers = {
  items: [
    {
      id: 'u1',
      email: 'john@test.com',
      first_name: 'John',
      last_name: 'Doe',
      is_active: true,
      is_superuser: false,
      roles: ['r1'],
      created_at: '2024-01-15T00:00:00Z',
    },
    {
      id: 'u2',
      email: 'admin@test.com',
      first_name: 'Admin',
      last_name: 'User',
      is_active: true,
      is_superuser: true,
      roles: [],
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'u3',
      email: 'inactive@test.com',
      first_name: 'Inactive',
      last_name: 'User',
      is_active: false,
      is_superuser: false,
      roles: [],
      created_at: '2024-03-01T00:00:00Z',
    },
  ],
  total: 3,
};

const mockRoles = {
  items: [
    { id: 'r1', name: 'Editor', description: 'Can edit', permissions: [], is_system: false },
  ],
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('UsersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsersList.mockResolvedValue(mockUsers);
    mockRolesList.mockResolvedValue(mockRoles);
  });

  it('renders page title', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'users.title' })).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    mockUsersList.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    // Loader2 icon is present via animate-spin class
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('displays users after loading', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('john@test.com')).toBeInTheDocument();
    });
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Admin User')).toBeInTheDocument();
  });

  it('shows active/inactive status', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('john@test.com')).toBeInTheDocument();
    });
    const activeLabels = screen.getAllByText('users.active');
    const inactiveLabels = screen.getAllByText('users.inactive');
    expect(activeLabels.length).toBeGreaterThanOrEqual(1);
    expect(inactiveLabels.length).toBeGreaterThanOrEqual(1);
  });

  it('filters users by search', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('john@test.com')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('users.searchPlaceholder');
    fireEvent.change(searchInput, { target: { value: 'admin' } });
    expect(screen.queryByText('john@test.com')).not.toBeInTheDocument();
    expect(screen.getByText('admin@test.com')).toBeInTheDocument();
  });

  it('shows role badges from role data', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Editor')).toBeInTheDocument();
    });
  });

  it('shows administrator badge for superuser', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('settings.administrator')).toBeInTheDocument();
    });
  });

  it('opens create modal', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('john@test.com')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('users.addUser'));
    expect(screen.getByTestId('modal')).toBeInTheDocument();
  });

  it('shows error state when query fails', async () => {
    mockUsersList.mockRejectedValue(new Error('Failed'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('users.loadError')).toBeInTheDocument();
    });
  });

  it('shows pagination info', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/users\.showingCount/)).toBeInTheDocument();
    });
  });

  it('shows no users found for empty search', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('john@test.com')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('users.searchPlaceholder');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });
    expect(screen.getByText('users.noUsersFound')).toBeInTheDocument();
  });
});
