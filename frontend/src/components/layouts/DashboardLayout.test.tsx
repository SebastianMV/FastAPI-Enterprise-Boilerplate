/**
 * Unit tests for DashboardLayout component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DashboardLayout from './DashboardLayout';

// Mock child components to keep tests focused
vi.mock('@/components/common/SearchBar', () => ({
  default: () => <div data-testid="search-bar">SearchBar</div>,
}));

vi.mock('@/components/notifications/NotificationsDropdown', () => ({
  default: () => <div data-testid="notifications-dropdown">Notifications</div>,
}));

vi.mock('@/components/common/EmailVerificationBanner', () => ({
  default: () => <div data-testid="email-banner">Email Banner</div>,
}));

// Mock stores
const mockUser = {
  id: '1',
  email: 'admin@example.com',
  first_name: 'Admin',
  last_name: 'User',
  is_superuser: true,
};

const mockLogout = vi.fn();
const mockFetchFeatures = vi.fn();

vi.mock('@/stores/authStore', () => ({
  useAuthStore: (selector?: (s: any) => any) => {
    const state = { user: mockUser, logout: mockLogout };
    return selector ? selector(state) : state;
  },
}));

vi.mock('@/stores/configStore', () => ({
  useConfigStore: (selector?: (s: any) => any) => {
    const state = { fetchFeatures: mockFetchFeatures };
    return selector ? selector(state) : state;
  },
}));

function renderLayout(route = '/dashboard') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <DashboardLayout />
    </MemoryRouter>
  );
}

describe('DashboardLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser.is_superuser = true;
  });

  it('should render sidebar with navigation', () => {
    renderLayout();
    expect(screen.getByText('navigation.dashboard')).toBeInTheDocument();
    expect(screen.getByText('navigation.users')).toBeInTheDocument();
    expect(screen.getByText('navigation.roles')).toBeInTheDocument();
    expect(screen.getByText('navigation.settings')).toBeInTheDocument();
  });

  it('should show admin nav items for superuser', () => {
    renderLayout();
    expect(screen.getByText('navigation.tenants')).toBeInTheDocument();
    expect(screen.getByText('navigation.dataExchange')).toBeInTheDocument();
  });

  it('should hide admin nav items for non-superuser', () => {
    mockUser.is_superuser = false;
    renderLayout();
    expect(screen.queryByText('navigation.tenants')).not.toBeInTheDocument();
    expect(screen.queryByText('navigation.dataExchange')).not.toBeInTheDocument();
  });

  it('should render user info in header', () => {
    renderLayout();
    expect(screen.getByText('A')).toBeInTheDocument(); // First letter of first_name
    expect(screen.getByText('Admin User')).toBeInTheDocument();
  });

  it('should render child components', () => {
    renderLayout();
    expect(screen.getByTestId('search-bar')).toBeInTheDocument();
    expect(screen.getByTestId('notifications-dropdown')).toBeInTheDocument();
    expect(screen.getByTestId('email-banner')).toBeInTheDocument();
  });

  it('should toggle user menu dropdown', () => {
    renderLayout();
    // Find and click the user menu button
    fireEvent.click(screen.getByText('Admin User'));
    expect(screen.getByText('userMenu.myProfile')).toBeInTheDocument();
    expect(screen.getByText('userMenu.languagePreferences')).toBeInTheDocument();
    expect(screen.getByText('userMenu.apiKeys')).toBeInTheDocument();
    expect(screen.getByText('userMenu.security')).toBeInTheDocument();
    expect(screen.getByText('common.signOut')).toBeInTheDocument();
  });

  it('should show user email in dropdown', () => {
    renderLayout();
    fireEvent.click(screen.getByText('Admin User'));
    expect(screen.getByText('admin@example.com')).toBeInTheDocument();
  });

  it('should call logout on sign out click', () => {
    renderLayout();
    fireEvent.click(screen.getByText('Admin User'));
    fireEvent.click(screen.getByText('common.signOut'));
    expect(mockLogout).toHaveBeenCalled();
  });

  it('should call fetchFeatures on mount', () => {
    renderLayout();
    expect(mockFetchFeatures).toHaveBeenCalled();
  });

  it('should render brand in sidebar', () => {
    renderLayout();
    expect(screen.getByText('common.brandName')).toBeInTheDocument();
  });
});
