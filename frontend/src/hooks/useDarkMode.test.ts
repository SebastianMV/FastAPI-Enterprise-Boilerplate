/**
 * Unit tests for useDarkMode hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDarkMode } from './useDarkMode';

describe('useDarkMode', () => {
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    length: 0,
    key: vi.fn(),
  };

  const matchMediaMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
    
    // Mock matchMedia
    matchMediaMock.mockReturnValue({
      matches: false,
      media: '(prefers-color-scheme: dark)',
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });
    
    Object.defineProperty(window, 'matchMedia', {
      value: matchMediaMock,
      writable: true,
    });
    
    // Reset document classes
    document.documentElement.classList.remove('dark');
  });

  afterEach(() => {
    document.documentElement.classList.remove('dark');
  });

  describe('Initial state', () => {
    it('should default to system theme when no preference is stored', () => {
      localStorageMock.getItem.mockReturnValue(null);
      
      const { result } = renderHook(() => useDarkMode());
      
      expect(result.current.theme).toBe('system');
    });

    it('should restore dark theme from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('dark');
      
      const { result } = renderHook(() => useDarkMode());
      
      expect(result.current.theme).toBe('dark');
    });

    it('should restore light theme from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('light');
      
      const { result } = renderHook(() => useDarkMode());
      
      expect(result.current.theme).toBe('light');
    });
  });

  describe('Theme application', () => {
    it('should add dark class when theme is dark', () => {
      localStorageMock.getItem.mockReturnValue('dark');
      
      renderHook(() => useDarkMode());
      
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should remove dark class when theme is light', () => {
      localStorageMock.getItem.mockReturnValue('light');
      document.documentElement.classList.add('dark');
      
      renderHook(() => useDarkMode());
      
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });

    it('should follow system preference when theme is system', () => {
      localStorageMock.getItem.mockReturnValue('system');
      matchMediaMock.mockReturnValue({
        matches: true, // System prefers dark
        media: '(prefers-color-scheme: dark)',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      });
      
      renderHook(() => useDarkMode());
      
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should follow light system preference', () => {
      localStorageMock.getItem.mockReturnValue('system');
      matchMediaMock.mockReturnValue({
        matches: false, // System prefers light
        media: '(prefers-color-scheme: dark)',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      });
      
      renderHook(() => useDarkMode());
      
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('Theme switching', () => {
    it('should switch to dark theme', () => {
      localStorageMock.getItem.mockReturnValue('light');
      
      const { result } = renderHook(() => useDarkMode());
      
      act(() => {
        result.current.setTheme('dark');
      });
      
      expect(result.current.theme).toBe('dark');
      expect(result.current.isDark).toBe(true);
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should switch to light theme', () => {
      localStorageMock.getItem.mockReturnValue('dark');
      
      const { result } = renderHook(() => useDarkMode());
      
      act(() => {
        result.current.setTheme('light');
      });
      
      expect(result.current.theme).toBe('light');
      expect(result.current.isDark).toBe(false);
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });

    it('should switch to system theme', () => {
      localStorageMock.getItem.mockReturnValue('dark');
      
      const { result } = renderHook(() => useDarkMode());
      
      act(() => {
        result.current.setTheme('system');
      });
      
      expect(result.current.theme).toBe('system');
    });
  });

  describe('localStorage persistence', () => {
    it('should save theme preference to localStorage', () => {
      localStorageMock.getItem.mockReturnValue('light');
      
      const { result } = renderHook(() => useDarkMode());
      
      act(() => {
        result.current.setTheme('dark');
      });
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark');
    });

    it('should save system preference to localStorage', () => {
      localStorageMock.getItem.mockReturnValue('dark');
      
      const { result } = renderHook(() => useDarkMode());
      
      act(() => {
        result.current.setTheme('system');
      });
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'system');
    });
  });

  describe('isDark state', () => {
    it('should be true when theme is dark', () => {
      localStorageMock.getItem.mockReturnValue('dark');
      
      const { result } = renderHook(() => useDarkMode());
      
      expect(result.current.isDark).toBe(true);
    });

    it('should be false when theme is light', () => {
      localStorageMock.getItem.mockReturnValue('light');
      
      const { result } = renderHook(() => useDarkMode());
      
      expect(result.current.isDark).toBe(false);
    });

    it('should reflect system preference when theme is system', () => {
      localStorageMock.getItem.mockReturnValue('system');
      matchMediaMock.mockReturnValue({
        matches: true,
        media: '(prefers-color-scheme: dark)',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      });
      
      const { result } = renderHook(() => useDarkMode());
      
      expect(result.current.isDark).toBe(true);
    });
  });

  describe('System preference changes', () => {
    it('should update when system preference changes (system theme)', () => {
      localStorageMock.getItem.mockReturnValue('system');
      
      let mediaChangeHandler: (() => void) | null = null;
      
      matchMediaMock.mockReturnValue({
        matches: false,
        media: '(prefers-color-scheme: dark)',
        addEventListener: (event: string, handler: () => void) => {
          if (event === 'change') {
            mediaChangeHandler = handler;
          }
        },
        removeEventListener: vi.fn(),
      });
      
      renderHook(() => useDarkMode());
      
      // Verify event listener was added
      expect(mediaChangeHandler).not.toBeNull();
    });

    it('should cleanup event listener on unmount', () => {
      localStorageMock.getItem.mockReturnValue('system');
      
      const removeEventListener = vi.fn();
      
      matchMediaMock.mockReturnValue({
        matches: false,
        media: '(prefers-color-scheme: dark)',
        addEventListener: vi.fn(),
        removeEventListener,
      });
      
      const { unmount } = renderHook(() => useDarkMode());
      
      unmount();
      
      expect(removeEventListener).toHaveBeenCalled();
    });
  });
});
