/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Get API URL from environment or use localhost for dev
const apiUrl = process.env.VITE_API_URL || 'http://localhost:8000';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    hmr: {
      clientPort: 3000,
    },
    proxy: {
      '/auth': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/users': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/roles': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/api-keys': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/mfa': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/tenants': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/oauth': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/search': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/dashboard': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/notifications': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/sessions': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/audit-logs': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/config': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/data-exchange': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/ws': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        ws: true,
        rewrite: (path) => `/api/v1${path}`,
      },
      '/api/v1': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/test/**', 'src/**/*.d.ts'],
      thresholds: {
        statements: 30,
        branches: 25,
        functions: 25,
        lines: 30,
      },
    },
  },
});
