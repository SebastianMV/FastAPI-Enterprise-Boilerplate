/**
 * Unit tests for authStore (Zustand).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act } from '@testing-library/react';
import { useAuthStore } from './authStore';

// Mock the auth service
const mockLogin = vi.fn();
const mockLogout = vi.fn().mockResolvedValue(undefined);
const mockRefresh = vi.fn();
const mockMe = vi.fn();

vi.mock('@/services/api', () => ({
  authService: {
    login: (...args: unknown[]) => mockLogin(...args),
    logout: (...args: unknown[]) => mockLogout(...args),
    refresh: (...args: unknown[]) => mockRefresh(...args),
    me: (...args: unknown[]) => mockMe(...args),
  },
}));

describe('authStore', () => {
  const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    is_active: true,
    is_superuser: false,
    email_verified: true,
    mfa_enabled: false,
    created_at: '2024-01-01T00:00:00Z',
  };

  const mockLoginResponse = {
    access_token: 'access-token-123',
    refresh_token: 'refresh-token-456',
    token_type: 'bearer',
    user: mockUser,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset store state before each test
    const store = useAuthStore.getState();
    store.logout();
    
    // Clear mocked localStorage
    localStorage.clear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial state', () => {
    it('should have correct initial state', () => {
      const state = useAuthStore.getState();
      
      expect(state.user).toBeNull();
      expect(state.tokenExpiresAt).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('login', () => {
    it('should login successfully', async () => {
      mockLogin.mockResolvedValueOnce(mockLoginResponse);
      
      await act(async () => {
        await useAuthStore.getState().login({
          email: 'test@example.com',
          password: 'password123',
        });
      });
      
      const state = useAuthStore.getState();
      
      expect(state.user).toEqual(mockUser);
      // Raw JWT is no longer stored; only tokenExpiresAt is kept
      expect(state.tokenExpiresAt).toBeNull(); // mock token is not a real JWT
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should set loading state during login', async () => {
      let resolveLogin: (value: typeof mockLoginResponse) => void;
      mockLogin.mockReturnValueOnce(new Promise((resolve) => {
        resolveLogin = resolve;
      }));
      
      const loginPromise = useAuthStore.getState().login({
        email: 'test@example.com',
        password: 'password123',
      });
      
      // Check loading state
      expect(useAuthStore.getState().isLoading).toBe(true);
      
      // Resolve login
      await act(async () => {
        resolveLogin!(mockLoginResponse);
        await loginPromise;
      });
      
      expect(useAuthStore.getState().isLoading).toBe(false);
    });

    it('should handle login failure', async () => {
      mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));
      
      await expect(
        act(async () => {
          await useAuthStore.getState().login({
            email: 'wrong@example.com',
            password: 'wrongpassword',
          });
        })
      ).rejects.toThrow('Invalid credentials');
      
      const state = useAuthStore.getState();
      
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe('auth.loginFailed');
    });

    it('should clear previous error on new login attempt', async () => {
      // First, set an error
      useAuthStore.getState().setError('Previous error');
      
      mockLogin.mockResolvedValueOnce(mockLoginResponse);
      
      await act(async () => {
        await useAuthStore.getState().login({
          email: 'test@example.com',
          password: 'password123',
        });
      });
      
      expect(useAuthStore.getState().error).toBeNull();
    });
  });

  describe('logout', () => {
    it('should clear all auth state on logout', async () => {
      // First login
      mockLogin.mockResolvedValueOnce(mockLoginResponse);
      
      await act(async () => {
        await useAuthStore.getState().login({
          email: 'test@example.com',
          password: 'password123',
        });
      });
      
      // Verify logged in
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      
      // Logout
      mockLogout.mockResolvedValueOnce(undefined);
      
      act(() => {
        useAuthStore.getState().logout();
      });
      
      const state = useAuthStore.getState();
      
      expect(state.user).toBeNull();
      expect(state.tokenExpiresAt).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should call logout API when token exists', async () => {
      mockLogin.mockResolvedValueOnce(mockLoginResponse);
      mockLogout.mockResolvedValueOnce(undefined);
      
      await act(async () => {
        await useAuthStore.getState().login({
          email: 'test@example.com',
          password: 'password123',
        });
      });
      
      act(() => {
        useAuthStore.getState().logout();
      });
      
      expect(mockLogout).toHaveBeenCalled();
    });
  });

  describe('refreshAccessToken', () => {
    it('should refresh token successfully', async () => {
      // Setup initial authenticated state
      mockLogin.mockResolvedValueOnce(mockLoginResponse);
      
      await act(async () => {
        await useAuthStore.getState().login({
          email: 'test@example.com',
          password: 'password123',
        });
      });
      
      mockRefresh.mockResolvedValueOnce({
        access_token: 'new-access-token',
      });
      
      await act(async () => {
        await useAuthStore.getState().refreshAccessToken();
      });
      
      expect(useAuthStore.getState().tokenExpiresAt).toBeNull(); // mock token not a real JWT
    });

    it('should throw error when no refresh token', async () => {
      mockRefresh.mockRejectedValueOnce(new Error('Network error'));

      await expect(
        act(async () => {
          await useAuthStore.getState().refreshAccessToken();
        })
      ).rejects.toThrow('auth.sessionExpired');
    });

    it('should logout on refresh failure', async () => {
      // Setup initial state with tokens
      act(() => {
        useAuthStore.getState().setTokens('access-123');
      });
      
      mockRefresh.mockRejectedValueOnce(new Error('Token expired'));
      
      await expect(
        act(async () => {
          await useAuthStore.getState().refreshAccessToken();
        })
      ).rejects.toThrow('auth.sessionExpired');
      
      // Should be logged out
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
  });

  describe('setTokens', () => {
    it('should extract token expiry (null for non-JWT strings)', () => {
      act(() => {
        useAuthStore.getState().setTokens('new-access');
      });
      
      const state = useAuthStore.getState();
      
      // 'new-access' is not a valid JWT, so tokenExpiresAt will be null
      expect(state.tokenExpiresAt).toBeNull();
      // isAuthenticated is NOT set by setTokens — caller must fetchUser()
      expect(state.isAuthenticated).toBe(false);
    });

    it('should extract expiry from a valid JWT', () => {
      // Create a minimal valid JWT with exp = 1700000000 (2023-11-14)
      const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
      const payload = btoa(JSON.stringify({ sub: 'user-1', exp: 1700000000 }));
      const signature = 'fakesig';
      const jwt = `${header}.${payload}.${signature}`;

      act(() => {
        useAuthStore.getState().setTokens(jwt);
      });
      
      const state = useAuthStore.getState();
      expect(state.tokenExpiresAt).toBe(1700000000 * 1000);
    });
  });

  describe('fetchUser', () => {
    it('should fetch and set user', async () => {
      mockMe.mockResolvedValueOnce(mockUser);
      
      await act(async () => {
        await useAuthStore.getState().fetchUser();
      });
      
      expect(useAuthStore.getState().user).toEqual(mockUser);
    });

    it('should throw error on fetch failure', async () => {
      mockMe.mockRejectedValueOnce(new Error('Unauthorized'));
      
      await expect(
        act(async () => {
          await useAuthStore.getState().fetchUser();
        })
      ).rejects.toThrow('Unauthorized');
    });
  });

  describe('Error management', () => {
    it('should set error', () => {
      act(() => {
        useAuthStore.getState().setError('Test error');
      });
      
      expect(useAuthStore.getState().error).toBe('Test error');
    });

    it('should clear error', () => {
      act(() => {
        useAuthStore.getState().setError('Test error');
      });
      
      expect(useAuthStore.getState().error).toBe('Test error');
      
      act(() => {
        useAuthStore.getState().clearError();
      });
      
      expect(useAuthStore.getState().error).toBeNull();
    });
  });
});
