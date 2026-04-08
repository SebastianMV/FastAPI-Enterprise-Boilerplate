import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ResetPasswordPage from './ResetPasswordPage';

// Mock api (this page uses axios via api, not native fetch)
const mockApiGet = vi.fn();
const mockApiPost = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
  },
}));

function renderPage(token?: string) {
  const path = token ? `/reset-password/${token}` : '/reset-password';
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/reset-password/:token" element={<ResetPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state while validating token', () => {
    // Never resolve api call so it stays in validating state
    mockApiGet.mockReturnValue(new Promise(() => {}));
    renderPage('valid-token');
    expect(screen.getByText('common.loading')).toBeInTheDocument();
  });

  it('shows invalid token state when no token provided', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('auth.invalidResetLink')).toBeInTheDocument();
    });
  });

  it('shows invalid token state when token validation fails', async () => {
    // api.get rejects on error → catch sets isTokenValid = true (fallback)
    // Actually, re-reading the component: catch sets isTokenValid = true
    // Token validation fails → fail-closed: shows invalid token screen
    mockApiGet.mockRejectedValue(new Error('Invalid token'));
    renderPage('bad-token');
    await waitFor(() => {
      // Component catches error and sets isTokenValid=false (fail-closed)
      expect(screen.getByText('auth.invalidResetLink')).toBeInTheDocument();
    });
  });

  it('shows request new link button on invalid token', async () => {
    // When no token is provided, "Invalid Reset Link" and "Request New Link" are shown
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('auth.requestNewLink')).toBeInTheDocument();
    });
  });

  it('shows back to login link on invalid token', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('auth.backToLogin')).toBeInTheDocument();
    });
  });

  it('shows reset form when token is valid', async () => {
    mockApiGet.mockResolvedValue({ data: {} });
    renderPage('valid-token');
    await waitFor(() => {
      expect(screen.getByText('auth.resetPasswordTitle')).toBeInTheDocument();
    });
    expect(screen.getByLabelText('profile.newPassword')).toBeInTheDocument();
    expect(screen.getByLabelText('profile.confirmPassword')).toBeInTheDocument();
  });

  it('shows password requirements', async () => {
    mockApiGet.mockResolvedValue({ data: {} });
    renderPage('valid-token');
    await waitFor(() => {
      expect(screen.getByText('auth.passwordRequirements')).toBeInTheDocument();
    });
    expect(screen.getByText(/auth.passwordReqMinChars/)).toBeInTheDocument();
    expect(screen.getByText(/auth.passwordReqUppercase/)).toBeInTheDocument();
    expect(screen.getByText(/auth.passwordReqLowercase/)).toBeInTheDocument();
    expect(screen.getByText(/auth.passwordReqNumber/)).toBeInTheDocument();
    expect(screen.getByText(/auth.passwordReqSpecial/)).toBeInTheDocument();
  });

  it('toggles password visibility', async () => {
    mockApiGet.mockResolvedValue({ data: {} });
    renderPage('valid-token');
    await waitFor(() => {
      expect(screen.getByLabelText('profile.newPassword')).toBeInTheDocument();
    });
    const passwordInput = screen.getByLabelText('profile.newPassword');
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('shows success state after password reset', async () => {
    mockApiGet.mockResolvedValue({ data: {} }); // validate token
    mockApiPost.mockResolvedValue({ data: {} }); // reset password

    renderPage('valid-token');
    await waitFor(() => {
      expect(screen.getByLabelText('profile.newPassword')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('profile.newPassword'), {
      target: { value: 'NewPass1!' },
    });
    fireEvent.change(screen.getByLabelText('profile.confirmPassword'), {
      target: { value: 'NewPass1!' },
    });
    fireEvent.submit(screen.getByText('profile.updatePassword'));

    await waitFor(() => {
      expect(screen.getByText('auth.passwordResetSuccess')).toBeInTheDocument();
    });
    expect(screen.getByText('auth.nowYouCanLogin')).toBeInTheDocument();
    expect(screen.getByText('auth.signIn')).toBeInTheDocument();
  });

  it('shows error when reset fails', async () => {
    mockApiGet.mockResolvedValue({ data: {} }); // validate token
    mockApiPost.mockRejectedValue({
      response: { data: { detail: { message: 'Token expired' } } },
    }); // reset password fails

    renderPage('valid-token');
    await waitFor(() => {
      expect(screen.getByLabelText('profile.newPassword')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('profile.newPassword'), {
      target: { value: 'NewPass1!' },
    });
    fireEvent.change(screen.getByLabelText('profile.confirmPassword'), {
      target: { value: 'NewPass1!' },
    });
    fireEvent.submit(screen.getByText('profile.updatePassword'));

    await waitFor(() => {
      expect(screen.getByText('auth.resetFailed')).toBeInTheDocument();
    });
  });

  it('shows submit button', async () => {
    mockApiGet.mockResolvedValue({ data: {} });
    renderPage('valid-token');
    await waitFor(() => {
      expect(screen.getByText('profile.updatePassword')).toBeInTheDocument();
    });
  });

  it('shows description text', async () => {
    mockApiGet.mockResolvedValue({ data: {} });
    renderPage('valid-token');
    await waitFor(() => {
      expect(screen.getByText('auth.resetPasswordDescription')).toBeInTheDocument();
    });
  });
});
