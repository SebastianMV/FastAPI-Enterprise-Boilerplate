import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import RolesPage from './RolesPage';

const mockRolesList = vi.fn();
const mockRolesCreate = vi.fn();
const mockRolesUpdate = vi.fn();
const mockRolesDelete = vi.fn();

vi.mock('@/services/api', () => ({
  rolesService: {
    list: (...args: unknown[]) => mockRolesList(...args),
    create: (...args: unknown[]) => mockRolesCreate(...args),
    update: (...args: unknown[]) => mockRolesUpdate(...args),
    delete: (...args: unknown[]) => mockRolesDelete(...args),
  },
}));

vi.mock('@/components/common/Modal', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  Modal: ({ isOpen, children, title }: any) =>
    isOpen ? <div data-testid="modal"><h2>{title}</h2>{children}</div> : null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  ConfirmModal: ({ isOpen, onConfirm, title }: any) =>
    isOpen ? (
      <div data-testid="confirm-modal">
        <h2>{title}</h2>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  AlertModal: ({ isOpen, title, message }: any) =>
    isOpen ? <div data-testid="alert-modal"><h2>{title}</h2><p>{message}</p></div> : null,
}));

const mockRoles = {
  items: [
    {
      id: 'r1',
      name: 'Admin',
      description: 'Full access role',
      permissions: ['users:read', 'users:write', 'roles:read', 'roles:write', 'settings:read'],
      is_system: true,
    },
    {
      id: 'r2',
      name: 'Editor',
      description: 'Can edit content',
      permissions: ['posts:read', 'posts:update'],
      is_system: false,
    },
    {
      id: 'r3',
      name: 'Viewer',
      description: '',
      permissions: [],
      is_system: false,
    },
  ],
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RolesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('RolesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRolesList.mockResolvedValue(mockRoles);
  });

  it('renders page title', () => {
    renderPage();
    expect(screen.getByText('roles.title')).toBeInTheDocument();
  });

  it('shows loading spinner initially', () => {
    mockRolesList.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('displays roles after loading', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });
    expect(screen.getByText('Editor')).toBeInTheDocument();
    expect(screen.getByText('Viewer')).toBeInTheDocument();
  });

  it('shows system role badge', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('roles.systemRole')).toBeInTheDocument();
    });
  });

  it('shows permission count', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getAllByText('roles.permissionCount').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows permission tags limited to 4', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('users:read')).toBeInTheDocument();
    });
    // Admin has 5 permissions, should show +1 more
    expect(screen.getByText('+1 roles.more')).toBeInTheDocument();
  });

  it('filters roles by search', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('roles.searchPlaceholder');
    fireEvent.change(searchInput, { target: { value: 'Editor' } });
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
    expect(screen.getByText('Editor')).toBeInTheDocument();
  });

  it('opens create modal', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('roles.createRole'));
    expect(screen.getByTestId('modal')).toBeInTheDocument();
  });

  it('shows error state on query failure', async () => {
    mockRolesList.mockRejectedValue(new Error('Failed'));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('roles.loadError')).toBeInTheDocument();
    });
  });

  it('shows no description text for roles without description', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('roles.noDescription')).toBeInTheDocument();
    });
  });

  it('does not show edit/delete for system roles', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });
    // Editor should have action buttons, but not system role
    const editButtons = screen.getAllByTitle('roles.editRole');
    const deleteButtons = screen.getAllByTitle('roles.deleteRole');
    // Only non-system roles (Editor, Viewer) should have buttons
    expect(editButtons.length).toBe(2);
    expect(deleteButtons.length).toBe(2);
  });
});
