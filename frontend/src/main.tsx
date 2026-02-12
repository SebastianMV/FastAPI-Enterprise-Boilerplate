import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';
import './i18n'; // Initialize i18n

// Initialize theme from localStorage before first render to avoid flash
const initializeTheme = () => {
  const raw = localStorage.getItem('theme');
  const VALID_THEMES = ['light', 'dark', 'system'] as const;
  const theme = (VALID_THEMES as readonly string[]).includes(raw ?? '') ? (raw as typeof VALID_THEMES[number]) : 'system';
  
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else if (theme === 'light') {
    document.documentElement.classList.remove('dark');
  } else {
    // System preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }
};

initializeTheme();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: (failureCount, error) => {
        if (failureCount >= 1) return false;
        const status = error instanceof Error && 'response' in error
          ? (error as { response?: { status?: number } }).response?.status
          : undefined;
        if (status === 401 || status === 403) return false;
        return true;
      },
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
