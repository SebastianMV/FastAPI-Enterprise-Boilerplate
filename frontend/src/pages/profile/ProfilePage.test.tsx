import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProfilePage from './ProfilePage';

const mockUpdateMe = vi.fn();
const mockUploadAvatar = vi.fn();
const mockDeleteAvatar = vi.fn();
const mockApiPost = vi.fn();

vi.mock('@/services/api', () => ({
  usersService: {
    updateMe: (...args: unknown[]) => mockUpdateMe(...args),
    uploadAvatar: (...args: unknown[]) => mockUploadAvatar(...args),
    deleteAvatar: (...args: unknown[]) => mockDeleteAvatar(...args),
  },
  default: { post: (...args: unknown[]) => mockApiPost(...args) },
}));

const mockFetchUser = vi.fn();
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock partial user
let mockUser: any = {
  first_name: 'John',
  last_name: 'Doe',
  email: 'john@test.com',
  is_superuser: false,
  is_active: true,
  avatar_url: null,
  created_at: '2024-01-01T00:00:00Z',
  last_login: '2024-06-01T12:00:00Z',
};

vi.mock('@/stores/authStore', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock store selector
  useAuthStore: (selector?: (s: any) => any) => {
    const state = { user: mockUser, fetchUser: mockFetchUser };
    return selector ? selector(state) : state;
  },
}));

vi.mock('@/components/profile/ConnectedAccounts', () => ({
  default: () => <div data-testid="connected-accounts">Connected Accounts</div>,
}));

vi.mock('@/components/common/Modal', () => ({
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

function renderPage() {
  return render(
    <MemoryRouter>
      <ProfilePage />
    </MemoryRouter>,
  );
}

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchUser.mockResolvedValue(undefined);
    mockUser = {
      first_name: 'John',
      last_name: 'Doe',
      email: 'john@test.com',
      is_superuser: false,
      is_active: true,
      avatar_url: null,
      created_at: '2024-01-01T00:00:00Z',
      last_login: '2024-06-01T12:00:00Z',
    };
  });

  it('renders page title', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'profile.title' })).toBeInTheDocument();
  });

  it('displays user info in header card', () => {
    renderPage();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    // Email is masked in the Account Details sidebar (maskEmail: "jo***@test.com")
    expect(screen.getAllByText(/jo\*\*\*@test\.com/).length).toBeGreaterThanOrEqual(1);
  });

  it('shows user role badge', () => {
    renderPage();
    expect(screen.getByText('settings.user')).toBeInTheDocument();
  });

  it('shows admin badge for superuser', () => {
    mockUser = { ...mockUser, is_superuser: true };
    renderPage();
    expect(screen.getByText('settings.administrator')).toBeInTheDocument();
  });

  it('renders tabs for profile, security, connections', () => {
    renderPage();
    expect(screen.getByText('profile.tabs.profile')).toBeInTheDocument();
    expect(screen.getByText('profile.tabs.security')).toBeInTheDocument();
    expect(screen.getByText('profile.tabs.connections')).toBeInTheDocument();
  });

  it('shows profile edit form on profile tab', () => {
    renderPage();
    expect(screen.getByText('profile.editProfile')).toBeInTheDocument();
    expect(screen.getByText('users.firstName')).toBeInTheDocument();
    expect(screen.getByText('users.lastName')).toBeInTheDocument();
  });

  it('shows account details sidebar', () => {
    renderPage();
    expect(screen.getByText('profile.accountDetails')).toBeInTheDocument();
    expect(screen.getByText('profile.memberSince')).toBeInTheDocument();
    expect(screen.getByText('profile.lastLogin')).toBeInTheDocument();
  });

  it('switches to security tab', () => {
    renderPage();
    fireEvent.click(screen.getByText('profile.tabs.security'));
    expect(screen.getByText('profile.changePassword')).toBeInTheDocument();
  });

  it('switches to connections tab', () => {
    renderPage();
    fireEvent.click(screen.getByText('profile.tabs.connections'));
    expect(screen.getByTestId('connected-accounts')).toBeInTheDocument();
  });

  it('shows avatar with initials when no avatar_url', () => {
    renderPage();
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('shows avatar image when avatar_url is present', () => {
    mockUser = { ...mockUser, avatar_url: 'https://example.com/avatar.jpg' };
    renderPage();
    const img = screen.getByAltText('profile.avatarAlt');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'https://example.com/avatar.jpg');
  });

  it('shows MFA configuration link on profile tab', () => {
    renderPage();
    expect(screen.getByText('profile.configureMfa')).toBeInTheDocument();
  });
});
