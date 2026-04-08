import api from './api';

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  usage_count: number;
  created_at: string;
}

export interface ApiKeyListResponse {
  items: ApiKey[];
  total: number;
}

export interface CreateApiKeyData {
  name: string;
  scopes: string[];
  expires_in_days: number | null;
}

export interface NewlyCreatedKey {
  id: string;
  name: string;
  prefix: string;
  key: string;
  scopes: string[];
  expires_at: string | null;
  created_at: string;
}

export const apiKeysService = {
  list: async (includeRevoked = false): Promise<ApiKeyListResponse> => {
    const response = await api.get<ApiKeyListResponse>(
      '/api-keys',
      { params: { include_revoked: includeRevoked } },
    );
    return response.data;
  },

  create: async (data: CreateApiKeyData): Promise<NewlyCreatedKey> => {
    const safeData = {
      name: data.name,
      scopes: data.scopes,
      expires_in_days: data.expires_in_days,
    };
    const response = await api.post<NewlyCreatedKey>('/api-keys', safeData);
    return response.data;
  },

  revoke: async (id: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(
      `/api-keys/${encodeURIComponent(id)}`,
    );
    return response.data;
  },
};
