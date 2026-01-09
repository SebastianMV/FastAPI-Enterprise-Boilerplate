import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authService, type LoginCredentials, type User } from '@/services/api';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
  setTokens: (accessToken: string, refreshToken?: string) => void;
  fetchUser: () => Promise<void>;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (credentials) => {
        set({ isLoading: true, error: null });
        
        try {
          const response = await authService.login(credentials);
          
          set({
            user: response.user,
            accessToken: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Login failed',
          });
          throw error;
        }
      },

      logout: () => {
        const { accessToken } = get();
        
        if (accessToken) {
          authService.logout().catch(console.error);
        }
        
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }
        
        try {
          const response = await authService.refresh(refreshToken);
          
          set({
            accessToken: response.access_token,
          });
        } catch {
          // If refresh fails, logout
          get().logout();
          throw new Error('Session expired');
        }
      },

      clearError: () => set({ error: null }),
      
      setError: (error) => set({ error }),
      
      setTokens: (accessToken, refreshToken) => {
        set({
          accessToken,
          ...(refreshToken && { refreshToken }),
          isAuthenticated: true,
        });
      },
      
      fetchUser: async () => {
        try {
          const user = await authService.me();
          set({ user });
        } catch (error) {
          console.error('Failed to fetch user:', error);
          throw error;
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
