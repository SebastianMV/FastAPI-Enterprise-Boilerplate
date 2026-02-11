import asyncio

import asyncpg


async def main():
    # Prueba 1: Conectar con boilerplate (owner)
    print("=" * 60)
    print("PRUEBA 1: Usuario boilerplate (OWNER)")
    print("=" * 60)
    conn_owner = await asyncpg.connect(
        "postgresql://boilerplate:boilerplate@localhost:5432/boilerplate"
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
        "postgresql://app_user:app_password@localhost:5432/boilerplate"
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
