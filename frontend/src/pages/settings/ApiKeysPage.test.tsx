import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ApiKeysPage from './ApiKeysPage';

const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
const mockApiDelete = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
    delete: (...args: unknown[]) => mockApiDelete(...args),
  },
}));

vi.mock('@/components/common/Modal', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock component props
  Modal: ({ isOpen, onClose, title, children }: any) =>
    isOpen ? (
      <div data-testid="modal">
        <h2>{title}</h2>
        <button onClick={onClose} aria-label="Close">×</button>
        <div>{children}</div>
      </div>
    ) : null,
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

const mockApiKeys = {
  data: {
    items: [
      {
        id: 'k1',
        name: 'Production Key',
        prefix: 'sk_prod',
        scopes: ['users:read', 'users:write'],
        is_active: true,
        expires_at: '2025-12-31T00:00:00Z',
        last_used_at: '2024-06-01T12:00:00Z',
        usage_count: 42,
        created_at: '2024-01-01T00:00:00Z',
      },
      {
        id: 'k2',
        name: 'Revoked Key',
        prefix: 'sk_old',
        scopes: ['users:read'],
        is_active: false,
        expires_at: null,
        last_used_at: null,
        usage_count: 0,
        created_at: '2023-06-01T00:00:00Z',
      },
    ],
  },
};

function renderPage() {
  return render(
    <MemoryRouter>
      <ApiKeysPage />
    </MemoryRouter>,
  );
}

describe('ApiKeysPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiGet.mockImplementation(() => Promise.resolve(mockApiKeys));
  });

  async function renderAndWait() {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Production Key')).toBeInTheDocument();
    });
  }

  it('renders page title', async () => {
    await renderAndWait();
    expect(screen.getByText('apiKeys.title')).toBeInTheDocument();
  });

  it('loads and displays API keys', async () => {
    await renderAndWait();
    expect(screen.getByText('Revoked Key')).toBeInTheDocument();
  });

  it('shows revoked badge for inactive keys', async () => {
    await renderAndWait();
    expect(screen.getByText('apiKeys.revoked')).toBeInTheDocument();
  });

  it('shows scope badges', async () => {
    await renderAndWait();
    expect(screen.getAllByText('users:read').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('users:write')).toBeInTheDocument();
  });

  it('shows key prefix', async () => {
    await renderAndWait();
    expect(screen.getByText('sk_prod...')).toBeInTheDocument();
  });

  it('opens create modal on button click', async () => {
    await renderAndWait();
    const createButtons = screen.getAllByText('apiKeys.createKey');
    fireEvent.click(createButtons[0]);
    expect(screen.getByText('apiKeys.keyName')).toBeInTheDocument();
  });

  it('shows revoke button only for active keys', async () => {
    await renderAndWait();
    expect(screen.getByText('apiKeys.revoke')).toBeInTheDocument();
  });

  it('shows usage info', async () => {
    await renderAndWait();
    expect(screen.getByText('42 apiKeys.requests')).toBeInTheDocument();
  });

  it('shows help section', async () => {
    await renderAndWait();
    expect(screen.getByText('apiKeys.usingApiKeys')).toBeInTheDocument();
  });

  it('shows empty state when no keys', async () => {
    mockApiGet.mockImplementation(() => Promise.resolve({ data: { items: [] } }));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('apiKeys.noKeysTitle')).toBeInTheDocument();
    });
  });

  it('shows error message on load failure', async () => {
    mockApiGet.mockImplementation(() => Promise.reject(new Error('Network error')));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('apiKeys.loadError')).toBeInTheDocument();
    });
  });

  it('has show revoked keys checkbox', async () => {
    await renderAndWait();
    expect(screen.getByText('apiKeys.showRevokedKeys')).toBeInTheDocument();
  });
});
