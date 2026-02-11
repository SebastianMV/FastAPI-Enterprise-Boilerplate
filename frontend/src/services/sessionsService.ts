import api from './api';

// Session Types
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
  list: async (): Promise<SessionListResponse> => {
    const response = await api.get<SessionListResponse>('/sessions');
    return response.data;
  },

  revoke: async (sessionId: string): Promise<RevokeSessionsResponse> => {
    const response = await api.delete<RevokeSessionsResponse>(`/sessions/${encodeURIComponent(sessionId)}`);
    return response.data;
  },

  revokeAll: async (): Promise<RevokeSessionsResponse> => {
    const response = await api.delete<RevokeSessionsResponse>('/sessions');
    return response.data;
  },
};
