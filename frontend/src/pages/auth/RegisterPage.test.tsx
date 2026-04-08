/**
 * Unit tests for RegisterPage component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RegisterPage from './RegisterPage';

// Mock api
const mockPost = vi.fn();
vi.mock('@/services/api', () => ({
  default: {
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <RegisterPage />
    </MemoryRouter>
  );
}

describe('RegisterPage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should render registration form', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'auth.createAccount' })).toBeInTheDocument();
    expect(screen.getByLabelText('auth.firstName')).toBeInTheDocument();
    expect(screen.getByLabelText('auth.lastName')).toBeInTheDocument();
    expect(screen.getByLabelText('auth.emailAddress')).toBeInTheDocument();
    expect(screen.getByLabelText('auth.password')).toBeInTheDocument();
    expect(screen.getByLabelText('profile.confirmPassword')).toBeInTheDocument();
  });

  it('should show password requirements section', () => {
    renderPage();
    expect(screen.getByText('auth.passwordRequirements')).toBeInTheDocument();
    expect(screen.getByText(/auth.passwordReqMinChars/)).toBeInTheDocument();
    expect(screen.getByText(/auth.passwordReqUppercase/)).toBeInTheDocument();
  });

  it('should have sign in link', () => {
    renderPage();
    expect(screen.getByText('auth.signIn')).toBeInTheDocument();
  });

  it('should toggle password visibility', () => {
    renderPage();
    const passwordInput = screen.getByLabelText('auth.password');
    expect(passwordInput).toHaveAttribute('type', 'password');
    
    // Find the toggle button by aria-label
    const toggleButtons = screen.getAllByRole('button', { name: 'auth.showPassword' });
    // Click first toggle (password field)
    fireEvent.click(toggleButtons[0]);
    expect(passwordInput).toHaveAttribute('type', 'text');
  });

  it('should show success state after registration', async () => {
    mockPost.mockResolvedValueOnce({ data: {} });
    renderPage();

    fireEvent.change(screen.getByLabelText('auth.firstName'), { target: { value: 'John' } });
    fireEvent.change(screen.getByLabelText('auth.lastName'), { target: { value: 'Doe' } });
    fireEvent.change(screen.getByLabelText('auth.emailAddress'), { target: { value: 'john@test.com' } });
    fireEvent.change(screen.getByLabelText('auth.password'), { target: { value: 'Test123!@' } });
    fireEvent.change(screen.getByLabelText('profile.confirmPassword'), { target: { value: 'Test123!@' } });

    const submitButtons = screen.getAllByText('auth.createAccount');
    fireEvent.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(screen.getByText('auth.loginSuccess')).toBeInTheDocument();
    });
  });

  it('should show error message on registration failure', async () => {
    mockPost.mockRejectedValueOnce({
      response: { data: { detail: { message: 'Email already exists' } } },
    });
    renderPage();

    fireEvent.change(screen.getByLabelText('auth.firstName'), { target: { value: 'John' } });
    fireEvent.change(screen.getByLabelText('auth.lastName'), { target: { value: 'Doe' } });
    fireEvent.change(screen.getByLabelText('auth.emailAddress'), { target: { value: 'john@test.com' } });
    fireEvent.change(screen.getByLabelText('auth.password'), { target: { value: 'Test123!@' } });
    fireEvent.change(screen.getByLabelText('profile.confirmPassword'), { target: { value: 'Test123!@' } });

    const submitButtons = screen.getAllByText('auth.createAccount');
    fireEvent.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() => {
      expect(screen.getByText('auth.registrationFailed')).toBeInTheDocument();
    });
  });
});
