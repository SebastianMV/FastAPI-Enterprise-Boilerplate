import api from './api';

// Dashboard types
export interface StatItem {
  name: string;
  value: number | string;
  change: string;
  change_type: 'positive' | 'negative' | 'neutral';
}

export interface ActivityItem {
  id: string;
  action: string;
  description: string;
  timestamp: string;
  user_name?: string;
  user_email?: string;
}

export interface DashboardStats {
  total_users: number;
  active_users: number;
  inactive_users: number;
  total_roles: number;
  total_api_keys: number;
  active_api_keys: number;
  users_created_last_30_days: number;
  users_created_last_7_days: number;
  stats: StatItem[];
}

export interface RecentActivity {
  items: ActivityItem[];
  total: number;
}

export interface SystemHealth {
  database_status: string;
  cache_status: string;
  avg_response_time_ms: number;
  uptime_percentage: number;
  active_sessions: number;
}

// Dashboard service
export const dashboardService = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await api.get<DashboardStats>('/dashboard/stats');
    return response.data;
  },

  getActivity: async (limit: number = 10): Promise<RecentActivity> => {
    const response = await api.get<RecentActivity>('/dashboard/activity', {
      params: { limit },
    });
    return response.data;
  },

  getHealth: async (): Promise<SystemHealth> => {
    const response = await api.get<SystemHealth>('/dashboard/health-metrics');
    return response.data;
  },
};
