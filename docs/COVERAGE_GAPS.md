# 📊 Coverage Gaps - Modules Below 95%

**Generated:** January 15, 2026  
**Current Coverage:** 94%  
**Modules Below 95%:** 63

---

## 🎯 Priority Breakdown

### 🔴 Critical (< 60% coverage)

**High Impact Endpoints:**

| Module | Coverage | Missing Statements | Priority |
| --- | --- | --- | --- |
| `app/api/v1/endpoints/auth.py` | 58% | 119 | 🔴 Critical |
| `app/api/v1/endpoints/mfa.py` | 43% | 54 | 🔴 Critical |
| `app/application/services/oauth_service.py` | 51% | 100 | 🔴 Critical |
| `app/api/v1/endpoints/sessions.py` | 50% | 35 | 🔴 Critical |
| `app/api/v1/endpoints/audit_logs.py` | 44% | 35 | 🔴 Critical |

**CLI Commands:**

| Module | Coverage | Missing Statements | Priority |
| --- | --- | --- | --- |
| `app/cli/commands/database.py` | 16% | 127 | 🟡 Medium |
| `app/cli/commands/apikeys.py` | 21% | 121 | 🟡 Medium |
| `app/cli/commands/users.py` | 32% | 66 | 🟡 Medium |
| `app/cli/main.py` | 38% | 18 | 🟡 Medium |

---

### 🟡 Medium Priority (60-80% coverage)

**Application Services:**

| Module | Coverage | Missing Statements |
| --- | --- | --- |
| `app/application/services/audit_service.py` | 75% | 9 |
| `app/cli/utils.py` | 79% | 12 |
| `app/infrastructure/search/__init__.py` | 79% | 5 |

**Infrastructure:**

| Module | Coverage | Missing Statements |
| --- | --- | --- |
| `app/infrastructure/auth/oauth_providers.py` | 77% | 32 |
| `app/infrastructure/database/models/role.py` | 71% | 12 |
| `app/infrastructure/email/templates.py` | 84% | 13 |
| `app/infrastructure/database/repositories/session_repository.py` | 84% | 10 |

---

### 🟢 Low Priority (80-95% coverage)

**Nearly Complete Endpoints:**

| Module | Coverage | Missing Statements |
| --- | --- | --- |
| `app/api/v1/endpoints/users.py` | 83% | 25 |
| `app/api/v1/endpoints/websocket.py` | 91% | 12 |
| `app/api/v1/endpoints/roles.py` | 93% | 8 |
| `app/api/v1/endpoints/tenants.py` | 94% | 7 |
| `app/api/v1/endpoints/config.py` | 92% | 1 |

**Infrastructure Components:**

| Module | Coverage | Missing Statements |
| --- | --- | --- |
| `app/infrastructure/cache/cache_service.py` | 92% | 16 |
| `app/infrastructure/database/connection.py` | 88% | 8 |
| `app/infrastructure/observability/logging.py` | 87% | 13 |
| `app/infrastructure/search/elasticsearch.py` | 88% | 30 |
| `app/infrastructure/storage/__init__.py` | 88% | 6 |
| `app/infrastructure/observability/telemetry.py` | 93% | 9 |

**Domain Entities:**

| Module | Coverage | Missing Statements |
| --- | --- | --- |
| `app/domain/entities/user.py` | 89% | 9 |

**Schemas:**

| Module | Coverage | Missing Statements |
| --- | --- | --- |
| `app/api/v1/schemas/common.py` | 94% | 2 |
| `app/infrastructure/database/models/mfa.py` | 94% | 1 |

---

## 📈 Recommended Action Plan

### Phase 1: Critical Endpoints (Target: +200 statements)

1. **Auth Endpoints** (119 statements)
   - Integration tests for login flows
   - MFA verification paths
   - Password reset flows
   - OAuth integration points

2. **MFA Endpoints** (54 statements)
   - TOTP setup and verification
   - Backup codes generation/use
   - MFA disable flows

3. **OAuth Service** (100 statements)
   - Provider-specific flows
   - Token exchange edge cases
   - Error handling paths

4. **Sessions & Audit** (70 statements)
   - Session lifecycle tests
   - Audit log creation scenarios

### Phase 2: CLI Commands (Target: +300 statements)

- Create integration tests with test database
- Cover async execution paths
- Test error scenarios and validations

### Phase 3: Polish (Target: +50 statements)

- Complete remaining endpoints to 95%+
- Add edge case coverage for infrastructure
- Domain entity validation scenarios

---

## 🎯 Target Milestones

| Milestone | Coverage Goal | Est. Tests Needed |
| --- | --- | --- |
| **v1.3.4** | 95% | ~80 tests |
| **v1.4.0** | 96% | ~120 tests |
| **v1.5.0** | 97%+ | ~150 tests |

---

## 📝 Notes

- **Current strength:** Infrastructure layer (WebSocket 87%, Storage 99%, Repositories 90%+)
- **Main gap:** API endpoints and CLI commands need integration tests
- **Strategy:** Focus on integration tests for endpoints, unit tests for services
- **Tooling:** Use pytest fixtures for common setup, TestClient for API tests

---

**Last Updated:** January 15, 2026
**Auto-generated from:** `coverage report --skip-covered`
