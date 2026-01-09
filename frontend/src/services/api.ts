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
  created_at: string;
  last_login?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
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
  baseURL: '/',
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
    if (error.response?.status === 401) {
      // Try to refresh token
      const authStorage = localStorage.getItem('auth-storage');
      
      if (authStorage) {
        try {
          const { state } = JSON.parse(authStorage);
          
          if (state?.refreshToken && !error.config._retry) {
            error.config._retry = true;
            
            const refreshResponse = await axios.post('/api/v1/auth/refresh', {
              refresh_token: state.refreshToken,
            });
            
            // Update stored token
            const newState = {
              ...state,
              accessToken: refreshResponse.data.access_token,
            };
            
            localStorage.setItem('auth-storage', JSON.stringify({
              state: newState,
              version: 0,
            }));
            
            // Retry original request
            error.config.headers.Authorization = `Bearer ${refreshResponse.data.access_token}`;
            return api(error.config);
          }
        } catch {
          // Refresh failed, clear storage
          localStorage.removeItem('auth-storage');
          window.location.href = '/login';
        }
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
  { id: 'discord', name: 'Discord', icon: 'discord', color: '#5865F2' },
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
// Chat Types and Service
// ==============================================================================

export interface ChatMessage {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  content_type: 'text' | 'image' | 'file' | 'audio' | 'video' | 'location' | 'system';
  metadata?: Record<string, unknown>;
  status: 'pending' | 'sent' | 'delivered' | 'read';
  reply_to_id?: string;
  reactions?: Record<string, string[]>;
  is_edited?: boolean;
  created_at: string;
}

export interface Conversation {
  id: string;
  type: 'direct' | 'group';
  name?: string;
  participants: Array<{
    user_id: string;
    role: string;
    nickname?: string;
  }>;
  last_message_preview?: string;
  last_message_at?: string;
  unread_count: number;
}

export interface MessagesResponse {
  items: ChatMessage[];
  has_more: boolean;
}

export const chatService = {
  /**
   * Get all conversations for current user
   */
  getConversations: async (): Promise<Conversation[]> => {
    const response = await api.get<Conversation[]>('/chat/conversations');
    return response.data;
  },

  /**
   * Get messages for a conversation
   */
  getMessages: async (
    conversationId: string,
    params?: { limit?: number; before?: string }
  ): Promise<MessagesResponse> => {
    const response = await api.get<MessagesResponse>(
      `/chat/conversations/${conversationId}/messages`,
      { params }
    );
    return response.data;
  },

  /**
   * Send a message to a conversation
   */
  sendMessage: async (
    conversationId: string,
    data: { content: string; reply_to_id?: string }
  ): Promise<ChatMessage> => {
    const response = await api.post<ChatMessage>(
      `/chat/conversations/${conversationId}/messages`,
      data
    );
    return response.data;
  },

  /**
   * Mark messages as read
   */
  markAsRead: async (
    conversationId: string,
    messageIds: string[]
  ): Promise<void> => {
    await api.post(`/chat/conversations/${conversationId}/read`, {
      message_ids: messageIds,
    });
  },

  /**
   * Create a direct conversation
   */
  createDirectConversation: async (participantId: string): Promise<Conversation> => {
    const response = await api.post<Conversation>('/chat/conversations/direct', {
      participant_id: participantId,
    });
    return response.data;
  },

  /**
   * Create a group conversation
   */
  createGroupConversation: async (
    name: string,
    participantIds: string[]
  ): Promise<Conversation> => {
    const response = await api.post<Conversation>('/chat/conversations/group', {
      name,
      participant_ids: participantIds,
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
  chat_enabled: boolean;
  websocket_enabled: boolean;
  websocket_notifications: boolean;
  websocket_chat: boolean;
  websocket_presence: boolean;
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

export default api;
