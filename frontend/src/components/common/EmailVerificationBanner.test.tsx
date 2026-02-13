/**
 * Unit tests for EmailVerificationBanner component.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EmailVerificationBanner from './EmailVerificationBanner';

// Mock auth store
const mockUser = {
  id: '1',
  email: 'test@example.com',
  email_verified: false,
  first_name: 'Test',
};

vi.mock('@/stores/authStore', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- test mock store selector
  useAuthStore: (selector: (s: any) => any) => selector({ user: mockUser }),
}));

// Mock emailVerificationService
const mockSendVerification = vi.fn();

vi.mock('@/services/api', () => ({
  emailVerificationService: {
    sendVerification: () => mockSendVerification(),
  },
}));

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe('EmailVerificationBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser.email_verified = false;
  });

  it('should render banner when email is not verified', () => {
    render(<EmailVerificationBanner />, { wrapper: createWrapper() });
    expect(screen.getByText('profile.emailVerification.verifyYourEmail')).toBeInTheDocument();
    expect(screen.getByText('profile.emailVerification.resend')).toBeInTheDocument();
  });

  it('should not render when email is verified', () => {
    mockUser.email_verified = true;
    const { container } = render(<EmailVerificationBanner />, { wrapper: createWrapper() });
    expect(container.firstChild).toBeNull();
  });

  it('should dismiss banner on X click', () => {
    render(<EmailVerificationBanner />, { wrapper: createWrapper() });
    fireEvent.click(screen.getByLabelText('profile.emailVerification.dismiss'));
    expect(screen.queryByText('profile.emailVerification.verifyYourEmail')).not.toBeInTheDocument();
  });

  it('should show success message after resend', async () => {
    mockSendVerification.mockResolvedValueOnce({});
    render(<EmailVerificationBanner />, { wrapper: createWrapper() });
    fireEvent.click(screen.getByText('profile.emailVerification.resend'));
    await waitFor(() => {
      expect(screen.getByText('profile.emailVerification.emailSent')).toBeInTheDocument();
    });
  });
});
