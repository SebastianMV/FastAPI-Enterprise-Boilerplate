import { clampPaginationParams } from "@/utils/security";
import api from "./api";

// Notification Types
export interface Notification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  action_url?: string;
}

export interface NotificationsResponse {
  items: Notification[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  unread_count: number;
}

export const notificationsService = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    unread_only?: boolean;
  }): Promise<NotificationsResponse> => {
    const { page, page_size } = clampPaginationParams(params);
    const response = await api.get<NotificationsResponse>("/notifications", {
      params: { page, page_size, unread_only: params?.unread_only },
    });
    return response.data;
  },

  getAll: async (params?: {
    page?: number;
    page_size?: number;
    unread_only?: boolean;
  }): Promise<NotificationsResponse> => {
    const { page, page_size } = clampPaginationParams(params);
    const response = await api.get<NotificationsResponse>("/notifications", {
      params: { page, page_size, unread_only: params?.unread_only },
    });
    return response.data;
  },

  markAsRead: async (id: string): Promise<void> => {
    await api.patch(`/notifications/${encodeURIComponent(id)}/read`);
  },

  markAllAsRead: async (): Promise<void> => {
    await api.post("/notifications/mark-all-read");
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/notifications/${encodeURIComponent(id)}`);
  },

  getUnreadCount: async (): Promise<number> => {
    const response = await api.get<{ count: number }>(
      "/notifications/unread-count",
    );
    return response.data.count;
  },
};
