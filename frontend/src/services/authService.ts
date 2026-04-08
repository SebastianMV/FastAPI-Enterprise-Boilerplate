import api from './api';
import type { User, LoginCredentials, LoginResponse, RefreshResponse } from './api';

// Re-export types used by consumers
export type { User, LoginCredentials, LoginResponse, RefreshResponse };

// Auth service
export const authService = {
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },
  
  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },
  
  refresh: async (): Promise<RefreshResponse> => {
    const response = await api.post<RefreshResponse>('/auth/refresh', {});
    return response.data;
  },
  
  me: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
};
