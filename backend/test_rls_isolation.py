#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba automatizada para verificar el aislamiento RLS multi-tenant.
Versión mejorada con SQLAlchemy Events + RLS.
"""

import asyncio
import sys
from uuid import UUID
import asyncpg
from app.config import settings
from app.middleware.tenant import set_current_tenant_id


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_success(msg: str) -> None:
    print(f"{Colors.GREEN}[OK] {msg}{Colors.RESET}")


def print_error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR] {msg}{Colors.RESET}")


def print_info(msg: str) -> None:
    print(f"{Colors.BLUE}[INFO] {msg}{Colors.RESET}")


def print_header(msg: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


class RLSIsolationTester:
    def __init__(self):
        self.tenant_a_id: UUID | None = None
        self.tenant_b_id: UUID | None = None
        self.user_a_id: UUID | None = None
        self.user_b_id: UUID | None = None
        self.passed_tests = 0
        self.failed_tests = 0
    
    async def setup_test_data(self, conn: asyncpg.Connection) -> bool:
        print_header("PASO 1: Crear Datos de Prueba")
        try:
            await conn.execute("SET app.current_tenant_id = '';")
            
            self.tenant_a_id = await conn.fetchval("""
                INSERT INTO tenants (id, name, slug, domain, is_active, is_deleted)
                VALUES (gen_random_uuid(), 'Test Empresa A RLS', 'test-empresa-a-rls', 'test-a-rls.com', true, false)
                ON CONFLICT (slug) DO UPDATE SET is_active = true, is_deleted = false
                RETURNING id
            """)
            print_info(f"Tenant A: {self.tenant_a_id}")
            
            self.tenant_b_id = await conn.fetchval("""
                INSERT INTO tenants (id, name, slug, domain, is_active, is_deleted)
                VALUES (gen_random_uuid(), 'Test Empresa B RLS', 'test-empresa-b-rls', 'test-b-rls.com', true, false)
                ON CONFLICT (slug) DO UPDATE SET is_active = true, is_deleted = false
                RETURNING id
            """)
            print_info(f"Tenant B: {self.tenant_b_id}")
            
            password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aW.u6CnP6W0K"
            
            self.user_a_id = await conn.fetchval("""
                INSERT INTO users (id, tenant_id, email, password_hash, first_name, last_name, is_active, is_superuser, is_deleted)
                VALUES (gen_random_uuid(), $1, 'rls-user-a@empresa-a.com', $2, 'RLS User', 'A', true, false, false)
                ON CONFLICT (tenant_id, email) DO UPDATE SET is_deleted = false
                RETURNING id
            """, self.tenant_a_id, password_hash)
            print_info(f"Usuario A: {self.user_a_id}")
            
            self.user_b_id = await conn.fetchval("""
                INSERT INTO users (id, tenant_id, email, password_hash, first_name, last_name, is_active, is_superuser, is_deleted)
                VALUES (gen_random_uuid(), $1, 'rls-user-b@empresa-b.com', $2, 'RLS User', 'B', true, false, false)
                ON CONFLICT (tenant_id, email) DO UPDATE SET is_deleted = false
                RETURNING id
            """, self.tenant_b_id, password_hash)
            print_info(f"Usuario B: {self.user_b_id}")
            
            print_success("Datos de prueba creados")
            return True
        except Exception as e:
            print_error(f"Error setup: {e}")
            return False
    
    async def test_sqlalchemy_rls(self) -> None:
        print_header("PASO 2: Verificar RLS con SQLAlchemy + Events")
        
        from app.infrastructure.database.connection import get_db_context
        
        try:
            # Test Tenant A
            set_current_tenant_id(self.tenant_a_id)
            async with get_db_context() as session:
                from app.infrastructure.database.models.user import UserModel
                from sqlalchemy import select
                
                result = await session.execute(select(UserModel))
                users_a = result.scalars().all()
                tenant_ids = {str(u.tenant_id) for u in users_a}
                
                if len(tenant_ids) == 1 and str(self.tenant_a_id) in tenant_ids:
                    print_success(f"SQLAlchemy: Tenant A solo ve sus usuarios ({len(users_a)} usuarios)")
                    self.passed_tests += 1
                else:
                    print_error(f"SQLAlchemy: Tenant A ve múltiples tenants: {tenant_ids}")
                    self.failed_tests += 1
            
            # Test Tenant B
            set_current_tenant_id(self.tenant_b_id)
            async with get_db_context() as session:
                result = await session.execute(select(UserModel))
                users_b = result.scalars().all()
                tenant_ids = {str(u.tenant_id) for u in users_b}
                
                if len(tenant_ids) == 1 and str(self.tenant_b_id) in tenant_ids:
                    print_success(f"SQLAlchemy: Tenant B solo ve sus usuarios ({len(users_b)} usuarios)")
                    self.passed_tests += 1
                else:
                    print_error(f"SQLAlchemy: Tenant B ve múltiples tenants: {tenant_ids}")
                    self.failed_tests += 1
            
            # Test isolation: Tenant A intenta ver usuario de Tenant B
            set_current_tenant_id(self.tenant_a_id)
            async with get_db_context() as session:
                result = await session.execute(
                    select(UserModel).where(UserModel.id == self.user_b_id)
                )
                user = result.scalar_one_or_none()
                
                if user is None:
                    print_success("SQLAlchemy: Tenant A NO puede ver Usuario B")
                    self.passed_tests += 1
                else:
                    print_error("SQLAlchemy: Tenant A PUEDE ver Usuario B")
                    self.failed_tests += 1
            
            # Reset context
            set_current_tenant_id(None)
            
        except Exception as e:
            print_error(f"Error SQLAlchemy RLS: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 3
    
    async def test_database_rls_direct(self, conn: asyncpg.Connection) -> None:
        print_header("PASO 3: Verificar RLS Directo en BD")
        try:
            # Test Tenant A - Usar transacción EXPLÍCITA con BEGIN/COMMIT
            await conn.execute("BEGIN;")
            await conn.execute(f"SET LOCAL app.current_tenant_id = '{self.tenant_a_id}';")
            users_a = await conn.fetch("SELECT id, email, tenant_id FROM users WHERE email LIKE 'rls-%';")
            await conn.execute("COMMIT;")
            
            tenant_ids = {str(u['tenant_id']) for u in users_a}
            
            if len(tenant_ids) == 1 and str(self.tenant_a_id) in tenant_ids:
                print_success(f"BD Direct: Tenant A solo ve sus usuarios ({len(users_a)} usuarios)")
                self.passed_tests += 1
            else:
                print_error(f"BD Direct: Tenant A ve múltiples tenants: {tenant_ids}")
                self.failed_tests += 1
            
            # Test Tenant B
            await conn.execute("BEGIN;")
            await conn.execute(f"SET LOCAL app.current_tenant_id = '{self.tenant_b_id}';")
            users_b = await conn.fetch("SELECT id, email, tenant_id FROM users WHERE email LIKE 'rls-%';")
            await conn.execute("COMMIT;")
            
            tenant_ids = {str(u['tenant_id']) for u in users_b}
            
            if len(tenant_ids) == 1 and str(self.tenant_b_id) in tenant_ids:
                print_success(f"BD Direct: Tenant B solo ve sus usuarios ({len(users_b)} usuarios)")
                self.passed_tests += 1
            else:
                print_error(f"BD Direct: Tenant B ve múltiples tenants: {tenant_ids}")
                self.failed_tests += 1
        except Exception as e:
            print_error(f"Error RLS BD: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests += 2
    
    async def test_rls_policies(self, conn: asyncpg.Connection) -> None:
        print_header("PASO 4: Verificar Políticas RLS Activas")
        try:
            await conn.execute("SET app.current_tenant_id = '';")
            
            policies = await conn.fetch("""
                SELECT tablename, policyname FROM pg_policies 
                WHERE tablename IN ('users', 'roles', 'api_keys', 'conversations', 'chat_messages', 'notifications', 'audit_logs', 'oauth_connections', 'sso_configurations')
                ORDER BY tablename, policyname
            """)
            
            if len(policies) >= 9:
                print_info(f"Políticas RLS encontradas: {len(policies)}")
                for p in policies:
                    print_info(f"  - {p['tablename']}.{p['policyname']}")
                print_success(f"Políticas RLS activas: {len(policies)}")
                self.passed_tests += 1
            else:
                print_error(f"Solo {len(policies)} políticas encontradas, esperadas >= 9")
                self.failed_tests += 1
        except Exception as e:
            print_error(f"Error verificar políticas: {e}")
            self.failed_tests += 1
    
    def print_summary(self) -> None:
        print_header("RESUMEN")
        total = self.passed_tests + self.failed_tests
        print(f"Total: {total}")
        print_success(f"Exitosas: {self.passed_tests}")
        if self.failed_tests > 0:
            print_error(f"Fallidas: {self.failed_tests}")
        else:
            print(f"{Colors.GREEN}Fallidas: 0{Colors.RESET}")
        
        if self.failed_tests == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] TODAS LAS PRUEBAS PASARON{Colors.RESET}")
            print(f"{Colors.GREEN}Aislamiento multi-tenant RLS funcionando correctamente{Colors.RESET}")
            print(f"{Colors.GREEN}Defensa en profundidad: SQLAlchemy Events + PostgreSQL RLS{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}[FAIL] HAY PROBLEMAS DE AISLAMIENTO{Colors.RESET}")
    
    async def run(self) -> bool:
        try:
            print_header("PRUEBA DE AISLAMIENTO MULTI-TENANT RLS")
            print_info("Modo: SQLAlchemy Events + PostgreSQL RLS (Defensa en Profundidad)")
            
            # Conexión como boilerplate (owner) para setup de datos
            setup_url = 'postgresql://boilerplate:boilerplate@localhost:5432/boilerplate'
            print_info(f"Setup con: boilerplate (owner - bypass RLS)")
            conn_setup = await asyncpg.connect(setup_url)
            
            if not await self.setup_test_data(conn_setup):
                await conn_setup.close()
                return False
            
            await conn_setup.close()
            
            # Conexión como app_user (NO owner) para pruebas de RLS
            test_url = 'postgresql://app_user:app_password@localhost:5432/boilerplate'
            print_info(f"Tests con: app_user (NO owner - RLS activo)")
            conn_test = await asyncpg.connect(test_url)
            
            await self.test_sqlalchemy_rls()
            await self.test_database_rls_direct(conn_test)
            await self.test_rls_policies(conn_test)
            
            await conn_test.close()
            
            self.print_summary()
            return self.failed_tests == 0
        except Exception as e:
            print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    tester = RLSIsolationTester()
    success = await tester.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
