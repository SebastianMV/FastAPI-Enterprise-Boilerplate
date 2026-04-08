import { authService, type LoginCredentials, type User } from "@/services/api";
import { useNotificationsStore } from "@/stores/notificationsStore";
import { safeDecodeJwtPayload } from "@/utils/security";
import { create } from "zustand";

/**
 * Extract the expiration timestamp from a JWT without storing the raw token.
 * Returns epoch milliseconds, or null if extraction fails.
 */
function extractTokenExpiry(token: string): number | null {
  const payload = safeDecodeJwtPayload(token);
  if (payload && typeof payload.exp === "number") {
    return payload.exp * 1000; // Convert seconds → ms
  }
  return null;
}

interface AuthState {
  user: User | null;
  /** Opaque expiry timestamp (ms) — raw JWT is never stored in JS-reachable state */
  tokenExpiresAt: number | null;
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

export const useAuthStore = create<AuthState>()((set, get) => ({
  user: null,
  tokenExpiresAt: null,
  isAuthenticated: false,
  isInitializing: true,
  isLoading: false,
  error: null,

  login: async (credentials) => {
    set({ isLoading: true, error: null });

    try {
      const response = await authService.login(credentials);

      // Tokens are stored in HttpOnly cookies by the backend.
      // We extract only the expiry timestamp — the raw JWT is NEVER
      // stored in JS-reachable state to prevent XSS exfiltration.
      set({
        tokenExpiresAt: extractTokenExpiry(response.access_token),
        isAuthenticated: true,
        isInitializing: false,
        isLoading: false,
      });

      // Fetch full user profile now that session cookies are set.
      // The login response only contains tokens, not the user object.
      await get().fetchUser();
    } catch (error) {
      set({
        isLoading: false,
        error: "auth.loginFailed",
      });
      throw error;
    }
  },

  logout: () => {
    // Clear client state immediately for responsive UX
    useNotificationsStore.getState().clearNotifications();
    set({
      user: null,
      tokenExpiresAt: null,
      isAuthenticated: false,
      error: null,
    });

    // Attempt server-side session invalidation with timeout.
    // Retry once on failure to maximize chance of cookie invalidation.
    const logoutWithTimeout = () =>
      Promise.race([
        authService.logout(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("timeout")), 5000),
        ),
      ]);

    logoutWithTimeout().catch(() => {
      // Retry once
      logoutWithTimeout().catch(() => {
        // Server-side invalidation failed — HttpOnly cookie may remain valid
        // until it expires naturally. This is logged for observability but
        // client state is already cleared above.
      });
    });
  },

  refreshAccessToken: async () => {
    try {
      // Refresh token is sent automatically via HttpOnly cookie
      const response = await authService.refresh();

      set({
        tokenExpiresAt: extractTokenExpiry(response.access_token),
      });
    } catch {
      // If refresh fails, logout
      get().logout();
      throw new Error("auth.sessionExpired");
    }
  },

  clearError: () => set({ error: null }),

  setError: (error) => set({ error }),

  setTokens: (accessToken) => {
    // Extract only the expiry timestamp — discard the raw JWT.
    // isAuthenticated is NOT set here — callers must also
    // fetchUser() to confirm validity.
    set({
      tokenExpiresAt: extractTokenExpiry(accessToken),
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
}));
