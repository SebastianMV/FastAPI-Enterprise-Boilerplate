import { clampPaginationParams } from "@/utils/security";
import api from "./api";

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
  page: number;
  page_size: number;
  pages: number;
}

export interface AuditLogFilters {
  page?: number;
  page_size?: number;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
}

export const auditLogsService = {
  list: async (filters?: AuditLogFilters): Promise<AuditLogListResponse> => {
    const { page, page_size } = clampPaginationParams(filters);
    // Allowlist filter params to prevent unexpected keys from reaching the API
    const ALLOWED_FILTER_KEYS = new Set([
      "action",
      "resource_type",
      "start_date",
      "end_date",
    ]);
    const safeFilters: Record<string, unknown> = { page, page_size };
    if (filters) {
      for (const [key, value] of Object.entries(filters)) {
        if (ALLOWED_FILTER_KEYS.has(key) && value !== undefined) {
          safeFilters[key] = value;
        }
      }
    }
    const response = await api.get<AuditLogListResponse>("/audit-logs", {
      params: safeFilters,
    });
    return response.data;
  },

  get: async (id: string): Promise<AuditLog> => {
    const response = await api.get<AuditLog>(
      `/audit-logs/${encodeURIComponent(id)}`,
    );
    return response.data;
  },

  getMyActivity: async (
    filters?: AuditLogFilters,
  ): Promise<AuditLogListResponse> => {
    const { page, page_size } = clampPaginationParams(filters);
    const ALLOWED_FILTER_KEYS = new Set([
      "action",
      "resource_type",
      "start_date",
      "end_date",
    ]);
    const safeFilters: Record<string, unknown> = { page, page_size };
    if (filters) {
      for (const [key, value] of Object.entries(filters)) {
        if (ALLOWED_FILTER_KEYS.has(key) && value !== undefined) {
          safeFilters[key] = value;
        }
      }
    }
    const response = await api.get<AuditLogListResponse>(
      "/audit-logs/my-activity",
      { params: safeFilters },
    );
    return response.data;
  },

  getRecentLogins: async (
    pageSize?: number,
    includeFailed?: boolean,
  ): Promise<AuditLogListResponse> => {
    const safePageSize = Math.min(
      100,
      Math.max(1, Math.floor(Number(pageSize) || 20)),
    );
    const response = await api.get<AuditLogListResponse>(
      "/audit-logs/recent-logins",
      {
        params: { page_size: safePageSize, include_failed: includeFailed },
      },
    );
    return response.data;
  },

  getResourceHistory: async (
    resourceType: string,
    resourceId: string,
    filters?: AuditLogFilters,
  ): Promise<AuditLogListResponse> => {
    const { page, page_size } = clampPaginationParams(filters);
    const ALLOWED_FILTER_KEYS = new Set(["action", "start_date", "end_date"]);
    const safeFilters: Record<string, unknown> = { page, page_size };
    if (filters) {
      for (const [key, value] of Object.entries(filters)) {
        if (ALLOWED_FILTER_KEYS.has(key) && value !== undefined) {
          safeFilters[key] = value;
        }
      }
    }
    const response = await api.get<AuditLogListResponse>(
      `/audit-logs/resource/${encodeURIComponent(resourceType)}/${encodeURIComponent(resourceId)}`,
      { params: safeFilters },
    );
    return response.data;
  },

  getActions: async (): Promise<string[]> => {
    const response = await api.get<string[]>("/audit-logs/actions/list");
    return response.data;
  },

  getResourceTypes: async (): Promise<string[]> => {
    const response = await api.get<string[]>("/audit-logs/resource-types/list");
    return response.data;
  },
};
