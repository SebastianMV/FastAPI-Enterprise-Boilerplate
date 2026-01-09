# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

# ============================================
# Production Dockerfile - Frontend
# Multi-stage build for optimized production image
# ============================================

# Stage 1: Dependencies
FROM node:22-alpine AS deps

WORKDIR /app

# Install dependencies only when package files change
COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile


# Stage 2: Builder
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the application
ENV NODE_ENV=production
RUN npm run build


# Stage 3: Production
FROM nginx:alpine AS production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Security: Remove default nginx files
RUN rm -rf /usr/share/nginx/html/50x.html

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

# Expose port
EXPOSE 80

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
