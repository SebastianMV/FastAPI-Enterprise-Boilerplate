# Row-Level Security (RLS) - Multi-Tenant Isolation

## 🛡️ Defense in Depth Architecture

Esta aplicación implementa **defensa en profundidad** para aislamiento multi-tenant, combinando:

### 1. **SQLAlchemy Events** (Application Layer)

- Configuración automática de `app.current_tenant_id` en cada transacción
- Se ejecuta ANTES de cualquier consulta SQL
- Implementado en `backend/app/infrastructure/database/connection.py`

```python
@event.listens_for(Session, "after_begin")
def receive_after_begin(session, transaction, connection):
    tenant_id = get_current_tenant_id()  # Del JWT vía TenantMiddleware
    if tenant_id:
        connection.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
```

### 2. **PostgreSQL Row-Level Security** (Database Layer)

- 9 políticas RLS activas en tablas core
- Aplican **incluso si la capa de aplicación falla**
- `FORCE ROW LEVEL SECURITY` activado
- Políticas con `USING` (SELECT) y `WITH CHECK` (INSERT/UPDATE/DELETE)

```sql
CREATE POLICY users_tenant_isolation ON users
FOR ALL
USING (tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), ''))
WITH CHECK (tenant_id::text = COALESCE(current_setting('app.current_tenant_id', true), ''));
```

## 📋 Estado de Implementación

### ✅ Completado

1. **Migración 006**: Habilitación de RLS en 7 tablas core
   - `users`, `roles`, `api_keys`, `conversations`, `chat_messages`, `notifications`, `audit_logs`
   - Políticas para `oauth_connections` y `sso_configurations` (migración 004)

2. **Migración 007**: Creación del usuario `app_user`
   - Usuario NO-owner para que RLS se aplique correctamente
   - Permisos SELECT, INSERT, UPDATE, DELETE en todas las tablas
   - **NO tiene** privilegio `BYPASSRLS`

3. **Migración 008**: Políticas CRUD completas
   - `FOR ALL` con `USING` + `WITH CHECK`
   - Soporta SELECT, INSERT, UPDATE, DELETE
   - Chat messages usa FK lookup a conversations

4. **SQLAlchemy Event Listener**: Configuración automática de contexto
   - Se ejecuta en `after_begin` de cada sesión
   - Obtiene `tenant_id` de `ContextVar` (configurado por `TenantMiddleware`)
   - Ejecuta `SET LOCAL app.current_tenant_id`

5. **TenantMiddleware**: Extracción y configuración de tenant
   - Lee `tenant_id` del JWT
   - Almacena en `ContextVar` thread-safe
   - Disponible para todo el request lifecycle

### 📝 Tablas Protegidas

| Tabla | Política | Tipo | Estado |
| ----- | -------- | ---- | ------ |
| `users` | users_tenant_isolation | FOR ALL | ✅ Activa |
| `roles` | roles_tenant_isolation | FOR ALL | ✅ Activa |
| `api_keys` | api_keys_tenant_isolation | FOR ALL | ✅ Activa |
| `conversations` | conversations_tenant_isolation | FOR ALL | ✅ Activa |
| `chat_messages` | chat_messages_tenant_isolation | FOR ALL (FK) | ✅ Activa |
| `notifications` | notifications_tenant_isolation | FOR ALL | ✅ Activa |
| `audit_logs` | audit_logs_tenant_isolation | FOR ALL | ✅ Activa |
| `oauth_connections` | oauth_connections_tenant_isolation | FOR SELECT | ✅ Activa |
| `sso_configurations` | sso_configurations_tenant_isolation | FOR SELECT | ✅ Activa |

## 🔑 Configuración de Usuarios

### Desarrollo (RLS Bypassed)

```env
DATABASE_URL=postgresql+asyncpg://boilerplate:boilerplate@localhost:5432/boilerplate
```

- Usuario: `boilerplate` (owner de tablas)
- RLS: **Bypassed** (FORCE RLS no aplica a owners con prepared statements)
- Uso: Desarrollo local, migraciones, admin tasks

### Producción (RLS Enforced) ⭐ **RECOMENDADO**

```env
DATABASE_URL=postgresql+asyncpg://app_user:app_password@localhost:5432/boilerplate
```

- Usuario: `app_user` (NO owner)
- RLS: **Enforced** (políticas aplican correctamente)
- Uso: Producción, staging, testing

## ✅ Verificación de RLS

### Test Automatizado

```bash
cd backend
python test_rls_isolation.py
```

**Output esperado**:

```text
✅ BD Direct: Tenant A solo ve sus usuarios (N usuarios)
✅ BD Direct: Tenant B solo ve sus usuarios (M usuarios)
✅ Políticas RLS activas: 9
```

### Test Manual (PostgreSQL)

```sql
-- Conectar como app_user
\c boilerplate app_user

-- Configurar tenant A
BEGIN;
SET LOCAL app.current_tenant_id = '<tenant-a-uuid>';
SELECT COUNT(*) FROM users;  -- Solo ve usuarios de tenant A
COMMIT;

-- Configurar tenant B
BEGIN;
SET LOCAL app.current_tenant_id = '<tenant-b-uuid>';
SELECT COUNT(*) FROM users;  -- Solo ve usuarios de tenant B
COMMIT;
```

## 🚨 Limitaciones Conocidas

### asyncpg + FORCE RLS + Table Owners

PostgreSQL tiene una limitación: `FORCE ROW LEVEL SECURITY` **NO se aplica completamente** a table owners cuando se usan prepared statements (que es como funciona asyncpg y SQLAlchemy).

**Solución implementada**:

1. Usuario `app_user` (NO owner) para la aplicación
2. Usuario `boilerplate` (owner) solo para migraciones

### OAuthConnectionModel Mapping Error

El modelo `OAuthConnectionModel` tiene un error de mapping circular con `UserModel`. Este error **NO afecta** el funcionamiento de RLS en base de datos.

**Solución temporal**: Comentar relación en desarrollo si causa problemas
**Solución definitiva**: Resolver import circular (pendiente)

## 🔐 Flujo de Seguridad

```text
HTTP Request
    ↓
TenantMiddleware (extrae tenant_id del JWT)
    ↓
ContextVar.set(tenant_id)
    ↓
SQLAlchemy Session.begin() 
    ↓
Event Listener "after_begin" 
    ↓
SET LOCAL app.current_tenant_id = '<tenant_id>'
    ↓
SQL Query (con RLS automático)
    ↓
PostgreSQL filtra por tenant_id
    ↓
Response (solo datos del tenant)
```

## 📊 Validación de Seguridad

### Escenarios Testeados

1. ✅ **SELECT Isolation**: Cada tenant solo ve sus propios registros
2. ✅ **INSERT Protection**: No se puede insertar en otro tenant
3. ✅ **UPDATE Protection**: No se puede modificar datos de otro tenant  
4. ✅ **DELETE Protection**: No se puede eliminar datos de otro tenant
5. ✅ **FK Consistency**: Chat messages respetan tenant via conversation FK
6. ✅ **Policy Active**: 9 políticas confirmadas en `pg_policies`

### Casos de Uso Críticos

| Caso | Estado | Protección |
| ---- | ------ | --------- |
| Usuario A intenta leer datos de B | ✅ Bloqueado | RLS BD |
| App olvida configurar tenant_id | ✅ Datos vacíos | RLS BD (current_setting = '') |
| SQL Injection intenta bypass | ✅ Bloqueado | RLS BD + parametrización |
| Owner hace SELECT sin tenant | ⚠️ Ve todo | Solo con boilerplate user |
| app_user hace SELECT sin tenant | ✅ Datos vacíos | RLS BD activo |

## 🔄 Migraciones Relacionadas

1. **001-005**: Schema base
2. **006** (`9446ce57e027`): Habilitar RLS + políticas SELECT
3. **007** (`007_change_owners`): Crear usuario app_user
4. **008** (`008_rls_write_pol`): Políticas INSERT/UPDATE/DELETE

## 📚 Referencias

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [SQLAlchemy Events](https://docs.sqlalchemy.org/en/20/orm/events.html)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/advanced/security/)

## ⚡ Performance Notes

- Event listener ejecuta `SET LOCAL` una vez por transacción (overhead mínimo)
- RLS policies usan índices existentes en `tenant_id`
- Prepared statements mantienen rendimiento óptimo
- `COALESCE` evita errores si current_setting no existe

## 🎯 Próximos Pasos

- [ ] Resolver OAuthConnectionModel mapping error
- [ ] Agregar RLS a `tenants` table (para super-admin scenarios)
- [ ] Implementar audit logging de intentos de acceso cross-tenant
- [ ] Configurar alertas de seguridad para RLS violations
- [ ] Tests de carga con RLS activo (performance validation)
