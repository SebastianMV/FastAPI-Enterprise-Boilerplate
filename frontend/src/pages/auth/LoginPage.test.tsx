/**
 * Tests for LoginPage component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import LoginPage from './LoginPage';
import { useAuthStore } from '@/stores/authStore';

// Mock useAuthStore
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    login: vi.fn(),
    isLoading: false,
    error: null,
    clearError: vi.fn(),
    setError: vi.fn(),
  })),
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock SocialLoginButtons
vi.mock('@/components/auth/SocialLoginButtons', () => ({
  default: () => <div data-testid="social-login-buttons">Social Login</div>,
}));

const renderLoginPage = () => {
  return render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
  );
};

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset mock implementation
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      login: vi.fn(),
      isLoading: false,
      error: null,
      clearError: vi.fn(),
      setError: vi.fn(),
    });
  });

  describe('Rendering', () => {
    it('should render login form', () => {
      renderLoginPage();
      
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
      expect(screen.getByLabelText(/auth.emailAddress/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/auth.password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /auth.signIn/i })).toBeInTheDocument();
    });

    it('should render logo', () => {
      renderLoginPage();
      
      expect(screen.getByAltText('common.brandLogoAlt')).toBeInTheDocument();
    });

    it('should render forgot password link', () => {
      renderLoginPage();
      
      expect(screen.getByText(/auth.forgotPassword/i)).toBeInTheDocument();
    });

    it('should render register link', () => {
      renderLoginPage();
      
      expect(screen.getByText(/auth.signUp/i)).toBeInTheDocument();
    });

    it('should render social login buttons', () => {
      renderLoginPage();
      
      expect(screen.getByTestId('social-login-buttons')).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('should show error when form is submitted empty', async () => {
      renderLoginPage();
      
      const form = document.querySelector('form');
      expect(form).toBeInTheDocument();
      
      // Submit the form
      fireEvent.submit(form!);

      await waitFor(() => {
        // Check that validation error messages appear (react-hook-form renders them)
        const errorMessages = document.querySelectorAll('.text-red-600');
        expect(errorMessages.length).toBeGreaterThan(0);
      });
    });

    it('should show error for invalid email format', async () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/auth.emailAddress/i);
      await userEvent.type(emailInput, 'invalid-email');
      
      const form = document.querySelector('form');
      fireEvent.submit(form!);

      await waitFor(() => {
        // Check for email validation error
        const errorMessages = document.querySelectorAll('.text-red-600');
        expect(errorMessages.length).toBeGreaterThan(0);
      });
    });

    it('should show error when password is too short', async () => {
      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/auth.emailAddress/i);
      const passwordInput = screen.getByLabelText(/auth.password/i);
      
      await userEvent.type(emailInput, 'test@example.com');
      await userEvent.type(passwordInput, '123');
      
      const form = document.querySelector('form');
      fireEvent.submit(form!);

      await waitFor(() => {
        // Check for password validation error
        const errorMessages = document.querySelectorAll('.text-red-600');
        expect(errorMessages.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Form Submission', () => {
    it('should call login with credentials on valid submission', async () => {
      const mockLogin = vi.fn().mockResolvedValue({});
      (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        login: mockLogin,
        isLoading: false,
        error: null,
        clearError: vi.fn(),
        setError: vi.fn(),
      });

      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/auth.emailAddress/i);
      const passwordInput = screen.getByLabelText(/auth.password/i);
      
      await userEvent.type(emailInput, 'test@example.com');
      await userEvent.type(passwordInput, 'password123');
      
      const submitButton = screen.getByRole('button', { name: /auth.signIn/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
        });
      });
    });

    it('should navigate to dashboard on successful login', async () => {
      const mockLogin = vi.fn().mockResolvedValue({});
      (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        login: mockLogin,
        isLoading: false,
        error: null,
        clearError: vi.fn(),
        setError: vi.fn(),
      });

      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/auth.emailAddress/i);
      const passwordInput = screen.getByLabelText(/auth.password/i);
      
      await userEvent.type(emailInput, 'test@example.com');
      await userEvent.type(passwordInput, 'password123');
      
      const submitButton = screen.getByRole('button', { name: /auth.signIn/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
      });
    });

    it('should clear error before submission', async () => {
      const mockClearError = vi.fn();
      const mockLogin = vi.fn().mockResolvedValue({});
      
      (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        login: mockLogin,
        isLoading: false,
        error: null,
        clearError: mockClearError,
        setError: vi.fn(),
      });

      renderLoginPage();
      
      const emailInput = screen.getByLabelText(/auth.emailAddress/i);
      const passwordInput = screen.getByLabelText(/auth.password/i);
      
      await userEvent.type(emailInput, 'test@example.com');
      await userEvent.type(passwordInput, 'password123');
      
      const submitButton = screen.getByRole('button', { name: /auth.signIn/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockClearError).toHaveBeenCalled();
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner when isLoading is true', () => {
      (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        login: vi.fn(),
        isLoading: true,
        error: null,
        clearError: vi.fn(),
        setError: vi.fn(),
      });

      renderLoginPage();
      
      expect(screen.getByText(/common.loading/i)).toBeInTheDocument();
    });

    it('should disable submit button when loading', () => {
      (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        login: vi.fn(),
        isLoading: true,
        error: null,
        clearError: vi.fn(),
        setError: vi.fn(),
      });

      renderLoginPage();
      
      const submitButton = screen.getByRole('button', { name: /common.loading/i });
      expect(submitButton).toBeDisabled();
    });
  });

  describe('Error State', () => {
    it('should display error message when error exists', () => {
      (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
        login: vi.fn(),
        isLoading: false,
        error: 'Invalid credentials',
        clearError: vi.fn(),
        setError: vi.fn(),
      });

      renderLoginPage();
      
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  describe('Password Visibility Toggle', () => {
    it('should toggle password visibility when button is clicked', async () => {
      renderLoginPage();
      
      const passwordInput = screen.getByLabelText(/auth.password/i);
      expect(passwordInput).toHaveAttribute('type', 'password');

      const toggleButton = screen.getByRole('button', { name: /auth.showPassword/i });
      await userEvent.click(toggleButton);

      expect(passwordInput).toHaveAttribute('type', 'text');

      await userEvent.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });
});
