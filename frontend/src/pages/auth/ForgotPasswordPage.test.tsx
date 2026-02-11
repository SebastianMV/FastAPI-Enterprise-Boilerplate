/**
 * Unit tests for ForgotPasswordPage component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ForgotPasswordPage from './ForgotPasswordPage';

// Mock api module
const mockPost = vi.fn();
vi.mock('@/services/api', () => ({
  default: {
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <ForgotPasswordPage />
    </MemoryRouter>
  );
}

describe('ForgotPasswordPage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should render the forgot password form', () => {
    renderPage();
    expect(screen.getByText('auth.forgotPasswordTitle')).toBeInTheDocument();
    expect(screen.getByText('auth.forgotPasswordDescription')).toBeInTheDocument();
    expect(screen.getByLabelText('auth.emailAddress')).toBeInTheDocument();
  });

  it('should have back to login link', () => {
    renderPage();
    const links = screen.getAllByText('auth.signIn');
    expect(links.length).toBeGreaterThan(0);
  });

  it('should show success state after submission', async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    renderPage();

    fireEvent.change(screen.getByLabelText('auth.emailAddress'), {
      target: { value: 'test@example.com' },
    });
    fireEvent.click(screen.getByText('auth.sendResetLink'));

    await waitFor(() => {
      expect(screen.getByText('auth.resetLinkSent')).toBeInTheDocument();
      expect(screen.getByText('auth.checkEmailReset')).toBeInTheDocument();
    });
  });

  it('should show success even on 404 (prevent email enumeration)', async () => {
    mockPost.mockRejectedValueOnce({ response: { status: 404 } });
    renderPage();

    fireEvent.change(screen.getByLabelText('auth.emailAddress'), {
      target: { value: 'notfound@example.com' },
    });
    fireEvent.click(screen.getByText('auth.sendResetLink'));

    await waitFor(() => {
      expect(screen.getByText('auth.resetLinkSent')).toBeInTheDocument();
    });
  });

  it('should show success on network error (security)', async () => {
    mockPost.mockRejectedValueOnce(new Error('Network error'));
    renderPage();

    fireEvent.change(screen.getByLabelText('auth.emailAddress'), {
      target: { value: 'test@example.com' },
    });
    fireEvent.click(screen.getByText('auth.sendResetLink'));

    await waitFor(() => {
      expect(screen.getByText('auth.resetLinkSent')).toBeInTheDocument();
    });
  });

  it('should allow trying another email after success', async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    renderPage();

    fireEvent.change(screen.getByLabelText('auth.emailAddress'), {
      target: { value: 'test@example.com' },
    });
    fireEvent.click(screen.getByText('auth.sendResetLink'));

    await waitFor(() => {
      expect(screen.getByText('auth.tryAnotherEmail')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('auth.tryAnotherEmail'));
    expect(screen.getByText('auth.forgotPasswordTitle')).toBeInTheDocument();
  });
});
