import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";

// =============================================================================
// Base Types (shared across all services)
// =============================================================================

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  avatar_url?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  email_verified: boolean;
  created_at: string;
  last_login?: string;
  roles?: string[];
  tenant_id?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
  mfa_code?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// =============================================================================
// CSRF Helper
// =============================================================================

/**
 * Read a cookie value by name.
 * Used to extract the CSRF double-submit token set by the backend.
 */
function getCookie(name: string): string | null {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  if (!match) return null;
  try {
    return decodeURIComponent(match.substring(match.indexOf("=") + 1));
  } catch {
    return match.substring(match.indexOf("=") + 1);
  }
}

// =============================================================================
// Auth Event (SPA-friendly redirect without full page reload)
// =============================================================================

/** Dispatched when the user's session is no longer valid. */
export const AUTH_LOGOUT_EVENT = "auth:logout";

/** Auth endpoints that must NOT trigger the 401 refresh/logout cycle. */
const AUTH_BYPASS_URLS = [
  "/auth/logout",
  "/auth/refresh",
  "/auth/login",
  "/auth/me",
];

let _logoutEmitted = false;
function emitLogout(): void {
  if (_logoutEmitted) return;
  _logoutEmitted = true;
  window.dispatchEvent(new CustomEvent(AUTH_LOGOUT_EVENT));
  setTimeout(() => {
    _logoutEmitted = false;
  }, 2000);
}

// =============================================================================
// Axios Instance & Interceptors
// =============================================================================

const configuredBaseURL = import.meta.env.VITE_API_URL;
if (!configuredBaseURL && import.meta.env.PROD) {
  // Silently fail — VITE_API_URL not configured; baseURL will fall back to '/'
}

const api: AxiosInstance = axios.create({
  baseURL: configuredBaseURL || "/",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // Send HttpOnly cookies automatically
  timeout: 30000, // 30s timeout to prevent hanging requests
});

// Request interceptor to add CSRF header
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // HttpOnly cookies are sent automatically via withCredentials.
  // No need to read tokens from localStorage.

  // CSRF double-submit: read the non-HttpOnly csrf_token cookie and
  // echo it back as X-CSRF-Token header only on state-changing requests.
  const method = config.method?.toLowerCase();
  if (method && ["post", "put", "patch", "delete"].includes(method)) {
    const csrfToken = getCookie("csrf_token");
    if (csrfToken) {
      config.headers["X-CSRF-Token"] = csrfToken;
    }
  }

  return config;
});

// Shared refresh promise to prevent concurrent refresh calls (F-01)
let refreshPromise: Promise<void> | null = null;

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 errors (token expired)
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Never intercept auth endpoints — prevents infinite logout loop
      const url = originalRequest.url || "";
      if (AUTH_BYPASS_URLS.some((u) => url.includes(u))) {
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      try {
        // If a refresh is already in progress, wait for it instead of starting another
        if (!refreshPromise) {
          refreshPromise = (async () => {
            try {
              // Include CSRF header on the refresh request for consistency
              const csrfToken = getCookie("csrf_token");
              const headers: Record<string, string> = {};
              if (csrfToken) {
                headers["X-CSRF-Token"] = csrfToken;
              }
              const refreshApi = axios.create({
                baseURL: configuredBaseURL || "/",
                withCredentials: true,
                timeout: 15000,
              });
              await refreshApi.post<RefreshResponse>(
                "/auth/refresh",
                {},
                { headers },
              );
            } finally {
              // Clear the promise only inside the creator to avoid race conditions
              refreshPromise = null;
            }
          })();
        }

        await refreshPromise;

        // Retry the original request — the new cookie will be sent automatically.
        return api(originalRequest);
      } catch (refreshError) {
        // Ensure promise is cleared on error so future attempts can retry
        refreshPromise = null;

        if (import.meta.env.DEV) {
          // eslint-disable-next-line no-console -- development-only error logging
          console.error("[API] Token refresh failed");
        }

        emitLogout();

        return Promise.reject(refreshError);
      }
    }

    // If 401 and already retried, redirect to login (skip auth endpoints)
    if (error.response?.status === 401) {
      const url = originalRequest.url || "";
      if (!AUTH_BYPASS_URLS.some((u) => url.includes(u))) {
        emitLogout();
      }
    }

    return Promise.reject(error);
  },
);

// =============================================================================
// Re-exports for backward compatibility
// All services have been moved to individual files under src/services/
// New code should import directly: import { authService } from '@/services/authService'
// =============================================================================

export { auditLogsService } from "./auditLogsService";
export type {
  AuditLog,
  AuditLogFilters,
  AuditLogListResponse,
} from "./auditLogsService";
export { authService } from "./authService";
export { configService } from "./configService";
export type { FeatureConfig } from "./configService";
export { dashboardService } from "./dashboardService";
export type {
  ActivityItem,
  DashboardStats,
  RecentActivity,
  StatItem,
  SystemHealth,
} from "./dashboardService";
export { dataExchangeService } from "./dataExchangeService";
export type {
  Entity,
  EntityField,
  ExportPreview,
  ImportResult,
  ReportFilter,
  ReportRequest,
} from "./dataExchangeService";
export { emailVerificationService } from "./emailVerificationService";
export type { VerificationStatus } from "./emailVerificationService";
export { mfaService } from "./mfaService";
export type {
  EmailOTPResponse,
  MFASetupResponse,
  MFAStatus,
} from "./mfaService";
export { notificationsService } from "./notificationsService";
export type {
  Notification,
  NotificationsResponse,
} from "./notificationsService";
export { OAUTH_PROVIDERS, oauthService } from "./oauthService";
export type {
  OAuthAuthorizeResponse,
  OAuthConnection,
  OAuthProvider,
} from "./oauthService";
export { rolesService } from "./rolesService";
export type {
  AssignRoleRequest,
  CreateRoleData,
  Role,
  RoleListResponse,
  UpdateRoleData,
  UserPermissions,
} from "./rolesService";
export { searchService } from "./searchService";
export type {
  SearchFilter,
  SearchHit,
  SearchRequest,
  SearchResponse,
  SearchSort,
  SearchSuggestion,
} from "./searchService";
export { sessionsService } from "./sessionsService";
export type {
  RevokeSessionsResponse,
  SessionListResponse,
  UserSession,
} from "./sessionsService";
export { tenantsService } from "./tenantsService";
export type {
  CreateTenantData,
  Tenant,
  TenantListResponse,
  TenantSettings,
  UpdateTenantData,
} from "./tenantsService";
export { usersService } from "./usersService";

export default api;
