# Deployment Guide

Complete guide for deploying FastAPI-Enterprise-Boilerplate to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Database Setup](#database-setup)
- [Reverse Proxy Configuration](#reverse-proxy-configuration)
- [SSL/TLS Setup](#ssltls-setup)
- [Monitoring](#monitoring)
- [Backup and Recovery](#backup-and-recovery)
- [Security Checklist](#security-checklist)

---

## Prerequisites

### System Requirements

| Component | Minimum       | Recommended      |
| --------- | ------------- | ---------------- |
| CPU       | 2 cores       | 4+ cores         |
| RAM       | 2 GB          | 4+ GB            |
| Storage   | 20 GB         | 50+ GB SSD       |
| OS        | Ubuntu 22.04+ | Ubuntu 24.04 LTS |

### Required Software

```bash
# Docker & Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Verify installation
docker --version  # 24.0+
docker compose version  # 2.20+
```

---

## Environment Configuration

### Production Environment Variables

Create a `.env.production` file:

```bash
# ===========================================
# Application
# ===========================================
APP_NAME=MyApp
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false

# ===========================================
# Security (CHANGE THESE!)
# ===========================================
JWT_SECRET_KEY=your-super-secret-key-at-least-32-chars-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ===========================================
# Database
# SECURITY: Use app_user (not boilerplate) for RLS enforcement
# ===========================================
DATABASE_URL=postgresql+asyncpg://app_user:your-secure-password@db:5432/myapp
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30

# ===========================================
# Redis
# ===========================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# ===========================================
# Rate Limiting
# ===========================================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# ===========================================
# Observability
# ===========================================
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
LOG_LEVEL=INFO
LOG_FORMAT=json

# ===========================================
# CORS (comma-separated origins)
# ===========================================
CORS_ORIGINS=https://myapp.com,https://www.myapp.com
```

### Secrets Management

**Never commit secrets to version control!**

Options for managing secrets:

1. **Docker Secrets** (recommended for Docker Swarm)
2. **HashiCorp Vault**
3. **AWS Secrets Manager / GCP Secret Manager**
4. **Environment variables injected at runtime**

---

## Docker Deployment

### Production Docker Compose

Create `docker-compose.deploy.yml`:

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    restart: always
    env_file:
      - .env.production
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 512M

  db:
    image: postgres:17.7-alpine
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 1G

  redis:
    image: redis:7.4-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:1.29-alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

### Production Dockerfile

Create `backend/Dockerfile.prod`:

> **Note:** The actual [Dockerfile.prod](../backend/Dockerfile.prod) in the repo is the source of truth.
> This is a simplified reference.

```dockerfile
# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

COPY requirements-prod.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements-prod.txt

# Production stage
FROM python:3.14-slim

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser

WORKDIR /app

# Install runtime dependencies from builder
COPY --from=builder /install /usr/local

# Copy application (no tests, no scripts)
COPY --chown=appuser:appgroup app/ ./app/

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

# Run with Uvicorn (4 workers, uvloop)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", \
     "--loop", "uvloop", "--http", "httptools", \
     "--no-access-log"]
```

### Deploy Commands

```bash
# Build and start
docker compose -f docker-compose.deploy.yml up -d --build

# View logs
docker compose -f docker-compose.deploy.yml logs -f backend

# Run migrations
docker compose -f docker-compose.deploy.yml exec backend alembic upgrade head

# Create superuser
docker compose -f docker-compose.deploy.yml exec backend \
    python -m app.cli users create-superuser \
    --email admin@myapp.com

# Restart services
docker compose -f docker-compose.deploy.yml restart backend
```

---

## Production Security & Initial Setup

### ⚠️ Critical: Remove Development Users

**The database migrations automatically create 3 development users for testing purposes. These MUST be removed before production deployment.**

#### Development Users (Created by Migrations)

| Email                 | Password      | Role       | Purpose      |
| --------------------- | ------------- | ---------- | ------------ |
| `admin@example.com`   | `Admin123!`   | superadmin | Testing only |
| `manager@example.com` | `Manager123!` | admin      | Testing only |
| `user@example.com`    | `User123!`    | user       | Testing only |

> **⚠️ SECURITY RISK**: These users have known credentials and will compromise your production system if not removed!

#### Step 1: List Current Users

```bash
# List all users in the system
docker compose -f docker-compose.deploy.yml exec backend \
  python -m app.cli users list
```

#### Step 2: Remove Development Users

##### Option A: Using CLI (Recommended)

```bash
# Deactivate development users
docker compose -f docker-compose.deploy.yml exec backend \
  python -m app.cli users deactivate <user-id>

# Repeat for each development user
```

##### Option B: Direct SQL (Faster)

```sql
-- Connect to production database
docker compose -f docker-compose.deploy.yml exec db psql -U boilerplate -d myapp

-- Delete all development users
DELETE FROM users WHERE email IN (
  'admin@example.com',
  'manager@example.com',
  'user@example.com'
);

-- Verify deletion
SELECT email, first_name, last_name, is_active FROM users;
```

#### Step 3: Create Production Admin Account

```bash
# Create your production superuser
docker compose -f docker-compose.deploy.yml exec backend \
  python -m app.cli users create-superuser \
  --email admin@yourcompany.com \
  --first-name "Your" \
  --last-name "Name"

# You will be prompted for a secure password
# Use a strong password (recommended: 16+ characters, mixed case, numbers, symbols)
```

#### Step 4: Verify Production Setup

```bash
# List users to confirm only production accounts exist
docker compose -f docker-compose.deploy.yml exec backend \
  python -m app.cli users list --active

# Test login with your new admin account
curl -X POST https://api.yourcompany.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourcompany.com", "password": "YourSecurePassword"}'
```

### CLI Commands Reference

> **Note**: CLI commands are **manual administrative tools** - they do NOT run automatically on startup.

#### User Management

```bash
# Create superuser (interactive)
docker compose exec backend python -m app.cli users create-superuser

# List all users
docker compose exec backend python -m app.cli users list

# List only active users
docker compose exec backend python -m app.cli users list --active

# Activate a user
docker compose exec backend python -m app.cli users activate <user-id>

# Deactivate a user
docker compose exec backend python -m app.cli users deactivate <user-id>
```

#### Database Management

```bash
# Seed additional test data (DEVELOPMENT ONLY)
docker compose exec backend python -m app.cli db seed --users --roles --tenants

# Clear and reseed (DEVELOPMENT ONLY)
docker compose exec backend python -m app.cli db seed --clear

# Check database info
docker compose exec backend python -m app.cli db info

# Run migrations manually
docker compose exec backend alembic upgrade head
```

#### API Key Management

```bash
# Generate API key
docker compose exec backend python -m app.cli apikeys generate \
  --name "CI/CD Integration" \
  --user admin@yourcompany.com \
  --scopes "users:read,reports:read"

# Generate expiring key
docker compose exec backend python -m app.cli apikeys generate \
  --name "Temporary Access" \
  --user admin@yourcompany.com \
  --expires 30

# List API keys
docker compose exec backend python -m app.cli apikeys list

# Revoke API key
docker compose exec backend python -m app.cli apikeys revoke <key-id>
```

### Environment-Based Seeding (Alternative)

If you prefer to prevent development users from being created in the first place, you can modify the migration:

```python
# backend/alembic/versions/001_initial_schema.py

def upgrade() -> None:
    # ... existing table creation ...

    # Only seed development users in non-production environments
    import os
    if os.getenv('ENVIRONMENT', 'development') != 'production':
        op.execute("""
            INSERT INTO users (id, tenant_id, email, ...)
            -- development users
        """)
```

---

## Kubernetes Deployment

### Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: myapp

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: myapp
data:
  APP_NAME: "MyApp"
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
```

### Secret

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: backend-secrets
  namespace: myapp
type: Opaque
stringData:
  JWT_SECRET_KEY: "your-super-secret-key"
  DATABASE_URL: "postgresql+asyncpg://user:pass@postgres:5432/myapp"
  REDIS_PASSWORD: "redis-password"
```

### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: myregistry/myapp-backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: backend-secrets
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "2Gi"
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
```

### Service and Ingress

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: myapp
spec:
  selector:
    app: backend
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: backend-ingress
  namespace: myapp
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.myapp.com
      secretName: api-tls
  rules:
    - host: api.myapp.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 80
```

---

## Database Setup

### Initial Setup

```bash
# Run migrations
docker compose exec backend alembic upgrade head

# Seed default data
docker compose exec backend python -m app.cli db seed

# Create admin user
docker compose exec backend python -m app.cli users create-superuser \
    --email admin@myapp.com \
    --password "SecurePassword123!"
```

### Enable Row Level Security

```sql
-- Enable RLS on tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Create RLS policy
CREATE POLICY tenant_isolation ON users
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## Backup and Recovery

### Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/myapp_${TIMESTAMP}.sql.gz"

# Create backup
docker compose exec -T db pg_dump -U ${DB_USER} ${DB_NAME} | gzip > ${BACKUP_FILE}

# Keep only last 30 days
find ${BACKUP_DIR} -name "myapp_*.sql.gz" -mtime +30 -delete

echo "Backup created: ${BACKUP_FILE}"
```

---

## Reverse Proxy Configuration

### Nginx Configuration

```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format json escape=json '{'
        '"time":"$time_iso8601",'
        '"remote_addr":"$remote_addr",'
        '"method":"$request_method",'
        '"uri":"$request_uri",'
        '"status":$status,'
        '"body_bytes_sent":$body_bytes_sent,'
        '"request_time":$request_time,'
        '"upstream_response_time":"$upstream_response_time"'
    '}';

    access_log /var/log/nginx/access.log json;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
    limit_conn_zone $binary_remote_addr zone=conn:10m;

    # Upstream
    upstream backend {
        least_conn;
        server backend:8000;
        keepalive 32;
    }

    server {
        listen 80;
        server_name api.myapp.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.myapp.com;

        # SSL
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_session_timeout 1d;
        ssl_session_cache shared:SSL:50m;
        ssl_session_tickets off;

        # Modern TLS
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;

        # HSTS
        add_header Strict-Transport-Security "max-age=63072000" always;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # API proxy
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            limit_conn conn 10;

            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Connection "";

            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Static files
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

---

## SSL/TLS Setup

### Using Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.myapp.com

# Auto-renewal (added automatically)
sudo systemctl status certbot.timer
```

### Manual Certificate Setup

```bash
# Generate self-signed for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/privkey.pem \
    -out nginx/ssl/fullchain.pem \
    -subj "/CN=api.myapp.com"
```

---

## Monitoring

### Prometheus + Grafana Stack

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config", "/etc/otel-config.yaml"]
    volumes:
      - ./monitoring/otel-config.yaml:/etc/otel-config.yaml
    ports:
      - "4317:4317"
      - "4318:4318"

volumes:
  prometheus_data:
  grafana_data:
```

### Key Metrics to Monitor

| Metric                | Alert Threshold |
| --------------------- | --------------- |
| Request latency (p99) | > 500ms         |
| Error rate            | > 1%            |
| CPU usage             | > 80%           |
| Memory usage          | > 85%           |
| Database connections  | > 90% pool      |
| Redis memory          | > 80%           |

---

## Security Checklist

### Pre-Deployment

#### User & Access Management

- [ ] **DELETE all development users** (`admin@example.com`, `manager@example.com`, `user@example.com`)
- [ ] Create production admin account with **strong unique password** (16+ chars)
- [ ] Document production admin credentials in secure vault (1Password, Vault, etc.)
- [ ] Verify no test/demo users exist in database

#### Secrets & Configuration

- [ ] Generate **strong JWT secret** (32+ random characters)
- [ ] Change **all default passwords** (database, Redis, etc.)
- [ ] Use **environment variables** for all secrets (never commit to git)
- [ ] Enable **secrets rotation** policy

#### Network & Access

- [ ] Enable **HTTPS only** (disable HTTP)
- [ ] Configure **CORS** with specific allowed origins (no wildcards)
- [ ] Enable **rate limiting** on all public endpoints
- [ ] Review and **minimize exposed ports**
- [ ] Set up **firewall rules** (allow only necessary traffic)

#### Code & Dependencies

- [ ] Scan Docker images for **vulnerabilities** (`docker scan`)
- [ ] Update all dependencies to **latest secure versions**
- [ ] Remove or disable **debug/development features**
- [ ] Review code for **hardcoded credentials**

### Post-Deployment

#### Monitoring & Logging

- [ ] Enable automatic **security updates**
- [ ] Set up **log aggregation** (ELK, Loki, CloudWatch)
- [ ] Configure **intrusion detection** (fail2ban, ModSecurity)
- [ ] Set up **alerting** for suspicious activities
- [ ] Monitor **failed login attempts**

#### Backup & Recovery

- [ ] Enable **automated database backups**
- [ ] Test **disaster recovery** procedure
- [ ] Document **incident response** plan
- [ ] Set up **backup retention** policy (30 days recommended)
- [ ] Test **restore from backup** monthly

#### Compliance & Audit

- [ ] Document **incident response** procedures
- [ ] Review **access logs** for unauthorized attempts
- [ ] Perform **security audit** of API endpoints
- [ ] Verify **GDPR/compliance** requirements met

### Ongoing

- [ ] Rotate secrets quarterly
- [ ] Review access logs monthly
- [ ] Update dependencies weekly
- [ ] Perform security audits quarterly
- [ ] Test backups monthly

---

## Troubleshooting

### Common Issues

**Container won't start:**

```bash
# Check logs
docker compose logs backend

# Check health
docker compose ps

# Inspect container
docker inspect <container_id>
```

**Database connection issues:**

```bash
# Test connectivity
docker compose exec backend python -c "
from app.infrastructure.database.connection import engine
import asyncio
asyncio.run(engine.connect())
print('OK')
"

# Check PostgreSQL logs
docker compose logs db
```

**High memory usage:**

```bash
# Check container stats
docker stats

# Adjust pool size in .env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### Getting Help

- **Documentation:** <https://github.com/your-org/boilerplate/docs>
- **Issues:** <https://github.com/your-org/boilerplate/issues>
- **Discussions:** <https://github.com/your-org/boilerplate/discussions>
