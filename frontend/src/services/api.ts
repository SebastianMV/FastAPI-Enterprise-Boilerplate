import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';

// Types
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
}

export interface LoginCredentials {
  email: string;
  password: string;
  mfa_code?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
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

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const authStorage = localStorage.getItem('auth-storage');
  
  if (authStorage) {
    try {
      const { state } = JSON.parse(authStorage);
      if (state?.accessToken) {
        config.headers.Authorization = `Bearer ${state.accessToken}`;
      }
    } catch {
      // Ignore parsing errors
    }
  }
  
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Handle 401 errors (token expired)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const authStorage = localStorage.getItem('auth-storage');
      
      if (authStorage) {
        try {
          const { state } = JSON.parse(authStorage);
          
          if (state?.refreshToken) {
            // Use axios.create to avoid interceptor loop
            const refreshApi = axios.create({
              baseURL: import.meta.env.VITE_API_URL || '/',
            });
            
            const refreshResponse = await refreshApi.post<RefreshResponse>('/auth/refresh', {
              refresh_token: state.refreshToken,
            });
            
            const newAccessToken = refreshResponse.data.access_token;
            
            // Update stored token
            const newState = {
              ...state,
              accessToken: newAccessToken,
            };
            
            localStorage.setItem('auth-storage', JSON.stringify({
              state: newState,
              version: 0,
            }));
            
            // Retry original request with new token
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          // Refresh failed, clear storage and redirect to login
          console.error('[API] Token refresh failed:', refreshError);
          localStorage.removeItem('auth-storage');
          
          // Only redirect if not already on login page
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          
          return Promise.reject(refreshError);
        }
      }
      
      // No refresh token available, redirect to login
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  },
);

// Auth service
export const authService = {
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },
  
  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },
  
  refresh: async (refreshToken: string): Promise<RefreshResponse> => {
    const response = await api.post<RefreshResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },
  
  me: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
};

// Users service
export const usersService = {
  list: async (params?: { skip?: number; limit?: number }): Promise<PaginatedResponse<User>> => {
    const response = await api.get<PaginatedResponse<User>>('/users', { params });
    return response.data;
  },
  
  get: async (id: string): Promise<User> => {
    const response = await api.get<User>(`/users/${id}`);
    return response.data;
  },
  
  create: async (data: Partial<User> & { password: string }): Promise<User> => {
    const response = await api.post<User>('/users', data);
    return response.data;
  },
  
  update: async (id: string, data: Partial<User>): Promise<User> => {
    const response = await api.patch<User>(`/users/${id}`, data);
    return response.data;
  },
  
  updateMe: async (data: { first_name?: string; last_name?: string }): Promise<User> => {
    const response = await api.patch<User>('/users/me', data);
    return response.data;
  },
  
  uploadAvatar: async (file: File): Promise<User> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<User>('/users/me/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  deleteAvatar: async (): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>('/users/me/avatar');
    return response.data;
  },
  
  delete: async (id: string): Promise<void> => {
    await api.delete(`/users/${id}`);
  },
};

// Dashboard types
export interface StatItem {
  name: string;
  value: number | string;
  change: string;
  change_type: 'positive' | 'negative' | 'neutral';
}

export interface ActivityItem {
  id: string;
  action: string;
  description: string;
  timestamp: string;
  user_name?: string;
  user_email?: string;
}

export interface DashboardStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  total_roles: number;
  total_api_keys: number;
  active_api_keys: number;
  users_created_last_30_days: number;
  users_created_last_7_days: number;
  stats: StatItem[];
}

export interface RecentActivity {
  items: ActivityItem[];
  total: number;
}

export interface SystemHealth {
  database_status: string;
  cache_status: string;
  avg_response_time_ms: number;
  uptime_percentage: number;
  active_sessions: number;
}

// Dashboard service
export const dashboardService = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await api.get<DashboardStats>('/dashboard/stats');
    return response.data;
  },

  getActivity: async (limit: number = 10): Promise<RecentActivity> => {
    const response = await api.get<RecentActivity>('/dashboard/activity', {
      params: { limit },
    });
    return response.data;
  },

  getHealth: async (): Promise<SystemHealth> => {
    const response = await api.get<SystemHealth>('/dashboard/health-metrics');
    return response.data;
  },
};

// ==============================================================================
// OAuth2/SSO Types and Service
// ==============================================================================

export interface OAuthProvider {
  id: string;
  name: string;
  icon: string;
  color: string;
}

export interface OAuthAuthorizeResponse {
  authorization_url: string;
  state: string;
}

export interface OAuthConnection {
  id: string;
  provider: string;
  provider_email: string | null;
  provider_username: string | null;
  provider_display_name: string | null;
  provider_avatar_url: string | null;
  is_primary: boolean;
  last_used_at: string | null;
  created_at: string | null;
}

export const OAUTH_PROVIDERS: OAuthProvider[] = [
  { id: 'google', name: 'Google', icon: 'google', color: '#4285F4' },
  { id: 'github', name: 'GitHub', icon: 'github', color: '#333333' },
  { id: 'microsoft', name: 'Microsoft', icon: 'microsoft', color: '#00A4EF' },
];

export const oauthService = {
  /**
   * Get authorization URL for OAuth provider
   */
  getAuthorizationUrl: async (provider: string): Promise<OAuthAuthorizeResponse> => {
    const response = await api.get<OAuthAuthorizeResponse>(
      `/auth/oauth/${provider}/authorize`
    );
    return response.data;
  },

  /**
   * Redirect to OAuth provider (opens in same window)
   */
  redirectToProvider: async (provider: string): Promise<void> => {
    const { authorization_url } = await oauthService.getAuthorizationUrl(provider);
    window.location.href = authorization_url;
  },

  /**
   * Get user's OAuth connections
   */
  getConnections: async (): Promise<OAuthConnection[]> => {
    const response = await api.get<OAuthConnection[]>('/auth/oauth/connections');
    return response.data;
  },

  /**
   * Disconnect an OAuth provider
   */
  disconnect: async (provider: string): Promise<void> => {
    await api.delete(`/auth/oauth/${provider}/disconnect`);
  },

  /**
   * Link a new OAuth provider to existing account
   */
  linkProvider: async (provider: string): Promise<void> => {
    const response = await api.get<OAuthAuthorizeResponse>(
      `/auth/oauth/${provider}/authorize`,
      { params: { link: true } }
    );
    window.location.href = response.data.authorization_url;
  },
};

// ==============================================================================
// Search Types and Service
// ==============================================================================

export interface SearchFilter {
  field: string;
  value: string | number | boolean;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'contains' | 'startswith' | 'endswith';
}

export interface SearchSort {
  field: string;
  order: 'asc' | 'desc';
}

export interface SearchRequest {
  query: string;
  index: 'users' | 'posts' | 'messages' | 'documents' | 'audit_logs';
  filters?: SearchFilter[];
  sort?: SearchSort[];
  highlight_fields?: string[];
  page?: number;
  page_size?: number;
  fuzzy?: boolean;
}

export interface SearchHit {
  id: string;
  score: number;
  source: Record<string, unknown>;
  highlights: Record<string, string[]>;
  matched_fields: string[];
}

export interface SearchResponse {
  hits: SearchHit[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  took_ms: number;
  max_score: number | null;
  suggestions: string[];
}

export interface SearchSuggestion {
  suggestions: string[];
}

export const searchService = {
  /**
   * Perform a full-text search
   */
  search: async (request: SearchRequest): Promise<SearchResponse> => {
    const response = await api.post<SearchResponse>('/search', request);
    return response.data;
  },

  /**
   * Get search suggestions (autocomplete)
   */
  suggest: async (
    query: string,
    index: string = 'users'
  ): Promise<string[]> => {
    const response = await api.get<SearchSuggestion>('/search/suggest', {
      params: { query, index },
    });
    return response.data.suggestions;
  },

  /**
   * Quick search across all indices
   */
  quickSearch: async (query: string): Promise<SearchResponse> => {
    const response = await api.get<SearchResponse>('/search/quick', {
      params: { q: query },
    });
    return response.data;
  },
};

// ==============================================================================
// Notifications Types and Service
// ==============================================================================

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  action_url?: string;
}

export interface NotificationsResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

export const notificationsService = {
  /**
   * Get user notifications
   */
  list: async (params?: { 
    skip?: number; 
    limit?: number; 
    unread_only?: boolean 
  }): Promise<NotificationsResponse> => {
    const response = await api.get<NotificationsResponse>('/notifications', { params });
    return response.data;
  },

  /**
   * Get all notifications with pagination
   */
  getAll: async (params?: {
    page?: number;
    page_size?: number;
    unread_only?: boolean;
  }): Promise<NotificationsResponse> => {
    const response = await api.get<NotificationsResponse>('/notifications', { params });
    return response.data;
  },

  /**
   * Mark notification as read
   */
  markAsRead: async (id: string): Promise<void> => {
    await api.patch(`/notifications/${id}/read`);
  },

  /**
   * Mark all notifications as read
   */
  markAllAsRead: async (): Promise<void> => {
    await api.post('/notifications/mark-all-read');
  },

  /**
   * Delete a notification
   */
  delete: async (id: string): Promise<void> => {
    await api.delete(`/notifications/${id}`);
  },

  /**
   * Get unread count
   */
  getUnreadCount: async (): Promise<number> => {
    const response = await api.get<{ count: number }>('/notifications/unread-count');
    return response.data.count;
  },
};

// ==============================================================================
// Configuration Types and Service
// ==============================================================================

export interface FeatureConfig {
  websocket_enabled: boolean;
  websocket_notifications: boolean;
}

export const configService = {
  /**
   * Get feature configuration (feature flags)
   */
  getFeatures: async (): Promise<FeatureConfig> => {
    const response = await api.get<FeatureConfig>('/config/features');
    return response.data;
  },
};

// ==============================================================================
// Session Types and Service
// ==============================================================================

export interface UserSession {
  id: string;
  device_name: string;
  device_type: string;
  browser: string;
  os: string;
  ip_address: string;
  location: string;
  last_activity: string;
  is_current: boolean;
  created_at: string;
}

export interface SessionListResponse {
  sessions: UserSession[];
  total: number;
}

export interface RevokeSessionsResponse {
  message: string;
  revoked_count: number;
}

export const sessionsService = {
  /**
   * List all active sessions for current user
   */
  list: async (): Promise<SessionListResponse> => {
    const response = await api.get<SessionListResponse>('/sessions');
    return response.data;
  },

  /**
   * Revoke a specific session
   */
  revoke: async (sessionId: string): Promise<RevokeSessionsResponse> => {
    const response = await api.delete<RevokeSessionsResponse>(`/sessions/${sessionId}`);
    return response.data;
  },

  /**
   * Revoke all other sessions
   */
  revokeAll: async (): Promise<RevokeSessionsResponse> => {
    const response = await api.delete<RevokeSessionsResponse>('/sessions');
    return response.data;
  },
};

// ==============================================================================
// Email Verification Service
// ==============================================================================

export interface VerificationStatus {
  email: string;
  email_verified: boolean;
  verification_required: boolean;
}

export const emailVerificationService = {
  /**
   * Send verification email
   */
  sendVerification: async (): Promise<{ message: string; success: boolean }> => {
    const response = await api.post<{ message: string; success: boolean }>('/auth/send-verification');
    return response.data;
  },

  /**
   * Verify email with token
   */
  verifyEmail: async (token: string): Promise<{ message: string; success: boolean }> => {
    const response = await api.post<{ message: string; success: boolean }>(`/auth/verify-email?token=${token}`);
    return response.data;
  },

  /**
   * Get verification status
   */
  getStatus: async (): Promise<VerificationStatus> => {
    const response = await api.get<VerificationStatus>('/auth/verification-status');
    return response.data;
  },
};

// ==============================================================================
// Roles Service
// ==============================================================================

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: string[];
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface RoleListResponse {
  items: Role[];
  total: number;
}

export interface CreateRoleData {
  name: string;
  description?: string;
  permissions: string[];
}

export interface UpdateRoleData {
  name?: string;
  description?: string;
  permissions?: string[];
}

export interface UserPermissions {
  user_id: string;
  permissions: string[];
  roles: Role[];
}

export interface AssignRoleRequest {
  user_id: string;
  role_id: string;
}

export const rolesService = {
  /**
   * List all roles for current tenant
   */
  list: async (params?: { skip?: number; limit?: number }): Promise<RoleListResponse> => {
    const response = await api.get<RoleListResponse>('/roles', { params });
    return response.data;
  },

  /**
   * Get role by ID
   */
  get: async (id: string): Promise<Role> => {
    const response = await api.get<Role>(`/roles/${id}`);
    return response.data;
  },

  /**
   * Create a new role
   */
  create: async (data: CreateRoleData): Promise<Role> => {
    const response = await api.post<Role>('/roles', data);
    return response.data;
  },

  /**
   * Update an existing role
   */
  update: async (id: string, data: UpdateRoleData): Promise<Role> => {
    const response = await api.patch<Role>(`/roles/${id}`, data);
    return response.data;
  },

  /**
   * Delete a role
   */
  delete: async (id: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/roles/${id}`);
    return response.data;
  },

  /**
   * Assign role to user
   */
  assignToUser: async (data: AssignRoleRequest): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/roles/assign', data);
    return response.data;
  },

  /**
   * Revoke role from user
   */
  revokeFromUser: async (data: AssignRoleRequest): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/roles/revoke', data);
    return response.data;
  },

  /**
   * Get user's permissions
   */
  getUserPermissions: async (userId: string): Promise<UserPermissions> => {
    const response = await api.get<UserPermissions>(`/roles/users/${userId}/permissions`);
    return response.data;
  },
};

// ==============================================================================
// Audit Logs Service
// ==============================================================================

export interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  resource_name?: string;
  actor_id?: string;
  actor_email?: string;
  actor_ip?: string;
  actor_user_agent?: string;
  tenant_id?: string;
  old_value?: Record<string, unknown>;
  new_value?: Record<string, unknown>;
  metadata: Record<string, unknown>;
  reason?: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  skip: number;
  limit: number;
}

export interface AuditLogFilters {
  skip?: number;
  limit?: number;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
}

export const auditLogsService = {
  /**
   * List audit logs for current tenant
   */
  list: async (filters?: AuditLogFilters): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>('/audit-logs', { params: filters });
    return response.data;
  },

  /**
   * Get specific audit log entry
   */
  get: async (id: string): Promise<AuditLog> => {
    const response = await api.get<AuditLog>(`/audit-logs/${id}`);
    return response.data;
  },

  /**
   * Get my activity
   */
  getMyActivity: async (filters?: AuditLogFilters): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>('/audit-logs/my-activity', { params: filters });
    return response.data;
  },

  /**
   * Get recent logins
   */
  getRecentLogins: async (limit?: number, includeFailed?: boolean): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>('/audit-logs/recent-logins', {
      params: { limit, include_failed: includeFailed },
    });
    return response.data;
  },

  /**
   * Get resource history
   */
  getResourceHistory: async (resourceType: string, resourceId: string, filters?: AuditLogFilters): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>(`/audit-logs/resource/${resourceType}/${resourceId}`, { params: filters });
    return response.data;
  },

  /**
   * Get available actions
   */
  getActions: async (): Promise<string[]> => {
    const response = await api.get<string[]>('/audit-logs/actions/list');
    return response.data;
  },

  /**
   * Get available resource types
   */
  getResourceTypes: async (): Promise<string[]> => {
    const response = await api.get<string[]>('/audit-logs/resource-types/list');
    return response.data;
  },
};

// ==============================================================================
// Tenants Service (Superuser only)
// ==============================================================================

export interface TenantSettings {
  enable_2fa: boolean;
  enable_api_keys: boolean;
  enable_webhooks: boolean;
  max_users: number;
  max_api_keys_per_user: number;
  max_storage_mb: number;
  primary_color: string;
  logo_url?: string;
  password_min_length: number;
  session_timeout_minutes: number;
  require_email_verification: boolean;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  email?: string;
  phone?: string;
  is_active: boolean;
  is_verified: boolean;
  plan: string;
  plan_expires_at?: string;
  settings: TenantSettings;
  domain?: string;
  timezone: string;
  locale: string;
  created_at: string;
  updated_at: string;
}

export interface TenantListResponse {
  items: Tenant[];
  total: number;
  skip: number;
  limit: number;
}

export interface CreateTenantData {
  name: string;
  slug: string;
  email?: string;
  phone?: string;
  domain?: string;
  timezone?: string;
  locale?: string;
  plan?: string;
  settings?: Partial<TenantSettings>;
}

export interface UpdateTenantData {
  name?: string;
  slug?: string;
  email?: string;
  phone?: string;
  domain?: string;
  timezone?: string;
  locale?: string;
  plan?: string;
  settings?: Partial<TenantSettings>;
}

export const tenantsService = {
  /**
   * List all tenants (superuser only)
   */
  list: async (params?: { skip?: number; limit?: number; is_active?: boolean }): Promise<TenantListResponse> => {
    const response = await api.get<TenantListResponse>('/tenants', { params });
    return response.data;
  },

  /**
   * Get tenant by ID
   */
  get: async (id: string): Promise<Tenant> => {
    const response = await api.get<Tenant>(`/tenants/${id}`);
    return response.data;
  },

  /**
   * Create a new tenant
   */
  create: async (data: CreateTenantData): Promise<Tenant> => {
    const response = await api.post<Tenant>('/tenants', data);
    return response.data;
  },

  /**
   * Update a tenant
   */
  update: async (id: string, data: UpdateTenantData): Promise<Tenant> => {
    const response = await api.patch<Tenant>(`/tenants/${id}`, data);
    return response.data;
  },

  /**
   * Delete a tenant
   */
  delete: async (id: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/tenants/${id}`);
    return response.data;
  },

  /**
   * Activate a tenant
   */
  activate: async (id: string): Promise<Tenant> => {
    const response = await api.post<Tenant>(`/tenants/${id}/activate`);
    return response.data;
  },

  /**
   * Deactivate a tenant
   */
  deactivate: async (id: string): Promise<Tenant> => {
    const response = await api.post<Tenant>(`/tenants/${id}/deactivate`);
    return response.data;
  },

  /**
   * Verify a tenant
   */
  verify: async (id: string): Promise<Tenant> => {
    const response = await api.post<Tenant>(`/tenants/${id}/verify`);
    return response.data;
  },

  /**
   * Update tenant plan
   */
  updatePlan: async (id: string, plan: string, expiresAt?: string): Promise<Tenant> => {
    const response = await api.patch<Tenant>(`/tenants/${id}/plan`, { plan, plan_expires_at: expiresAt });
    return response.data;
  },
};

export default api;
