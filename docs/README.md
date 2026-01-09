# Documentation Index

Welcome to the FastAPI Enterprise Boilerplate documentation! 

## 🚀 Getting Started

| Document | Purpose |
|----------|---------|
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Complete setup guide for development and production |
| [DOCKER.md](./DOCKER.md) | Docker configuration and troubleshooting |

## 🏗️ Architecture & Design

| Document | Purpose |
|----------|---------|
| [TECHNICAL_OVERVIEW.md](./TECHNICAL_OVERVIEW.md) | **Start here!** Comprehensive technical documentation |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Hexagonal architecture patterns and principles |

## 🔐 Security & Production

| Document | Purpose |
|----------|---------|
| [DEPLOYMENT.md](./DEPLOYMENT.md) | **Production deployment guide** with security setup |
| [SECURITY_AUDIT.md](./SECURITY_AUDIT.md) | Security measures and audit results |
| ~~[PRODUCTION_DATABASE_CONFIG.md](./PRODUCTION_DATABASE_CONFIG.md)~~ | ⚠️ Deprecated - See DEPLOYMENT.md instead |

## 🔧 Features & Configuration

| Document | Purpose |
|----------|---------|
| [API_REFERENCE.md](./API_REFERENCE.md) | API endpoints and usage examples |
| [OAUTH2_SSO.md](./OAUTH2_SSO.md) | OAuth2/SSO integration guide |
| [FULL_TEXT_SEARCH.md](./FULL_TEXT_SEARCH.md) | Full-text search setup and usage |
| [WEBSOCKET.md](./WEBSOCKET.md) | Real-time WebSocket features |
| [EMAIL_TEMPLATES.md](./EMAIL_TEMPLATES.md) | Email system configuration |
| [RLS_SETUP.md](./RLS_SETUP.md) | Row-Level Security for multi-tenancy |

## 📚 Quick Links

### For Developers
1. Start with [GETTING_STARTED.md](./GETTING_STARTED.md)
2. Understand architecture in [TECHNICAL_OVERVIEW.md](./TECHNICAL_OVERVIEW.md)
3. Check [API_REFERENCE.md](./API_REFERENCE.md) for endpoints

### For DevOps/Deployment
1. Read [DEPLOYMENT.md](./DEPLOYMENT.md) - **Production Security & Initial Setup**
2. Configure with [DOCKER.md](./DOCKER.md)
3. Review [SECURITY_AUDIT.md](./SECURITY_AUDIT.md)

## 🚨 Important Security Notes

**Before Production:**
- 🔴 Delete development users (see [DEPLOYMENT.md#production-security--initial-setup](./DEPLOYMENT.md#production-security--initial-setup))
- 🔴 Change all default passwords and secrets
- 🔴 Use `app_user` database role for RLS enforcement

## 📝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.
