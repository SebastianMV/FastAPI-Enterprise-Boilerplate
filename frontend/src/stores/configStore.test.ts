/**
 * Tests for configStore.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act } from '@testing-library/react';

// Mock the api module
vi.mock('@/services/api', () => ({
  configService: {
    getFeatures: vi.fn(),
  },
}));

// Import after mock
import { useConfigStore } from './configStore';
import { configService } from '@/services/api';

describe('configStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset store state
    act(() => {
      useConfigStore.setState({
        websocket_enabled: true,
        websocket_notifications: true,
        isLoading: false,
        error: null,
      });
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial state', () => {
    it('should have websocket_enabled set to true by default', () => {
      const state = useConfigStore.getState();
      expect(state.websocket_enabled).toBe(true);
    });

    it('should have websocket_notifications set to true by default', () => {
      const state = useConfigStore.getState();
      expect(state.websocket_notifications).toBe(true);
    });

    it('should not be loading initially', () => {
      const state = useConfigStore.getState();
      expect(state.isLoading).toBe(false);
    });

    it('should have no error initially', () => {
      const state = useConfigStore.getState();
      expect(state.error).toBeNull();
    });
  });

  describe('fetchFeatures', () => {
    it('should set loading to true while fetching', async () => {
      (configService.getFeatures as ReturnType<typeof vi.fn>).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ websocket_enabled: true, websocket_notifications: true }), 100))
      );

      const promise = useConfigStore.getState().fetchFeatures();
      
      expect(useConfigStore.getState().isLoading).toBe(true);
      
      await promise;
    });

    it('should update features on success', async () => {
      const mockFeatures = {
        websocket_enabled: false,
        websocket_notifications: false,
      };
      
      (configService.getFeatures as ReturnType<typeof vi.fn>).mockResolvedValue(mockFeatures);

      await useConfigStore.getState().fetchFeatures();
      
      const state = useConfigStore.getState();
      expect(state.websocket_enabled).toBe(false);
      expect(state.websocket_notifications).toBe(false);
      expect(state.isLoading).toBe(false);
    });

    it('should set error on failure', async () => {
      (configService.getFeatures as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Network error')
      );

      await useConfigStore.getState().fetchFeatures();
      
      const state = useConfigStore.getState();
      expect(state.error).toBe('config.fetchError');
      expect(state.isLoading).toBe(false);
    });

    it('should handle non-Error rejection', async () => {
      (configService.getFeatures as ReturnType<typeof vi.fn>).mockRejectedValue('Unknown error');

      await useConfigStore.getState().fetchFeatures();
      
      const state = useConfigStore.getState();
      expect(state.error).toBe('config.fetchError');
    });

    it('should clear previous error when fetching', async () => {
      act(() => {
        useConfigStore.setState({ error: 'Previous error' });
      });
      
      (configService.getFeatures as ReturnType<typeof vi.fn>).mockResolvedValue({
        websocket_enabled: true,
        websocket_notifications: true,
      });

      await useConfigStore.getState().fetchFeatures();
      
      expect(useConfigStore.getState().error).toBeNull();
    });
  });

  describe('setError', () => {
    it('should set error message', () => {
      act(() => {
        useConfigStore.getState().setError('Test error');
      });
      
      expect(useConfigStore.getState().error).toBe('Test error');
    });

    it('should clear error when null is passed', () => {
      act(() => {
        useConfigStore.setState({ error: 'Existing error' });
      });
      
      act(() => {
        useConfigStore.getState().setError(null);
      });
      
      expect(useConfigStore.getState().error).toBeNull();
    });
  });
});
