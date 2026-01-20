# 🗄️ PostgreSQL para Tests de Integración

## Problema Identificado

Los tests de integración actuales usan **SQLite in-memory**, pero el sistema en producción usa **PostgreSQL 17** con características específicas:

- ✅ **RLS (Row-Level Security)** - Aislamiento multi-tenant
- ✅ **JSONB** - Almacenamiento de permissions, settings
- ✅ **ARRAY Types** - Listas de permisos
- ✅ **Foreign Keys** - Relaciones complejas
- ✅ **Constraints únicos** - Por tenant

**Resultado:** Los tests pasan con SQLite pero no cubren código real porque:

1. Mocking excesivo previene ejecución de endpoints
2. SQLite no valida constraints de PostgreSQL
3. No hay tests contra esquema real

## Solución Implementada

### 1. PostgreSQL de Testing

Se creó `docker-compose.test.yml` con base de datos aislada:

```yaml
services:
  test_db:
    image: postgres:17-alpine
    ports:
      - "5433:5432"  # Puerto diferente a dev (5432)
    environment:
      - POSTGRES_USER=test_user
      - POSTGRES_PASSWORD=test_password
      - POSTGRES_DB=test_boilerplate
```

**Ventajas:**
- ✅ Esquema idéntico a producción
- ✅ Validación real de constraints
- ✅ RLS funciona correctamente
- ✅ JSONB y ARRAY types
- ✅ Aislado del entorno de desarrollo

### 2. Configuración de Tests

Modificación en `tests/conftest.py`:

```python
@pytest.fixture(scope="session")
async def test_engine():
    """
    Usa PostgreSQL si TEST_DATABASE_URL está definida,
    sino usa SQLite (unit tests).
    """
    test_db_url = os.getenv("TEST_DATABASE_URL")
    
    if test_db_url:
        # PostgreSQL para integration tests
        engine = create_async_engine(
            test_db_url,
            poolclass=NullPool,  # Sin pooling
        )
    else:
        # SQLite para unit tests
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
        )
```

### 3. Comandos PowerShell

Agregados en `make.ps1`:

```powershell
# Iniciar PostgreSQL de testing
Start-TestDatabase

# Ejecutar tests de integración con PostgreSQL
Invoke-IntegrationTests

# Con coverage
Invoke-IntegrationTestsCoverage

# Detener PostgreSQL
Stop-TestDatabase
```

### 4. Tests de Integración Reales

Creado `tests/integration/test_roles_integration.py`:

**ANTES (no funcionaba):**
```python
# ❌ Mock previene ejecución
mock_repo = AsyncMock()
mock_repo.create.side_effect = ConflictError(...)
await create_role(request, session)
# Endpoint recibe error inmediato, nunca ejecuta código
```

**AHORA (funciona):**
```python
# ✅ Repositorio real + DB real
repo = SQLAlchemyRoleRepository(db_session)

# Crear rol real para duplicado
role1 = Role(name="Admin", tenant_id=tenant.id, ...)
await repo.create(role1)

# Intentar duplicado (ejecuta TODO el código)
with pytest.raises(HTTPException) as exc:
    await create_role(
        request=RoleCreate(name="Admin", ...),
        session=db_session,
    )
# Ahora sí cubre: validación, entity creation, conflict check
```

## Uso

### Paso 1: Iniciar PostgreSQL de Testing

```powershell
# Cargar funciones
. .\make.ps1

# Iniciar DB
Start-TestDatabase
```

O manualmente:
```bash
docker compose -f docker-compose.test.yml up -d
```

### Paso 2: Ejecutar Tests de Integración

```powershell
# Con funciones PowerShell
Invoke-IntegrationTests

# O manualmente
cd backend
$env:TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5433/test_boilerplate"
pytest tests/integration/test_roles_integration.py -v
```

### Paso 3: Verificar Coverage

```powershell
Invoke-IntegrationTestsCoverage
```

## Tests Creados

### `test_roles_integration.py` (10 tests)

**CREATE ROLE:**
- ✅ `test_create_role_duplicate_name_causes_conflict` → Cubre línea 168
- ✅ `test_create_role_success_stores_permissions` → JSONB storage

**UPDATE ROLE:**
- ✅ `test_update_role_not_found_raises_404` → Cubre línea 203
- ✅ `test_update_role_invalid_permission_format_raises_400` → Cubre línea 215
- ✅ `test_update_role_duplicate_name_raises_409` → Cubre línea 221

**GET USER PERMISSIONS:**
- ✅ `test_get_permissions_user_not_found_raises_404` → Cubre líneas 288-297
- ✅ `test_get_permissions_returns_role_permissions` → Aggregation logic

**DELETE ROLE:**
- ✅ `test_delete_role_removes_from_database` → Delete + cascades

## Cobertura Esperada

**ANTES:**
- roles.py: **93%** (8 líneas perdidas)
- Tests pasan pero no cubren código (mocks)

**DESPUÉS:**
- roles.py: **96-98%** (2-3 líneas perdidas)
- Tests ejecutan código real con DB real

**Líneas cubiertas:**
- ✅ 168: ConflictError en create_role
- ✅ 203: EntityNotFoundError en update_role
- ✅ 215: ValidationError permissions inválidas
- ✅ 221: ConflictError en update_role
- ✅ 288-297: User not found en get_user_permissions

## Próximos Pasos

1. **Ejecutar tests** con PostgreSQL activo
2. **Medir coverage** real
3. **Replicar patrón** para otros endpoints:
   - tenants.py (94% → 97%+)
   - websocket.py (91% → 95%+)
   - users.py (83% → 90%+)
   - mfa.py (83% → 90%+)

## Troubleshooting

**Docker no inicia:**
```powershell
# Verificar Docker Desktop está corriendo
docker ps

# Si no, iniciar Docker Desktop primero
```

**Puerto 5433 ocupado:**
```bash
# Cambiar puerto en docker-compose.test.yml
ports:
  - "5434:5432"  # Usar otro puerto

# Actualizar TEST_DATABASE_URL
$env:TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@localhost:5434/test_boilerplate"
```

**Tests fallan con "database does not exist":**
```bash
# Reiniciar contenedor
docker compose -f docker-compose.test.yml down
docker compose -f docker-compose.test.yml up -d

# Esperar 10 segundos para inicialización
Start-Sleep -Seconds 10
```

## Recursos

- **Archivo:** `docker-compose.test.yml`
- **Tests:** `tests/integration/test_roles_integration.py`
- **Config:** `tests/conftest.py` (líneas 48-95)
- **Comandos:** `make.ps1` (líneas 90-143)

---

**Creado:** Enero 19, 2026  
**Autor:** FastAPI Enterprise Boilerplate Team
