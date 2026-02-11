import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import VerifyEmailPage from './VerifyEmailPage';

const mockVerifyEmail = vi.fn();

vi.mock('@/services/api', () => ({
  emailVerificationService: {
    verifyEmail: (...args: unknown[]) => mockVerifyEmail(...args),
  },
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderPage(token?: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const path = token ? `/?token=${token}` : '/';
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <VerifyEmailPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('VerifyEmailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state when token is present', () => {
    mockVerifyEmail.mockReturnValue(new Promise(() => {}));
    renderPage('valid-token');
    expect(screen.getByText('auth.verifyEmail')).toBeInTheDocument();
    expect(screen.getByText('auth.verifyEmailDescription')).toBeInTheDocument();
  });

  it('shows no-token state when no token provided', () => {
    renderPage();
    expect(screen.getByText('auth.noTokenProvided')).toBeInTheDocument();
    expect(screen.getByText('auth.noTokenMessage')).toBeInTheDocument();
  });

  it('shows success state on successful verification', async () => {
    mockVerifyEmail.mockResolvedValue({ message: 'Email verified successfully' });
    renderPage('valid-token');
    await waitFor(() => {
      expect(screen.getByText('auth.emailVerified')).toBeInTheDocument();
    });
    expect(screen.getByText('auth.emailVerifiedSuccess')).toBeInTheDocument();
    expect(screen.getByText('auth.goToDashboard')).toBeInTheDocument();
  });

  it('shows error state on verification failure', async () => {
    mockVerifyEmail.mockRejectedValue({
      message: 'Token expired',
      response: { data: { detail: { message: 'Token expired' } } },
    });
    renderPage('invalid-token');
    await waitFor(() => {
      expect(screen.getByText('auth.verificationFailed')).toBeInTheDocument();
    });
    expect(screen.getByText('auth.verificationError')).toBeInTheDocument();
  });

  it('calls verifyEmail with correct token', async () => {
    mockVerifyEmail.mockResolvedValue({ message: 'OK' });
    renderPage('my-token-123');
    await waitFor(() => {
      expect(mockVerifyEmail).toHaveBeenCalledWith('my-token-123');
    });
  });

  it('shows resend verification link on error', async () => {
    mockVerifyEmail.mockRejectedValue(new Error('Failed'));
    renderPage('bad-token');
    await waitFor(() => {
      expect(screen.getByText('auth.resendVerification')).toBeInTheDocument();
    });
  });

  it('shows go to dashboard link on no-token', () => {
    renderPage();
    expect(screen.getByText('auth.goToDashboard')).toBeInTheDocument();
  });

  it('shows go to dashboard button on success', async () => {
    mockVerifyEmail.mockResolvedValue({ message: 'Done' });
    renderPage('token');
    await waitFor(() => {
      expect(screen.getByText('auth.goToDashboard')).toBeInTheDocument();
    });
  });
});
