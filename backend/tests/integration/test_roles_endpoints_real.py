# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Integration tests for roles endpoints - REAL database, NO mocks.

These tests execute actual code paths to improve coverage.
"""

import pytest
from uuid import uuid4
from fastapi import HTTPException

from app.api.v1.endpoints.roles import create_role, update_role, get_user_permissions
from app.api.v1.schemas.roles import RoleCreate, RoleUpdate
from app.domain.entities.role import Role
from app.domain.entities.user import User
from app.domain.entities.tenant import Tenant
from app.domain.value_objects.email import Email
from app.infrastructure.auth.jwt_handler import hash_password


@pytest.mark.asyncio
async def test_create_role_real_conflict(db_session):
    """Test create role with REAL conflict - NO mocks."""
    from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
    from app.infrastructure.database.repositories.role_repository import SQLAlchemyRoleRepository
    
    # Create real tenant
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug=f"test-{uuid4().hex[:8]}",
        plan="free",
        is_active=True,
    )
    tenant = await tenant_repo.create(tenant)
    await db_session.flush()
    
    # Create first role
    role_repo = SQLAlchemyRoleRepository(db_session)
    first_role = Role(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Admin",
        description="Admin role",
        permissions=[],
        is_system=False,
    )
    await role_repo.create(first_role)
    await db_session.flush()
    
    # Try to create duplicate - REAL conflict
    request = RoleCreate(
        name="Admin",  # Same name
        description="Duplicate admin",
        permissions=[],
    )
    
    with pytest.raises(HTTPException) as exc:
        await create_role(
            request=request,
            superuser_id=uuid4(),
            tenant_id=tenant.id,
            session=db_session,
        )
    
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_role_real_invalid_permission(db_session):
    """Test update role with REAL invalid permission - NO mocks."""
    from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
    from app.infrastructure.database.repositories.role_repository import SQLAlchemyRoleRepository
    
    # Create real tenant and role
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug=f"test-{uuid4().hex[:8]}",
        plan="free",
        is_active=True,
    )
    tenant = await tenant_repo.create(tenant)
    await db_session.flush()
    
    role_repo = SQLAlchemyRoleRepository(db_session)
    role = Role(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Role",
        description="Test",
        permissions=[],
        is_system=False,
    )
    role = await role_repo.create(role)
    await db_session.flush()
    
    # Update with invalid permission format
    request = RoleUpdate(
        permissions=["invalid:format:too:many:colons"],
    )
    
    with pytest.raises(HTTPException) as exc:
        await update_role(
            role_id=role.id,
            request=request,
            superuser_id=uuid4(),
            session=db_session,
        )
    
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_user_permissions_real_not_found(db_session):
    """Test get permissions for non-existent user - REAL query."""
    from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
    
    # Create real tenant
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug=f"test-{uuid4().hex[:8]}",
        plan="free",
        is_active=True,
    )
    await tenant_repo.create(tenant)
    await db_session.flush()
    
    # Query non-existent user - REAL database query
    non_existent_id = uuid4()
    
    with pytest.raises(HTTPException) as exc:
        await get_user_permissions(
            user_id=non_existent_id,
            current_user_id=uuid4(),
            session=db_session,
        )
    
    assert exc.value.status_code == 404
    assert "USER_NOT_FOUND" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_create_role_success_real(db_session):
    """Test successful role creation with REAL database."""
    from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
    
    # Create real tenant
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug=f"test-{uuid4().hex[:8]}",
        plan="free",
        is_active=True,
    )
    tenant = await tenant_repo.create(tenant)
    await db_session.flush()
    
    # Create role - REAL operation
    request = RoleCreate(
        name="Editor",
        description="Editor role",
        permissions=["posts:read", "posts:write"],
    )
    
    result = await create_role(
        request=request,
        superuser_id=uuid4(),
        tenant_id=tenant.id,
        session=db_session,
    )
    
    assert result.name == "Editor"
    assert len(result.permissions) == 2
    assert "posts:read" in result.permissions
