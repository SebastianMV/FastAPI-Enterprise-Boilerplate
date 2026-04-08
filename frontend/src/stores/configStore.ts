import { create } from 'zustand';
import { configService, type FeatureConfig } from '@/services/api';

interface ConfigState extends FeatureConfig {
  isLoading: boolean;
  error: string | null;
  
  // Actions
  fetchFeatures: () => Promise<void>;
  setError: (error: string | null) => void;
}

/**
 * Zustand store for application feature configuration.
 * 
 * Manages feature flags like chat enabled, websocket enabled, etc.
 */
export const useConfigStore = create<ConfigState>()(
    (set) => ({
      // Initial state — features disabled by default (fail-closed)
      // until explicitly enabled by server response
      websocket_enabled: false,
      websocket_notifications: false,
      isLoading: false,
      error: null,

      fetchFeatures: async () => {
        set({ isLoading: true, error: null });
        
        try {
          const features = await configService.getFeatures();
          
          // Only apply known properties (allowlist) to prevent state pollution
          set({
            websocket_enabled: Boolean(features.websocket_enabled),
            websocket_notifications: Boolean(features.websocket_notifications),
            isLoading: false,
          });
        } catch (error) {
          if (import.meta.env.DEV) {
            // eslint-disable-next-line no-console -- development-only error logging
            console.error('[configStore] Failed to fetch features:', error);
          }
          set({
            isLoading: false,
            error: 'config.fetchError',
          });
        }
      },

      setError: (error) => {
        set({ error });
      },
    }),
);
