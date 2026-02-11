import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authService, type LoginCredentials, type User } from '@/services/api';
import { useNotificationsStore } from '@/stores/notificationsStore';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isInitializing: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  setTokens: (accessToken: string) => void;
  fetchUser: () => Promise<void>;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isInitializing: true,
      isLoading: false,
      error: null,

      login: async (credentials) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await authService.login(credentials);
          
          // Tokens are now stored in HttpOnly cookies by the backend.
          // We keep accessToken in memory (state) for Bearer header fallback,
          // but do NOT persist tokens to localStorage anymore.
          set({
            user: response.user,
            accessToken: response.access_token,
            isAuthenticated: true,
            isInitializing: false,
            isLoading: false,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: 'auth.loginFailed',
          });
          throw error;
        }
      },

      logout: () => {
        // Call backend to clear HttpOnly cookies and blacklist token
        authService.logout().catch(() => {});
        
        // Clear notification state so the next user starts fresh
        useNotificationsStore.getState().clearNotifications();
        
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshAccessToken: async () => {
        try {
          // Refresh token is sent automatically via HttpOnly cookie
          const response = await authService.refresh();
          
          set({
            accessToken: response.access_token,
          });
        } catch {
          // If refresh fails, logout
          get().logout();
          throw new Error('auth.sessionExpired');
        }
      },

      clearError: () => set({ error: null }),
      
      setError: (error) => set({ error }),
      
      setTokens: (accessToken) => {
        set({
          accessToken,
          isAuthenticated: true,
        });
      },
      
      fetchUser: async () => {
        try {
          const user = await authService.me();
          set({ user, isAuthenticated: true, isInitializing: false });
        } catch (error) {
          set({ isInitializing: false });
          throw error;
        }
      },
    }),
    {
      name: 'auth-storage',
      // Only persist minimal flags — NO tokens, NO user PII in localStorage.
      // isAuthenticated is derived from user presence after fetchUser().
      partialize: () => ({}),
    },
  ),
);
