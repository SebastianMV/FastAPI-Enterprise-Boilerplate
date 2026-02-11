import api from './api';

// Tenant Types
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
  list: async (params?: { skip?: number; limit?: number; is_active?: boolean }): Promise<TenantListResponse> => {
    const response = await api.get<TenantListResponse>('/tenants', { params });
    return response.data;
  },

  get: async (id: string): Promise<Tenant> => {
    const response = await api.get<Tenant>(`/tenants/${encodeURIComponent(id)}`);
    return response.data;
  },

  create: async (data: CreateTenantData): Promise<Tenant> => {
    const response = await api.post<Tenant>('/tenants', data);
    return response.data;
  },

  update: async (id: string, data: UpdateTenantData): Promise<Tenant> => {
    const response = await api.patch<Tenant>(`/tenants/${encodeURIComponent(id)}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/tenants/${encodeURIComponent(id)}`);
    return response.data;
  },

  activate: async (id: string): Promise<Tenant> => {
    const response = await api.post<Tenant>(`/tenants/${encodeURIComponent(id)}/activate`);
    return response.data;
  },

  deactivate: async (id: string): Promise<Tenant> => {
    const response = await api.post<Tenant>(`/tenants/${encodeURIComponent(id)}/deactivate`);
    return response.data;
  },

  verify: async (id: string): Promise<Tenant> => {
    const response = await api.post<Tenant>(`/tenants/${encodeURIComponent(id)}/verify`);
    return response.data;
  },

  updatePlan: async (id: string, plan: string, expiresAt?: string): Promise<Tenant> => {
    const response = await api.patch<Tenant>(`/tenants/${encodeURIComponent(id)}/plan`, { plan, plan_expires_at: expiresAt });
    return response.data;
  },
};
