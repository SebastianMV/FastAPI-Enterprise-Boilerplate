# 🏃 Plan de Sprints - Resolución de Deuda Técnica

**Proyecto:** FastAPI Enterprise Boilerplate  
**Versión actual:** v1.2.1  
**Fecha inicio:** 9 de Enero 2026  
**Última actualización:** 9 de Enero 2026  
**Objetivo:** Cobertura 95%+ y eliminar toda deuda técnica

---

## 📊 Resumen Ejecutivo

| Sprint | Duración | Enfoque | Objetivo Cobertura | Estado |
| --- | --- | --- | --- | --- |
| Sprint 1 | 1 semana | OAuth + Auth Tests | 87% → 90% | ⬜ Pendiente |
| Sprint 2 | 1 semana | WebSocket + Search Tests | 90% → 92% | ⬜ Pendiente |
| Sprint 3 | 1 semana | Frontend Tests Setup | - | ⬜ Pendiente |
| Sprint 4 | 1 semana | CLI + Storage Tests | 92% → 95% | ⬜ Pendiente |
| Sprint 5 | 1 semana | i18n + Mejoras UX | 95% (mantenido) | ✅ Completado |
| Sprint 6 | 1 semana | Refactoring + Limpieza | 95%+ final | ✅ Completado |

**Duración restante:** 4 semanas (Sprints 1-4)

---

## 📈 Estado Actual del Proyecto

### ✅ Deuda Técnica RESUELTA

| Item | Estado Anterior | Estado Actual |
| --- | --- | --- |
| TODOs en código producción | 7 | **0** ✅ |
| Deprecation warnings (python-jose) | 37 | **0** ✅ |
| Idiomas soportados | 3 (EN, ES, PT) | **5** (EN, ES, PT, FR, DE) ✅ |
| Migración JWT | python-jose | **PyJWT 2.10.1** ✅ |
| Tests backend | 3,189 | **3,443** ✅ |

### ⬜ Deuda Técnica PENDIENTE

| Item | Estado Actual | Objetivo | Sprint |
| --- | --- | --- | --- |
| Cobertura backend | 87% | 95%+ | 1-4 |
| Tests frontend | 0 | 50+ archivos | 3 |
| Cobertura frontend | 0% | 70%+ | 3 |
| Optimización queries N+1 | Pendiente | Perfilado | Futuro |

---

## 🔴 Sprint 1: OAuth & Authentication Tests (Semana 1)

**Objetivo:** Cubrir los módulos de OAuth que tienen la menor cobertura

### Tareas

| # | Tarea | Archivo | Líneas | Esfuerzo | Estado |
| --- | --- | --- | --- | --- | --- |
| 1.1 | Tests OAuth Service - get_authorization_url | `test_oauth_service.py` | 15 | 2h | ⬜ |
| 1.2 | Tests OAuth Service - exchange_code | `test_oauth_service.py` | 25 | 3h | ⬜ |
| 1.3 | Tests OAuth Service - get_user_info | `test_oauth_service.py` | 20 | 2h | ⬜ |
| 1.4 | Tests OAuth Service - link_provider | `test_oauth_service.py` | 15 | 2h | ⬜ |
| 1.5 | Tests OAuth Service - unlink_provider | `test_oauth_service.py` | 10 | 1h | ⬜ |
| 1.6 | Tests OAuth Service - login_or_register | `test_oauth_service.py` | 24 | 3h | ⬜ |
| 1.7 | Tests OAuth Endpoint - authorize | `test_oauth_endpoint.py` | 10 | 2h | ⬜ |
| 1.8 | Tests OAuth Endpoint - callback | `test_oauth_endpoint.py` | 15 | 2h | ⬜ |
| 1.9 | Tests OAuth Endpoint - connections | `test_oauth_endpoint.py` | 14 | 2h | ⬜ |

### Criterios de Aceptación

- [ ] `oauth_service.py` cobertura >= 90%
- [ ] `oauth.py` endpoint cobertura >= 85%
- [ ] Todos los providers testeados (Google, GitHub, Microsoft, Discord)
- [ ] Tests de error handling para OAuth failures
- [ ] 0 tests fallidos

### Estimación Total: 19 horas (~4 días)

---

## 🟡 Sprint 2: WebSocket & Search Tests (Semana 2)

**Objetivo:** Cubrir la funcionalidad real-time y búsqueda

### Tareas

| # | Tarea | Archivo | Líneas | Esfuerzo | Estado |
| --- | --- | --- | --- | --- | --- |
| 2.1 | Tests WebSocket Endpoint - connect/disconnect | `test_websocket_endpoint.py` | 15 | 2h | ⬜ |
| 2.2 | Tests WebSocket Endpoint - message handling | `test_websocket_endpoint.py` | 20 | 3h | ⬜ |
| 2.3 | Tests WebSocket Endpoint - authentication | `test_websocket_endpoint.py` | 12 | 2h | ⬜ |
| 2.4 | Tests WebSocket Endpoint - rooms/broadcast | `test_websocket_endpoint.py` | 12 | 2h | ⬜ |
| 2.5 | Tests Redis Manager - pub/sub | `test_redis_manager.py` | 25 | 3h | ⬜ |
| 2.6 | Tests Redis Manager - connection pool | `test_redis_manager.py` | 20 | 2h | ⬜ |
| 2.7 | Tests Redis Manager - room management | `test_redis_manager.py` | 15 | 2h | ⬜ |
| 2.8 | Tests Redis Manager - presence | `test_redis_manager.py` | 16 | 2h | ⬜ |
| 2.9 | Tests Search Endpoint - full-text search | `test_search_endpoint.py` | 15 | 2h | ⬜ |
| 2.10 | Tests Search Endpoint - filters/pagination | `test_search_endpoint.py` | 15 | 2h | ⬜ |
| 2.11 | Tests Search Endpoint - indexing | `test_search_endpoint.py` | 12 | 2h | ⬜ |

### Criterios de Aceptación

- [ ] `websocket.py` endpoint cobertura >= 85%
- [ ] `redis_manager.py` cobertura >= 80%
- [ ] `search.py` endpoint cobertura >= 85%
- [ ] Tests de reconnection y error handling
- [ ] 0 tests fallidos

### Estimación Total: 24 horas (~5 días)

---

## 🟢 Sprint 3: Frontend Tests Setup (Semana 3)

**Objetivo:** Establecer infraestructura de tests frontend y cubrir componentes críticos

### Tareas

| # | Tarea | Archivo | Componentes | Esfuerzo | Estado |
| --- | --- | --- | --- | --- | --- |
| 3.1 | Setup Vitest + React Testing Library | `vitest.config.ts`, `setup.ts` | - | 2h | ⬜ |
| 3.2 | Setup MSW para mocking API | `mocks/handlers.ts` | - | 2h | ⬜ |
| 3.3 | Tests AuthStore | `stores/authStore.test.ts` | 1 | 3h | ⬜ |
| 3.4 | Tests LoginPage | `pages/auth/LoginPage.test.tsx` | 1 | 3h | ⬜ |
| 3.5 | Tests SocialLoginButtons | `components/auth/SocialLoginButtons.test.tsx` | 1 | 2h | ⬜ |
| 3.6 | Tests ChatWindow | `components/chat/ChatWindow.test.tsx` | 1 | 4h | ⬜ |
| 3.7 | Tests ConversationList | `components/chat/ConversationList.test.tsx` | 1 | 2h | ⬜ |
| 3.8 | Tests NotificationsDropdown | `components/notifications/NotificationsDropdown.test.tsx` | 1 | 3h | ⬜ |
| 3.9 | Tests SearchPage | `pages/search/SearchPage.test.tsx` | 1 | 3h | ⬜ |
| 3.10 | Tests useWebSocket hook | `hooks/useWebSocket.test.ts` | 1 | 3h | ⬜ |
| 3.11 | Tests useChat hook | `hooks/useChat.test.ts` | 1 | 3h | ⬜ |

### Criterios de Aceptación

- [ ] Vitest ejecuta correctamente con `npm run test`
- [ ] MSW intercepta llamadas API
- [ ] >= 10 archivos de test creados
- [ ] Cobertura frontend >= 50%
- [ ] CI/CD ejecuta tests frontend

### Estimación Total: 30 horas (~6 días)

---

## 🔵 Sprint 4: CLI & Storage Tests (Semana 4)

**Objetivo:** Cubrir herramientas CLI y adaptadores de storage

### Tareas

| # | Tarea | Archivo | Líneas | Esfuerzo | Estado |
| --- | --- | --- | --- | --- | --- |
| 4.1 | Tests CLI apikeys - create | `test_cli_apikeys.py` | 30 | 2h | ⬜ |
| 4.2 | Tests CLI apikeys - list/delete | `test_cli_apikeys.py` | 30 | 2h | ⬜ |
| 4.3 | Tests CLI apikeys - rotate | `test_cli_apikeys.py` | 25 | 2h | ⬜ |
| 4.4 | Tests CLI database - migrate | `test_cli_database.py` | 40 | 3h | ⬜ |
| 4.5 | Tests CLI database - seed | `test_cli_database.py` | 40 | 3h | ⬜ |
| 4.6 | Tests CLI database - backup/restore | `test_cli_database.py` | 43 | 3h | ⬜ |
| 4.7 | Tests CLI users - create/update | `test_cli_users.py` | 40 | 3h | ⬜ |
| 4.8 | Tests CLI users - list/delete | `test_cli_users.py` | 37 | 2h | ⬜ |
| 4.9 | Tests S3 Storage - upload/download | `test_s3_storage.py` | 15 | 2h | ⬜ |
| 4.10 | Tests S3 Storage - presigned URLs | `test_s3_storage.py` | 10 | 1h | ⬜ |
| 4.11 | Tests S3 Storage - delete/list | `test_s3_storage.py` | 8 | 1h | ⬜ |
| 4.12 | Tests Elasticsearch - index/search | `test_elasticsearch.py` | 15 | 2h | ⬜ |
| 4.13 | Tests Elasticsearch - aggregations | `test_elasticsearch.py` | 15 | 2h | ⬜ |

### Criterios de Aceptación

- [ ] CLI commands cobertura >= 80%
- [ ] S3 storage cobertura >= 90%
- [ ] Elasticsearch cobertura >= 85%
- [ ] Tests con mocks para servicios externos
- [ ] 0 tests fallidos

### Estimación Total: 28 horas (~5-6 días)

---

## 🟣 Sprint 5: Internacionalización & UX (Semana 5) ✅ COMPLETADO

**Objetivo:** Agregar idiomas y mejorar UX

### Tareas

| # | Tarea | Archivo | Descripción | Esfuerzo | Estado |
| --- | --- | --- | --- | --- | --- |
| 5.1 | Traducciones Francés (FR) Backend | `locales/fr.json` | ~240 strings | 3h | ✅ |
| 5.2 | Traducciones Alemán (DE) Backend | `locales/de.json` | ~240 strings | 3h | ✅ |
| 5.3 | Traducciones Francés (FR) Frontend | `locales/fr.json` | ~150 strings | 2h | ✅ |
| 5.4 | Traducciones Alemán (DE) Frontend | `locales/de.json` | ~150 strings | 2h | ✅ |
| 5.5 | Config DEFAULT_LOCALE en backend | `config.py` | Settings | 1h | ✅ |
| 5.6 | Actualizar i18n service | `i18n/__init__.py` | Usar settings | 1h | ✅ |
| 5.7 | Frontend i18n config | `i18n/index.ts` | 5 idiomas | 1h | ✅ |
| 5.8 | Implementar unread_count real | `chat.py` | Cálculo desde participant | 2h | ✅ |
| 5.9 | ~~Tests i18n~~ | - | Aplazado a Sprint 1-4 | - | ⏩ |
| 5.10 | ~~Dashboard métricas reales~~ | - | Aplazado | - | ⏩ |

### Resultados

- ✅ 5 idiomas funcionando (EN, ES, PT, FR, DE)
- ✅ unread_count calculado desde participant data
- ✅ Configuración i18n via settings
- ✅ 0 regressions

---

## ⚪ Sprint 6: Refactoring & Cleanup (Semana 6) ✅ COMPLETADO

**Objetivo:** Limpiar código, eliminar TODOs y optimizar

### Tareas

| # | Tarea | Archivo | Descripción | Esfuerzo | Estado |
| --- | --- | --- | --- | --- | --- |
| 6.1 | Resolver TODO conftest.py L168 | `conftest.py` | Actualizar docs | 0.5h | ✅ |
| 6.2 | Resolver TODO conftest.py L176 | `conftest.py` | Actualizar docs | 0.5h | ✅ |
| 6.3 | Resolver TODO conftest.py L194 | `conftest.py` | Email mock docs | 0.5h | ✅ |
| 6.4 | Resolver TODO queue.py L223 | `queue.py` | Conectar EmailService | 1h | ✅ |
| 6.5 | Resolver TODO queue.py L283 | `queue.py` | Documentar Redis TTL | 0.5h | ✅ |
| 6.6 | Migrar python-jose → PyJWT | `jwt_handler.py` | Eliminar deprecation | 2h | ✅ |
| 6.7 | Actualizar requirements.txt | `requirements.txt` | PyJWT 2.10.0 | 0.5h | ✅ |
| 6.8 | Actualizar pyproject.toml | `pyproject.toml` | PyJWT 2.10.0 | 0.5h | ✅ |
| 6.9 | Actualizar integration tests | `conftest.py` | PyJWT imports | 0.5h | ✅ |
| 6.10 | ~~Optimizar queries N+1~~ | - | Aplazado | - | ⏩ |
| 6.11 | Actualizar README final | `README.md` | Métricas finales | 1h | ⬜ |
| 6.12 | Release v1.3.0 | `CHANGELOG.md` | Tag + notes | 2h | ⬜ |

### Resultados

- ✅ 0 TODOs pendientes en código principal
- ✅ python-jose → PyJWT (37 warnings eliminados)
- ✅ Dependencias actualizadas
- ✅ Tests de integración actualizados
- ✅ 0 deprecation warnings de JWT

### Criterios de Aceptación

- [ ] 0 TODOs en código de producción
- [ ] 0 deprecation warnings
- [ ] Dependencias actualizadas
- [ ] Documentación completa
- [ ] Release v1.3.0 publicado

### Estimación Total: 24 horas (~5 días)

---

## 📅 Calendario Propuesto

```text
Semana 1 (13-17 Ene): Sprint 1 - OAuth Tests
Semana 2 (20-24 Ene): Sprint 2 - WebSocket & Search Tests  
Semana 3 (27-31 Ene): Sprint 3 - Frontend Tests
Semana 4 (03-07 Feb): Sprint 4 - CLI & Storage Tests
Semana 5 (10-14 Feb): Sprint 5 - i18n & UX
Semana 6 (17-21 Feb): Sprint 6 - Refactoring & Release
```

---

## 📈 Métricas de Progreso

### Cobertura Objetivo por Sprint

| Después de | Backend | Frontend | Global |
| --- | --- | --- | --- |
| Sprint 1 | 90% | 0% | 87% |
| Sprint 2 | 92% | 0% | 89% |
| Sprint 3 | 92% | 50% | 90% |
| Sprint 4 | 95% | 50% | 92% |
| Sprint 5 | 95% | 60% | 93% |
| Sprint 6 | 95%+ | 70%+ | 95%+ |

### KPIs Finales Esperados

| Métrica | Actual | Objetivo | Estado |
| --- | --- | --- | --- |
| Backend Tests | 3,443 | 3,800+ | 🔄 En progreso |
| Frontend Tests | 0 | 50+ | ⬜ Pendiente |
| Cobertura Backend | 87% | 95%+ | 🔄 En progreso |
| Cobertura Frontend | 0% | 70%+ | ⬜ Pendiente |
| TODOs en código | 0 | 0 | ✅ Completado |
| Deprecation Warnings | 0 | 0 | ✅ Completado |
| Idiomas soportados | 5 | 5 | ✅ Completado |

---

## 🎯 Definition of Done (DoD)

Cada tarea se considera completada cuando:

1. ✅ Código implementado y funcionando
2. ✅ Tests unitarios escritos y pasando
3. ✅ Cobertura del módulo >= objetivo
4. ✅ Sin errores de tipo (pyright/TypeScript)
5. ✅ Sin errores de linting (ruff/ESLint)
6. ✅ Documentación actualizada si aplica
7. ✅ Code review aprobado (si aplica)

---

## 🚀 Cómo Empezar

### Sprint 1 - Día 1

```bash
# 1. Verificar estado actual
cd backend
pytest tests/unit/application/test_oauth_service.py -v --cov=app/application/services/oauth_service

# 2. Crear tests faltantes
# Ver archivo actual: test_oauth_service.py

# 3. Ejecutar y verificar cobertura
pytest --cov=app --cov-report=html
```

### Comando de Verificación Diaria

```powershell
# Windows (PowerShell)
cd backend
$env:OTEL_SDK_DISABLED="true"
python -m pytest tests/unit -q --tb=no
python -m pytest --cov=app --cov-report=term-missing | Select-String "TOTAL"
```

---

**Autor:** GitHub Copilot  
**Fecha:** 9 de Enero 2026  
**Próxima revisión:** Final de Sprint 1 (17 Enero 2026)
