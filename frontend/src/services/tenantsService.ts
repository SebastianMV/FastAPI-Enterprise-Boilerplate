import { clampPaginationParams } from "@/utils/security";
import api from "./api";

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
  page: number;
  page_size: number;
  pages: number;
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
  list: async (params?: {
    page?: number;
    page_size?: number;
    is_active?: boolean;
  }): Promise<TenantListResponse> => {
    const { page, page_size } = clampPaginationParams(params);
    const response = await api.get<TenantListResponse>("/tenants", {
      params: { page, page_size, is_active: params?.is_active },
    });
    return response.data;
  },

  get: async (id: string): Promise<Tenant> => {
    const response = await api.get<Tenant>(
      `/tenants/${encodeURIComponent(id)}`,
    );
    return response.data;
  },

  create: async (data: CreateTenantData): Promise<Tenant> => {
    const ALLOWED_FIELDS: (keyof CreateTenantData)[] = [
      "name",
      "slug",
      "email",
      "phone",
      "domain",
      "timezone",
      "locale",
      "plan",
      "settings",
    ];
    const safeData: Record<string, unknown> = {};
    for (const key of ALLOWED_FIELDS) {
      if (data[key] !== undefined) safeData[key] = data[key];
    }
    const response = await api.post<Tenant>("/tenants", safeData);
    return response.data;
  },

  update: async (id: string, data: UpdateTenantData): Promise<Tenant> => {
    const ALLOWED_FIELDS: (keyof UpdateTenantData)[] = [
      "name",
      "slug",
      "email",
      "phone",
      "domain",
      "timezone",
      "locale",
      "plan",
      "settings",
    ];
    const safeData: Record<string, unknown> = {};
    for (const key of ALLOWED_FIELDS) {
      if (data[key] !== undefined) safeData[key] = data[key];
    }
    const response = await api.patch<Tenant>(
      `/tenants/${encodeURIComponent(id)}`,
      safeData,
    );
    return response.data;
  },

  delete: async (id: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(
      `/tenants/${encodeURIComponent(id)}`,
    );
    return response.data;
  },

  activate: async (id: string): Promise<Tenant> => {
    const response = await api.post<Tenant>(
      `/tenants/${encodeURIComponent(id)}/activate`,
    );
    return response.data;
  },

  deactivate: async (id: string): Promise<Tenant> => {
    const response = await api.post<Tenant>(
      `/tenants/${encodeURIComponent(id)}/deactivate`,
    );
    return response.data;
  },

  verify: async (id: string): Promise<Tenant> => {
    const response = await api.post<Tenant>(
      `/tenants/${encodeURIComponent(id)}/verify`,
    );
    return response.data;
  },

  updatePlan: async (
    id: string,
    plan: string,
    expiresAt?: string,
  ): Promise<Tenant> => {
    const response = await api.patch<Tenant>(
      `/tenants/${encodeURIComponent(id)}/plan`,
      { plan, plan_expires_at: expiresAt },
    );
    return response.data;
  },
};
