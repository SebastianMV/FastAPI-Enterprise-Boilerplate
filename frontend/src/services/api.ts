import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';

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
  skip: number;
  limit: number;
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
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? match.substring(match.indexOf('=') + 1) : null;
}

// =============================================================================
// Auth Event (SPA-friendly redirect without full page reload)
// =============================================================================

/** Dispatched when the user's session is no longer valid. */
export const AUTH_LOGOUT_EVENT = 'auth:logout';

function emitLogout(): void {
  window.dispatchEvent(new CustomEvent(AUTH_LOGOUT_EVENT));
}

// =============================================================================
// Axios Instance & Interceptors
// =============================================================================

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // Send HttpOnly cookies automatically
});

// Request interceptor to add CSRF header
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // HttpOnly cookies are sent automatically via withCredentials.
  // No need to read tokens from localStorage.

  // CSRF double-submit: read the non-HttpOnly csrf_token cookie and
  // echo it back as X-CSRF-Token header on every state-changing request.
  const csrfToken = getCookie('csrf_token');
  if (csrfToken) {
    config.headers['X-CSRF-Token'] = csrfToken;
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
      originalRequest._retry = true;
      
      try {
        // If a refresh is already in progress, wait for it instead of starting another
        if (!refreshPromise) {
          refreshPromise = (async () => {
            const refreshApi = axios.create({
              baseURL: import.meta.env.VITE_API_URL || '/',
              withCredentials: true,
            });
            await refreshApi.post<RefreshResponse>('/auth/refresh', {});
          })();
        }

        await refreshPromise;
        refreshPromise = null;
        
        // Retry the original request — the new cookie will be sent automatically.
        return api(originalRequest);
      } catch (refreshError) {
        refreshPromise = null;
        
        if (import.meta.env.DEV) {
          console.error('[API] Token refresh failed');
        }
        
        emitLogout();
        
        return Promise.reject(refreshError);
      }
    }
    
    // If 401 and already retried, redirect to login
    if (error.response?.status === 401) {
      emitLogout();
    }
    
    return Promise.reject(error);
  },
);

// =============================================================================
// Re-exports for backward compatibility
// All services have been moved to individual files under src/services/
// New code should import directly: import { authService } from '@/services/authService'
// =============================================================================

export { authService } from './authService';
export { usersService } from './usersService';
export { dashboardService } from './dashboardService';
export type { StatItem, ActivityItem, DashboardStats, RecentActivity, SystemHealth } from './dashboardService';
export { oauthService, OAUTH_PROVIDERS } from './oauthService';
export type { OAuthProvider, OAuthAuthorizeResponse, OAuthConnection } from './oauthService';
export { searchService } from './searchService';
export type { SearchFilter, SearchSort, SearchRequest, SearchHit, SearchResponse, SearchSuggestion } from './searchService';
export { notificationsService } from './notificationsService';
export type { Notification, NotificationsResponse } from './notificationsService';
export { configService } from './configService';
export type { FeatureConfig } from './configService';
export { sessionsService } from './sessionsService';
export type { UserSession, SessionListResponse, RevokeSessionsResponse } from './sessionsService';
export { emailVerificationService } from './emailVerificationService';
export type { VerificationStatus } from './emailVerificationService';
export { rolesService } from './rolesService';
export type { Role, RoleListResponse, CreateRoleData, UpdateRoleData, UserPermissions, AssignRoleRequest } from './rolesService';
export { auditLogsService } from './auditLogsService';
export type { AuditLog, AuditLogListResponse, AuditLogFilters } from './auditLogsService';
export { tenantsService } from './tenantsService';
export type { Tenant, TenantSettings, TenantListResponse, CreateTenantData, UpdateTenantData } from './tenantsService';
export { dataExchangeService } from './dataExchangeService';
export type { EntityField, Entity, ExportPreview, ImportResult, ReportFilter, ReportRequest } from './dataExchangeService';
export { mfaService } from './mfaService';
export type { MFAStatus, MFASetupResponse, EmailOTPResponse } from './mfaService';

export default api;
