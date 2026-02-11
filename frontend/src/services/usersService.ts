import api from './api';
import type { User, PaginatedResponse } from './api';

// Re-export types used by consumers
export type { User, PaginatedResponse };

// Users service
export const usersService = {
  list: async (params?: { skip?: number; limit?: number }): Promise<PaginatedResponse<User>> => {
    const response = await api.get<PaginatedResponse<User>>('/users', { params });
    return response.data;
  },
  
  get: async (id: string): Promise<User> => {
    const response = await api.get<User>(`/users/${encodeURIComponent(id)}`);
    return response.data;
  },
  
  create: async (data: Partial<User> & { password: string }): Promise<User> => {
    const response = await api.post<User>('/users', data);
    return response.data;
  },
  
  update: async (id: string, data: Partial<User>): Promise<User> => {
    const response = await api.patch<User>(`/users/${encodeURIComponent(id)}`, data);
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
    await api.delete(`/users/${encodeURIComponent(id)}`);
  },
};
