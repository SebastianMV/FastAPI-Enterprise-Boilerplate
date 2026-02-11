import api from './api';

// Role Types
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
  list: async (params?: { skip?: number; limit?: number }): Promise<RoleListResponse> => {
    const response = await api.get<RoleListResponse>('/roles', { params });
    return response.data;
  },

  get: async (id: string): Promise<Role> => {
    const response = await api.get<Role>(`/roles/${encodeURIComponent(id)}`);
    return response.data;
  },

  create: async (data: CreateRoleData): Promise<Role> => {
    const response = await api.post<Role>('/roles', data);
    return response.data;
  },

  update: async (id: string, data: UpdateRoleData): Promise<Role> => {
    const response = await api.patch<Role>(`/roles/${encodeURIComponent(id)}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/roles/${encodeURIComponent(id)}`);
    return response.data;
  },

  assignToUser: async (data: AssignRoleRequest): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/roles/assign', data);
    return response.data;
  },

  revokeFromUser: async (data: AssignRoleRequest): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/roles/revoke', data);
    return response.data;
  },

  getUserPermissions: async (userId: string): Promise<UserPermissions> => {
    const response = await api.get<UserPermissions>(`/roles/users/${encodeURIComponent(userId)}/permissions`);
    return response.data;
  },
};
