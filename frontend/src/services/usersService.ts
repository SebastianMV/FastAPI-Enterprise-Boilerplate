import api from './api';
import type { User, PaginatedResponse } from './api';
import { validateAvatarFile, clampPaginationParams } from '@/utils/security';

// Re-export types used by consumers
export type { User, PaginatedResponse };

// Users service
export const usersService = {
  list: async (params?: { skip?: number; limit?: number }): Promise<PaginatedResponse<User>> => {
    const safeParams = clampPaginationParams(params);
    const response = await api.get<PaginatedResponse<User>>('/users', { params: safeParams });
    return response.data;
  },
  
  get: async (id: string): Promise<User> => {
    const response = await api.get<User>(`/users/${encodeURIComponent(id)}`);
    return response.data;
  },
  
  create: async (data: { email: string; password: string; first_name: string; last_name: string; is_active?: boolean; is_superuser?: boolean; roles?: string[] }): Promise<User> => {
    // Only send explicitly allowed fields to prevent mass-assignment
    const safeData = {
      email: data.email,
      password: data.password,
      first_name: data.first_name,
      last_name: data.last_name,
      is_active: data.is_active,
      is_superuser: data.is_superuser,
      roles: data.roles,
    };
    const response = await api.post<User>('/users', safeData);
    return response.data;
  },
  
  update: async (id: string, data: Partial<User>): Promise<User> => {
    // Only send explicitly allowed fields to prevent mass-assignment / privilege escalation
    const safeData: Record<string, unknown> = {};
    const ALLOWED_FIELDS = ['email', 'first_name', 'last_name', 'is_active', 'roles'] as const;
    for (const field of ALLOWED_FIELDS) {
      if (data[field] !== undefined) {
        safeData[field] = data[field];
      }
    }
    const response = await api.patch<User>(`/users/${encodeURIComponent(id)}`, safeData);
    return response.data;
  },
  
  updateMe: async (data: { first_name?: string; last_name?: string }): Promise<User> => {
    const response = await api.patch<User>('/users/me', data);
    return response.data;
  },
  
  uploadAvatar: async (file: File): Promise<User> => {
    const validation = validateAvatarFile(file);
    if (!validation.valid) {
      throw new Error(validation.error || 'Invalid file');
    }
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
    await api.delete(`/users/${encodeURIComponent(id)}`);
  },
};
