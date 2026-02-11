import api from './api';

// Audit Log Types
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
  list: async (filters?: AuditLogFilters): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>('/audit-logs', { params: filters });
    return response.data;
  },

  get: async (id: string): Promise<AuditLog> => {
    const response = await api.get<AuditLog>(`/audit-logs/${encodeURIComponent(id)}`);
    return response.data;
  },

  getMyActivity: async (filters?: AuditLogFilters): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>('/audit-logs/my-activity', { params: filters });
    return response.data;
  },

  getRecentLogins: async (limit?: number, includeFailed?: boolean): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>('/audit-logs/recent-logins', {
      params: { limit, include_failed: includeFailed },
    });
    return response.data;
  },

  getResourceHistory: async (resourceType: string, resourceId: string, filters?: AuditLogFilters): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>(`/audit-logs/resource/${encodeURIComponent(resourceType)}/${encodeURIComponent(resourceId)}`, { params: filters });
    return response.data;
  },

  getActions: async (): Promise<string[]> => {
    const response = await api.get<string[]>('/audit-logs/actions/list');
    return response.data;
  },

  getResourceTypes: async (): Promise<string[]> => {
    const response = await api.get<string[]>('/audit-logs/resource-types/list');
    return response.data;
  },
};
