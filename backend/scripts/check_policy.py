import asyncio
import os

import asyncpg


async def main():
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "boilerplate")
    owner_user = os.environ.get("DB_OWNER_USER", "boilerplate")
    owner_pass = os.environ.get("DB_OWNER_PASSWORD", "boilerplate")
    app_user = os.environ.get("DB_APP_USER", "app_user")
    app_pass = os.environ.get("DB_APP_PASSWORD", "app_password")

    # Prueba 1: Conectar con boilerplate (owner)
    print("=" * 60)
    print("PRUEBA 1: Usuario boilerplate (OWNER)")
    print("=" * 60)
    conn_owner = await asyncpg.connect(
        f"postgresql://{owner_user}:{owner_pass}@{db_host}:{db_port}/{db_name}"
    )

    # Verificar owner
    result = await conn_owner.fetchrow("""
        SELECT relname, pg_get_userbyid(relowner) as owner
        FROM pg_class 
        WHERE relname = 'users';
    """)
    print(f"Owner de tabla users: {result['owner']}")

    # Test RLS
    await conn_owner.execute("BEGIN;")
    await conn_owner.execute(
        "SET LOCAL app.current_tenant_id = '00000000-0000-0000-0000-000000000001';"
    )
    users = await conn_owner.fetch("SELECT COUNT(*) as count FROM users;")
    await conn_owner.execute("COMMIT;")
    print(f"Total usuarios visibles: {users[0]['count']}")

    await conn_owner.close()

    # Prueba 2: Conectar con app_user (NO owner)
    print("\n" + "=" * 60)
    print("PRUEBA 2: Usuario app_user (NO OWNER)")
    print("=" * 60)
    conn_app = await asyncpg.connect(
        f"postgresql://{app_user}:{app_pass}@{db_host}:{db_port}/{db_name}"
    )

    current_user = await conn_app.fetchval("SELECT current_user;")
    print(f"Usuario conectado: {current_user}")

    # Test RLS
    await conn_app.execute("BEGIN;")
    await conn_app.execute(
        "SET LOCAL app.current_tenant_id = '00000000-0000-0000-0000-000000000001';"
    )
    users = await conn_app.fetch(
        "SELECT COUNT(*) as count FROM users WHERE tenant_id::text = '00000000-0000-0000-0000-000000000001';"
    )
    await conn_app.execute("COMMIT;")
    print(f"Total usuarios de tenant específico (sin RLS): {users[0]['count']}")

    # Test RLS (sin WHERE - debería filtrar automáticamente)
    await conn_app.execute("BEGIN;")
    await conn_app.execute(
        "SET LOCAL app.current_tenant_id = '00000000-0000-0000-0000-000000000001';"
    )
    users_rls = await conn_app.fetch("SELECT COUNT(*) as count FROM users;")
    await conn_app.execute("COMMIT;")
    print(f"Total usuarios visibles CON RLS: {users_rls[0]['count']}")

    if users[0]["count"] == users_rls[0]["count"]:
        print("\n✅ RLS FUNCIONA! app_user solo ve su tenant")
    else:
        print("\n❌ RLS NO funciona correctamente")

    await conn_app.close()


asyncio.run(main())
