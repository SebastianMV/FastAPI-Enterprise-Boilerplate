/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";
import { defineConfig } from "vitest/config";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Get API URL from environment or use localhost for dev
const apiUrl = process.env.VITE_API_URL || "http://localhost:8000";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    // WARNING: 0.0.0.0 exposes dev server on all network interfaces.
    // Docker overrides this via VITE_DEV_HOST env var.
    host: process.env.VITE_DEV_HOST || "localhost",
    hmr: {
      clientPort: 3000,
    },
    proxy: {
      // NOTE: secure: false disables TLS certificate verification for the
      // dev proxy target.  This is acceptable for local development only.
      // In production, nginx handles proxying with proper TLS.
      "/auth": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/users": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/roles": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/api-keys": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/mfa": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/tenants": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/oauth": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/search": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/dashboard": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/notifications": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/sessions": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/audit-logs": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/config": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/data-exchange": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/ws": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        ws: true,
        rewrite: (path) => `/api/v1${path}`,
      },
      "/api/v1": {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: process.env.VITE_SOURCEMAP === "true" ? "hidden" : false,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/test/**", "src/**/*.d.ts"],
      thresholds: {
        statements: 50,
        branches: 40,
        functions: 40,
        lines: 50,
      },
    },
  },
});
