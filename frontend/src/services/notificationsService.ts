import api from './api';
import { clampPaginationParams } from '@/utils/security';

// Notification Types
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  action_url?: string;
}

export interface NotificationsResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

export const notificationsService = {
  list: async (params?: { 
    skip?: number; 
    limit?: number; 
    unread_only?: boolean 
  }): Promise<NotificationsResponse> => {
    const { skip, limit } = clampPaginationParams(params);
    const response = await api.get<NotificationsResponse>('/notifications', { 
      params: { skip, limit, unread_only: params?.unread_only } 
    });
    return response.data;
  },

  getAll: async (params?: {
    page?: number;
    page_size?: number;
    unread_only?: boolean;
  }): Promise<NotificationsResponse> => {
    const safePage = Math.max(1, Math.min(1000, Math.floor(Number(params?.page) || 1)));
    const safePageSize = Math.min(100, Math.max(1, Math.floor(Number(params?.page_size) || 20)));
    const response = await api.get<NotificationsResponse>('/notifications', { 
      params: { page: safePage, page_size: safePageSize, unread_only: params?.unread_only } 
    });
    return response.data;
  },

  markAsRead: async (id: string): Promise<void> => {
    await api.patch(`/notifications/${encodeURIComponent(id)}/read`);
  },

  markAllAsRead: async (): Promise<void> => {
    await api.post('/notifications/mark-all-read');
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/notifications/${encodeURIComponent(id)}`);
  },

  getUnreadCount: async (): Promise<number> => {
    const response = await api.get<{ count: number }>('/notifications/unread-count');
    return response.data.count;
  },
};
