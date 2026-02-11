# 📚 Documentation

> FastAPI Enterprise Boilerplate v0.9.0 — Complete Documentation Index

---

## 🚀 Getting Started

| Document | Purpose | Audience |
|----------|---------|----------|
| [GETTING_STARTED.md](./GETTING_STARTED.md) | Complete setup guide (Docker + local dev) | ⭐ **New Users** |
| [DOCKER.md](./DOCKER.md) | Docker configuration, dev vs prod, troubleshooting | 🐳 **Docker Users** |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Production deployment (Docker, K8s, SSL, monitoring) | 🚀 **DevOps** |

---

## 🔐 Security & Authentication

| Document | Description |
|----------|-------------|
| [SECURITY.md](./SECURITY.md) | Security features, audit, OWASP compliance, best practices |
| [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) | Per-PR security checklist (from 13 security audits) |
| [OAUTH2_SSO.md](./OAUTH2_SSO.md) | Social login (Google, GitHub, Microsoft, Discord) |
| [RLS_SETUP.md](./RLS_SETUP.md) | Row-Level Security for multi-tenant data isolation |

---

## 📖 Feature Documentation

| Document | Description |
|----------|-------------|
| [API_REFERENCE.md](./API_REFERENCE.md) | Complete REST API documentation with curl examples |
| [WEBSOCKET.md](./WEBSOCKET.md) | Real-time features, message types, React integration |
| [FULL_TEXT_SEARCH.md](./FULL_TEXT_SEARCH.md) | PostgreSQL Full-Text Search with GIN indexes |
| [I18N.md](./I18N.md) | Internationalization guide (EN/ES/PT) |
| [EMAIL_TEMPLATES.md](./EMAIL_TEMPLATES.md) | Email template system and pluggable providers |

---

## 📊 Data Management

| Document | Description |
|----------|-------------|
| [DATA_EXCHANGE.md](./DATA_EXCHANGE.md) | Import/Export/Reports system with dynamic entity config |
| [BULK_OPERATIONS.md](./BULK_OPERATIONS.md) | Batch CRUD API for users/roles |
| [PDF_EXCEL_FEATURES.md](./PDF_EXCEL_FEATURES.md) | Advanced PDF (WeasyPrint) & Excel (openpyxl) generation |

---

## 📋 Project-Level Documentation

| File | Description |
|------|-------------|
| [README.md](../README.md) | Project overview, quick start, features, architecture |
| [CHANGELOG.md](../CHANGELOG.md) | Version history and release notes |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines |
| [PROJECT_STATUS.md](../PROJECT_STATUS.md) | Current status, metrics, and roadmap to v1.0.0 |
| [MAKEFILE.md](../MAKEFILE.md) | Cross-platform Make/PowerShell command reference |

---

## 🗂️ Documentation by Role

### For Developers
1. **Setup** → [GETTING_STARTED.md](./GETTING_STARTED.md)
2. **API** → [API_REFERENCE.md](./API_REFERENCE.md)
3. **Security** → [SECURITY.md](./SECURITY.md)
4. **PR Checklist** → [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md)
5. **i18n** → [I18N.md](./I18N.md)
6. **Real-time** → [WEBSOCKET.md](./WEBSOCKET.md)

### For DevOps
1. **Deploy** → [DEPLOYMENT.md](./DEPLOYMENT.md)
2. **Docker** → [DOCKER.md](./DOCKER.md)
3. **Database** → [RLS_SETUP.md](./RLS_SETUP.md)
4. **Security** → [SECURITY.md](./SECURITY.md)

### For Contributors
1. **Guidelines** → [CONTRIBUTING.md](../CONTRIBUTING.md)
2. **Status** → [PROJECT_STATUS.md](../PROJECT_STATUS.md)
3. **Changes** → [CHANGELOG.md](../CHANGELOG.md)

---

## 🚨 Before Production

- 🔴 Delete development users — see [DEPLOYMENT.md](./DEPLOYMENT.md#production-security--initial-setup)
- 🔴 Change all default passwords and secrets
- 🔴 Use `app_user` database role for RLS enforcement
- 🔴 Review the [Pre-Production Security Checklist](../PROJECT_STATUS.md#-pre-production-security-checklist)
