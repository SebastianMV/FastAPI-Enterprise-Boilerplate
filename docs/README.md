# 📚 Documentation Index

> FastAPI Enterprise Boilerplate - Complete Documentation

---

## 🚀 Quick Start

| Document | Purpose | For |
| -------- | ------- | --- |
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Complete setup guide for development and production | ⭐ **New Users** |
| [TECHNICAL_OVERVIEW.md](./TECHNICAL_OVERVIEW.md) | Architecture, design patterns, and technical decisions | 🏗️ **Developers** |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Production deployment guide (Docker, Kubernetes) | 🚀 **DevOps** |

---

## 📖 Feature Documentation

### Authentication & Security

| Document | Description |
| -------- | ----------- |
| [SECURITY.md](./SECURITY.md) | Complete security guide, audit, and best practices (500+ lines) |
| [OAUTH2_SSO.md](./OAUTH2_SSO.md) | Social login integration (Google, GitHub, Microsoft, Discord) |
| [RLS_SETUP.md](./RLS_SETUP.md) | Row-Level Security for multi-tenant isolation |

### Infrastructure & Communication

| Document | Description |
| -------- | ----------- |
| [DOCKER.md](./DOCKER.md) | Complete Docker setup and troubleshooting |
| [WEBSOCKET.md](./WEBSOCKET.md) | Real-time features and WebSocket implementation |
| [EMAIL_TEMPLATES.md](./EMAIL_TEMPLATES.md) | Email system and templates (17 complete) |
| [FULL_TEXT_SEARCH.md](./FULL_TEXT_SEARCH.md) | PostgreSQL + Elasticsearch search |

### Frontend & API

| Document | Description |
| -------- | ----------- |
| [I18N.md](./I18N.md) | Internationalization guide (100% coverage, EN/ES/PT active, FR/DE available) |
| [API_REFERENCE.md](./API_REFERENCE.md) | Complete REST API documentation |

---

## 📊 Project Documentation (Root Level)

| File | Description |
| ---- | ----------- |
| [README.md](../README.md) | Project overview and quick start |
| [CHANGELOG.md](../CHANGELOG.md) | Version history and release notes |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines |
| [PROJECT_STATUS.md](../PROJECT_STATUS.md) | Current status, metrics, and roadmap |
| [ROADMAP.md](../ROADMAP.md) | Future plans and features |
| [MAKEFILE.md](../MAKEFILE.md) | PowerShell commands for Windows |
| [GITHUB_SETUP.md](../GITHUB_SETUP.md) | GitHub Actions and CI/CD setup |
| [AGENTS.md](../AGENTS.md) | Context for AI agents (private) |

---

## 🗂️ Documentation by Role

### For Developers

1. **Setup:** [GETTING_STARTED.md](./GETTING_STARTED.md)
2. **Architecture:** [TECHNICAL_OVERVIEW.md](./TECHNICAL_OVERVIEW.md)
3. **Security:** [SECURITY.md](./SECURITY.md)
4. **i18n:** [I18N.md](./I18N.md)
5. **API:** [API_REFERENCE.md](./API_REFERENCE.md)
6. **Real-time:** [WEBSOCKET.md](./WEBSOCKET.md)

### For DevOps

1. **Deploy:** [DEPLOYMENT.md](./DEPLOYMENT.md)
2. **Docker:** [DOCKER.md](./DOCKER.md)
3. **Security:** [SECURITY.md](./SECURITY.md)
4. **Database:** [RLS_SETUP.md](./RLS_SETUP.md)

### For Contributors

1. **Guidelines:** [CONTRIBUTING.md](../CONTRIBUTING.md)
2. **Status:** [PROJECT_STATUS.md](../PROJECT_STATUS.md)
3. **Changes:** [CHANGELOG.md](../CHANGELOG.md)
4. **Roadmap:** [ROADMAP.md](../ROADMAP.md)

## 🚨 Important Security Notes

**Before Production:**

- 🔴 Delete development users (see [DEPLOYMENT.md#production-security--initial-setup](./DEPLOYMENT.md#production-security--initial-setup))
- 🔴 Change all default passwords and secrets
- 🔴 Use `app_user` database role for RLS enforcement

## 📝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.
