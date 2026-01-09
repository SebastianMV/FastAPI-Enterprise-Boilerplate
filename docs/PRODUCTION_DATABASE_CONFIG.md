# Configuración de Producción - DATABASE_URL

> 📖 **Note:** This document is now consolidated into [DEPLOYMENT.md](./DEPLOYMENT.md#database-setup). It's kept for reference but may be removed in future versions.

## ⚠️ IMPORTANTE: Seguridad Multi-Tenant

Para **producción**, debes usar el usuario `app_user` en vez de `boilerplate` para que Row-Level Security (RLS) funcione correctamente.

## 🔐 ¿Por qué app_user?

- **`boilerplate`**: Usuario OWNER de las tablas → RLS bypassed (solo desarrollo)
- **`app_user`**: Usuario NO-owner → RLS enforced (producción segura)

## 📝 Pasos de Configuración

### 1. El usuario `app_user` ya está creado

Si ejecutaste las migraciones, el usuario ya existe (migración 007). Si no:

```sql
-- Conectar como boilerplate (superuser)
psql -U boilerplate -d boilerplate

-- Verificar que app_user existe
\du app_user

-- Si no existe, créalo:
CREATE ROLE app_user WITH LOGIN PASSWORD 'your-secure-password-here';
GRANT CONNECT ON DATABASE boilerplate TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
```

### 2. Actualizar variables de entorno

**Archivo `.env` (producción):**

```env
# PRODUCTION: Use app_user for RLS enforcement
DATABASE_URL=postgresql+asyncpg://app_user:your-secure-password@db:5432/boilerplate
```

**Docker Compose (ya configurado en docker-compose.prod.yml):**

```yaml
environment:
  - DATABASE_URL=postgresql+asyncpg://app_user:app_password@db:5432/boilerplate
```

### 3. Cambiar contraseña de app_user

**IMPORTANTE**: Cambia la contraseña por defecto antes de desplegar:

```sql
ALTER USER app_user WITH PASSWORD 'your-very-secure-password-123!';
```

Luego actualiza `DATABASE_URL` con la nueva contraseña.

### 4. Verificar RLS funciona

```bash
# Ejecutar test de aislamiento
cd backend
python test_rls_isolation.py
```

**Output esperado:**

```text
✅ BD Direct: Tenant A solo ve sus usuarios (N usuarios)
✅ BD Direct: Tenant B solo ve sus usuarios (M usuarios)
✅ Políticas RLS activas: 9
```

## 🏗️ Desarrollo vs Producción

| Entorno | Usuario | RLS | Uso |
| -------------- | ------------- | ------------ | ----------------------------- |
| **Desarrollo** | `boilerplate` | ❌ Bypassed | Admin, migraciones, debugging |
| **Producción** | `app_user` | ✅ Enforced | Aplicación en runtime |

## ✅ Checklist Pre-Deploy

- [ ] Migraciones ejecutadas (`alembic upgrade head`)
- [ ] Usuario `app_user` existe en base de datos
- [ ] Contraseña de `app_user` cambiada (NO usar `app_password`)
- [ ] Variable `DATABASE_URL` usa `app_user`
- [ ] Test RLS ejecutado exitosamente
- [ ] Healthcheck pasa: `curl http://localhost:8000/api/v1/health`

## 🆘 Troubleshooting

### "password authentication failed for user app_user"

- Verifica que la contraseña en `DATABASE_URL` coincida con la de la base de datos
- Verifica que el usuario existe: `psql -U boilerplate -c "\du app_user"`

### "permission denied for table users"

- Ejecuta migración 007: `alembic upgrade 007_change_owners`
- Verifica permisos: `GRANT SELECT, INSERT, UPDATE, DELETE ON users TO app_user;`

### RLS no filtra datos

- Verifica que estás usando `app_user`, no `boilerplate`
- Ejecuta `python test_rls_isolation.py` para diagnosticar

## 📚 Más Información

- [docs/RLS_SETUP.md](RLS_SETUP.md) - Documentación completa de RLS
- [docker-compose.prod.yml](../docker-compose.prod.yml) - Configuración de producción
- [.env.example](../.env.example) - Ejemplo de variables de entorno
