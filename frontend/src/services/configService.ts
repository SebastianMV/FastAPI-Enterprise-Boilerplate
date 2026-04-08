import api from './api';

// Config Types
export interface FeatureConfig {
  websocket_enabled: boolean;
  websocket_notifications: boolean;
}

export const configService = {
  getFeatures: async (): Promise<FeatureConfig> => {
    const response = await api.get<FeatureConfig>('/config/features');
    return response.data;
  },
};
