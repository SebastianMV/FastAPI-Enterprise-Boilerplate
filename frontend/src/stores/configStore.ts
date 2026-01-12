import { create } from 'zustand';
import { persist } from 'zustand/middleware';
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
  persist(
    (set) => ({
      // Initial state - all features disabled until fetched
      websocket_enabled: true,
      websocket_notifications: true,
      isLoading: false,
      error: null,

      fetchFeatures: async () => {
        set({ isLoading: true, error: null });
        
        try {
          const features = await configService.getFeatures();
          
          set({
            ...features,
            isLoading: false,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Failed to fetch features',
          });
        }
      },

      setError: (error) => {
        set({ error });
      },
    }),
    {
      name: 'config-storage',
      partialize: (state) => ({
        websocket_enabled: state.websocket_enabled,
        websocket_notifications: state.websocket_notifications,
      }),
    }
  )
);
