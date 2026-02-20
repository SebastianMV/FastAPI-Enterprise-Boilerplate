# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

# ============================================
# Production Dockerfile - Frontend
# Multi-stage build for optimized production image
# ============================================

# Stage 1: Dependencies
# Pin to LTS minor; update patch periodically: docker pull node:22.16-alpine
FROM node:22.16-alpine AS deps

WORKDIR /app

# Install dependencies only when package files change
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --legacy-peer-deps


# Stage 2: Builder
FROM node:22.16-alpine AS builder

WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the application
ENV NODE_ENV=production
RUN npm run build


# Stage 3: Production
# Pin to specific version for reproducibility.
# Update periodically and verify with: docker pull nginx:1.29-alpine
FROM nginx:1.29-alpine AS production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Security: Remove default nginx files
RUN rm -rf /usr/share/nginx/html/50x.html

# Security: Run as non-root user
USER nginx

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

# Expose port
EXPOSE 80

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
