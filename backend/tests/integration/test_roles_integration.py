# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Integration tests for roles endpoints with PostgreSQL.

These tests use real PostgreSQL database to test:
- RLS (Row-Level Security)
- JSONB permissions
- ARRAY types
- Foreign key constraints
- Transaction rollback
"""

import pytest
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.roles import (
    create_role,
    update_role,
    delete_role,
    get_user_permissions,
)
from app.api.v1.schemas.roles import RoleCreate, RoleUpdate
from app.domain.entities.role import Role, Permission
from app.domain.entities.user import User
from app.domain.entities.tenant import Tenant
from app.infrastructure.database.repositories.role_repository import SQLAlchemyRoleRepository
from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
from app.infrastructure.auth.jwt_handler import hash_password


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create test tenant in real DB."""
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    
    tenant = Tenant(
        id=uuid4(),
        name="Test Company",
        domain="test-company",
        plan="professional",
        is_active=True,
    )
    
    await tenant_repo.create(tenant)
    await db_session.flush()
    
    return tenant


@pytest.fixture
async def test_superuser(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create superuser in real DB."""
    user_repo = SQLAlchemyUserRepository(db_session)
    
    user = User(
        id=uuid4(),
        email="superuser@test.com",
        password_hash=hash_password("Test123!"),
        first_name="Super",
        last_name="User",
        tenant_id=test_tenant.id,
        is_active=True,
        is_superuser=True,
        email_verified=True,
    )
    
    await user_repo.create(user)
    await db_session.flush()
    
    return user


@pytest.fixture
async def test_role(db_session: AsyncSession, test_tenant: Tenant) -> Role:
    """Create test role in real DB."""
    role_repo = SQLAlchemyRoleRepository(db_session)
    
    role = Role(
        id=uuid4(),
        name="Admin",
        description="Administrator role",
        tenant_id=test_tenant.id,
        permissions=[
            Permission.from_string("users:read"),
            Permission.from_string("users:write"),
        ],
        is_system=False,
    )
    
    await role_repo.create(role)
    await db_session.flush()
    
    return role


# ===========================================
# CREATE ROLE - Integration Tests
# ===========================================

class TestCreateRoleIntegration:
    """Integration tests for create_role endpoint with real DB."""
    
    async def test_create_role_duplicate_name_causes_conflict(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_superuser: User,
        test_role: Role,
    ):
        """
        Test: Creating role with duplicate name raises HTTP 409.
        
        Covers:
        - Line 168: ConflictError handling
        - Real database constraint validation
        - JSONB permissions storage
        """
        request = RoleCreate(
            name="Admin",  # Duplicate name
            description="Another admin",
            permissions=["users:read"],
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await create_role(
                request=request,
                current_user_id=test_superuser.id,
                tenant_id=test_tenant.id,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 409
        assert "ROLE_EXISTS" in exc_info.value.detail or "already exists" in str(exc_info.value.detail).lower()
    
    async def test_create_role_success_stores_permissions(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_superuser: User,
    ):
        """
        Test: Creating role successfully stores JSONB permissions.
        
        Covers:
        - JSONB array storage
        - Permission parsing
        - Role creation flow
        """
        request = RoleCreate(
            name="Editor",
            description="Content editor",
            permissions=["posts:read", "posts:write", "comments:moderate"],
        )
        
        result = await create_role(
            request=request,
            current_user_id=test_superuser.id,
            tenant_id=test_tenant.id,
            session=db_session,
        )
        
        assert result.name == "Editor"
        assert result.description == "Content editor"
        assert len(result.permissions) == 3
        assert "posts:read" in result.permissions
        assert "posts:write" in result.permissions
        assert "comments:moderate" in result.permissions


# ===========================================
# UPDATE ROLE - Integration Tests
# ===========================================

class TestUpdateRoleIntegration:
    """Integration tests for update_role endpoint with real DB."""
    
    async def test_update_role_not_found_raises_404(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_superuser: User,
    ):
        """
        Test: Updating non-existent role raises HTTP 404.
        
        Covers:
        - Line 203: EntityNotFoundError handling
        - Database query with invalid ID
        """
        fake_role_id = uuid4()
        request = RoleUpdate(description="Updated description")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_role(
                role_id=fake_role_id,
                request=request,
                current_user_id=test_superuser.id,
                tenant_id=test_tenant.id,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 404
        assert "ROLE_NOT_FOUND" in exc_info.value.detail or "not found" in str(exc_info.value.detail).lower()
    
    async def test_update_role_invalid_permission_format_raises_400(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_superuser: User,
        test_role: Role,
    ):
        """
        Test: Updating role with invalid permission format raises HTTP 400.
        
        Covers:
        - Line 215: ValidationError for invalid permissions
        - Permission parsing logic
        """
        request = RoleUpdate(
            permissions=["invalid_permission", "another:invalid:format"]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await update_role(
                role_id=test_role.id,
                request=request,
                current_user_id=test_superuser.id,
                tenant_id=test_tenant.id,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 400
        assert "INVALID_PERMISSION" in exc_info.value.detail or "invalid" in str(exc_info.value.detail).lower()
    
    async def test_update_role_duplicate_name_raises_409(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_superuser: User,
        test_role: Role,
    ):
        """
        Test: Updating role to duplicate name raises HTTP 409.
        
        Covers:
        - Line 221: ConflictError for duplicate name
        - Unique constraint validation
        """
        # Create another role first
        role_repo = SQLAlchemyRoleRepository(db_session)
        another_role = Role(
            id=uuid4(),
            name="Editor",
            tenant_id=test_tenant.id,
            permissions=[],
            is_system=False,
        )
        await role_repo.create(another_role)
        await db_session.flush()
        
        # Try to rename test_role to "Editor"
        request = RoleUpdate(name="Editor")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_role(
                role_id=test_role.id,
                request=request,
                current_user_id=test_superuser.id,
                tenant_id=test_tenant.id,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 409


# ===========================================
# GET USER PERMISSIONS - Integration Tests
# ===========================================

class TestGetUserPermissionsIntegration:
    """Integration tests for get_user_permissions endpoint with real DB."""
    
    async def test_get_permissions_user_not_found_raises_404(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_superuser: User,
    ):
        """
        Test: Getting permissions for non-existent user raises HTTP 404.
        
        Covers:
        - Lines 288-297: User not found handling
        - Foreign key relationship validation
        """
        fake_user_id = uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_user_permissions(
                user_id=fake_user_id,
                current_user_id=test_superuser.id,
                tenant_id=test_tenant.id,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 404
        assert "USER_NOT_FOUND" in exc_info.value.detail or "not found" in str(exc_info.value.detail).lower()
    
    async def test_get_permissions_returns_role_permissions(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_superuser: User,
        test_role: Role,
    ):
        """
        Test: Get permissions returns aggregated role permissions.
        
        Covers:
        - User-role relationship
        - Permission aggregation
        - JSONB array querying
        """
        # Assign role to user
        user_repo = SQLAlchemyUserRepository(db_session)
        test_superuser.role_id = test_role.id
        await user_repo.update(test_superuser.id, test_superuser)
        await db_session.flush()
        
        result = await get_user_permissions(
            user_id=test_superuser.id,
            current_user_id=test_superuser.id,
            tenant_id=test_tenant.id,
            session=db_session,
        )
        
        assert len(result.permissions) >= 2
        assert "users:read" in result.permissions
        assert "users:write" in result.permissions


# ===========================================
# DELETE ROLE - Integration Tests
# ===========================================

class TestDeleteRoleIntegration:
    """Integration tests for delete_role endpoint with real DB."""
    
    async def test_delete_role_removes_from_database(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_superuser: User,
        test_role: Role,
    ):
        """
        Test: Deleting role removes it from PostgreSQL.
        
        Covers:
        - Soft delete or hard delete
        - Foreign key cascades
        - Transaction commit
        """
        role_id = test_role.id
        
        await delete_role(
            role_id=role_id,
            current_user_id=test_superuser.id,
            tenant_id=test_tenant.id,
            session=db_session,
        )
        
        # Verify deletion
        role_repo = SQLAlchemyRoleRepository(db_session)
        deleted_role = await role_repo.get_by_id(role_id)
        
        assert deleted_role is None or deleted_role.deleted_at is not None
