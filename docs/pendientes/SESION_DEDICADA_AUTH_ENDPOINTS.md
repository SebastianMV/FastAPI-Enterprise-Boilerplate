# 🎯 SESIÓN DEDICADA: Auth Endpoints

> **Fecha:** Pendiente de agendar  
> **Duración estimada:** 3-4 horas  
> **Prioridad:** Alta  
> **Impacto:** +1.27% global coverage (106 statements)

---

## 📊 Estado Actual

| Métrica | Valor |
| --- | --- |
| **Coverage actual** | 58% (168 statements, 106 missed) |
| **Coverage objetivo** | 85%+ |
| **Archivo principal** | `app/api/v1/endpoints/auth.py` |
| **Tests existentes** | 24 tests (todos failing) |

---

## 🔍 Análisis de Problemas

### Tests Existentes con Errores

**Archivo:** `tests/unit/api/test_auth_endpoints_complete.py`

**Problemas identificados:**

1. **ImportError de variables inexistentes** (18 tests afectados)
   - Tests intentan acceder a `_active_sessions`, `_email_verification_tokens`
   - Estas variables NO existen en el módulo auth
   - Real implementación usa `SessionRepository` (database)

2. **ValidationError en schemas** (4 tests afectados)
   - `LoginRequest`, `RegisterRequest` con parámetros incorrectos
   - Tests usan `mfa_code` pero schema espera estructura diferente

3. **TypeError en refresh token** (1 test)
   - `'NoneType' object is not subscriptable`
   - Mock de JWT decode retorna None

4. **AssertionError en mensajes** (2 tests)
   - Mensajes de error cambiaron en implementación
   - Tests esperan códigos antiguos: `INVALID_RESET_TOKEN`, `RESET_TOKEN_EXPIRED`

---

## 🏗️ Estrategia de Refactoring

### Fase 1: Análisis (30 mins)

- [ ] Revisar implementación real de todos los endpoints
- [ ] Documentar flujos de autenticación actuales
- [ ] Identificar dependencias (SessionRepository, UserRepository, EmailService)
- [ ] Mapear schemas de request/response

### Fase 2: Integration Tests (2 horas)

**Cambio de enfoque:** Unit tests → Integration tests

**Razón:** Auth endpoints dependen fuertemente de:

- Base de datos (SessionRepository)
- Email service (verificación, password reset)
- Redis cache (rate limiting, tokens)

**Archivos a crear/modificar:**

```text
tests/integration/test_auth_endpoints_integration.py  # Nuevo
tests/unit/api/test_auth_endpoints_complete.py        # Eliminar/refactorizar
```

**Tests necesarios:**

1. **Login Endpoint** (12 tests)
   - Login exitoso con credenciales válidas
   - Login con password incorrecto
   - Login con usuario inexistente
   - Login con cuenta bloqueada (account_lockout)
   - Login con MFA habilitado (sin código)
   - Login con MFA (código válido)
   - Login con MFA (código inválido)
   - Login con MFA (backup code)
   - Login con email no verificado (si aplica)
   - Login genera session en DB
   - Login retorna access + refresh tokens
   - Login actualiza last_login timestamp

2. **Register Endpoint** (8 tests)
   - Registro exitoso crea user + tenant
   - Registro con email duplicado
   - Registro con password débil
   - Registro con passwords no coincidentes
   - Registro envía email de verificación
   - Registro crea tenant default
   - Registro asigna rol default
   - Registro valida formato de email

3. **Refresh Token** (5 tests)
   - Refresh exitoso retorna nuevos tokens
   - Refresh con token inválido
   - Refresh con token expirado
   - Refresh con session eliminada
   - Refresh revoca token anterior

4. **Logout** (3 tests)
   - Logout revoca session en DB
   - Logout con token inválido
   - Logout múltiple (todas las sessions)

5. **Change Password** (4 tests)
   - Change password exitoso
   - Change password con password actual incorrecto
   - Change password con passwords no coincidentes
   - Change password invalida sessions activas

6. **Forgot Password** (4 tests)
   - Forgot password envía email
   - Forgot password con email no registrado (mensaje genérico)
   - Forgot password genera token único
   - Forgot password token expira

7. **Reset Password** (5 tests)
   - Reset exitoso con token válido
   - Reset con token inválido
   - Reset con token expirado
   - Reset con token ya usado
   - Reset invalida sessions activas

8. **Verify Email** (3 tests)
   - Verificación exitosa
   - Verificación con token inválido
   - Verificación con token expirado

### Fase 3: Fixtures y Mocks (1 hora)

**Fixtures necesarios:**

```python
@pytest.fixture
async def db_session():
    """Session de DB real para integration tests."""
    
@pytest.fixture
async def test_user():
    """Usuario de prueba en DB."""
    
@pytest.fixture
async def test_tenant():
    """Tenant de prueba."""
    
@pytest.fixture
def mock_email_service():
    """Mock del EmailService para no enviar emails reales."""
```

**Mocks críticos:**

- `EmailService.send_email` → AsyncMock (no enviar emails reales)
- `settings.EMAIL_ENABLED` → True
- `settings.EMAIL_VERIFICATION_REQUIRED` → False (tests rápidos)

### Fase 4: Cleanup (30 mins)

- [ ] Eliminar `test_auth_endpoints_complete.py`
- [ ] Actualizar documentación de tests
- [ ] Verificar coverage final ≥85%
- [ ] Commit con mensaje descriptivo

---

## 📝 Notas Técnicas

### Arquitectura Real vs Tests Antiguos

**Tests antiguos asumían:**

```python
# ❌ NO EXISTE
from app.api.v1.endpoints.auth import _active_sessions
from app.api.v1.endpoints.auth import _email_verification_tokens
```

**Arquitectura real usa:**

```python
# ✅ CORRECTO
from app.infrastructure.database.repositories.session_repository import SessionRepository
from app.domain.entities.user import User
from app.infrastructure.email.service import EmailService
```

### Endpoints con Mayor Cobertura Faltante

| Endpoint | Líneas Faltantes | Motivo |
| --- | --- | --- |
| `login()` | 15-30 | Flujo MFA completo |
| `refresh_token()` | 10-15 | Validación de session |
| `register()` | 20-25 | Creación user + tenant |
| `reset_password()` | 15-20 | Validación de token |
| `verify_email()` | 10-12 | Token verification |

---

## 🎯 Métricas de Éxito

- [ ] Coverage ≥85% en `auth.py` (+27%)
- [ ] 0 tests failing
- [ ] +44 tests integration (mínimo)
- [ ] Tiempo de ejecución <30s
- [ ] Documentación actualizada

---

## 🔗 Referencias

- **Archivo fuente:** [app/api/v1/endpoints/auth.py](../backend/app/api/v1/endpoints/auth.py)
- **Tests actuales:** [tests/unit/api/test_auth_endpoints_complete.py](../backend/tests/unit/api/test_auth_endpoints_complete.py)
- **SessionRepository:** [app/infrastructure/database/repositories/session_repository.py](../backend/app/infrastructure/database/repositories/session_repository.py)
- **Schemas:** [app/api/v1/schemas/auth.py](../backend/app/api/v1/schemas/auth.py)

---

**Última actualización:** 16 de Enero 2026  
**Estado:** 📋 Planificado - Pendiente de ejecución
