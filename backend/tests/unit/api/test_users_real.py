# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Real integration tests for users endpoints without excessive mocking.
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.endpoints.users import (
    list_users,
    get_user,
    update_self,
    update_user,
    delete_user,
)
from app.api.v1.schemas.users import UserUpdateSelf, UserUpdate
from app.domain.entities.user import User
from app.domain.entities.tenant import Tenant
from app.infrastructure.database.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.database.repositories.tenant_repository import SQLAlchemyTenantRepository
from app.infrastructure.auth.jwt_handler import hash_password


@pytest.fixture
async def test_tenant(db_session):
    """Create a test tenant with unique slug."""
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    
    unique_id = str(uuid4())[:8]
    tenant = Tenant(
        id=uuid4(),
        name=f"Test Company {unique_id}",
        slug=f"test-company-{unique_id}",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    created_tenant = await tenant_repo.create(tenant)
    await db_session.flush()
    
    return created_tenant


@pytest.fixture
async def test_user(db_session, test_tenant):
    """Create a test user with unique email."""
    user_repo = SQLAlchemyUserRepository(db_session)
    
    unique_id = str(uuid4())[:8]
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"testuser-{unique_id}@example.com",
        password_hash=hash_password("Test123!@#"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_superuser=False,
        email_verified=True,
        roles=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    created_user = await user_repo.create(user)
    await db_session.flush()
    
    return created_user


@pytest.fixture
async def test_admin_user(db_session, test_tenant):
    """Create a test admin user."""
    user_repo = SQLAlchemyUserRepository(db_session)
    
    unique_id = str(uuid4())[:8]
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"admin-{unique_id}@example.com",
        password_hash=hash_password("Admin123!@#"),
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_superuser=True,
        email_verified=True,
        roles=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    
    created_user = await user_repo.create(user)
    await db_session.flush()
    
    return created_user


class TestUpdateSelf:
    """Tests for PATCH /users/me endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_me_first_name(self, db_session, test_user):
        """Test updating first name."""
        update_req = UserUpdateSelf(
            first_name="Updated",
            last_name=None,
        )
        
        result = await update_self(
            current_user_id=test_user.id,
            request=update_req,
            session=db_session,
        )
        
        assert result.first_name == "Updated"
        assert result.last_name == test_user.last_name  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_me_last_name(self, db_session, test_user):
        """Test updating last name."""
        update_req = UserUpdateSelf(
            first_name=None,
            last_name="NewLastName",
        )
        
        result = await update_self(
            current_user_id=test_user.id,
            request=update_req,
            session=db_session,
        )
        
        assert result.first_name == test_user.first_name  # Unchanged
        assert result.last_name == "NewLastName"
    
    @pytest.mark.asyncio
    async def test_update_me_both_names(self, db_session, test_user):
        """Test updating both names."""
        update_req = UserUpdateSelf(
            first_name="NewFirst",
            last_name="NewLast",
        )
        
        result = await update_self(
            current_user_id=test_user.id,
            request=update_req,
            session=db_session,
        )
        
        assert result.first_name == "NewFirst"
        assert result.last_name == "NewLast"


class TestListUsers:
    """Tests for GET /users endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_users_as_admin(self, db_session, test_admin_user, test_user):
        """Test listing users as admin."""
        result = await list_users(
            current_user_id=test_admin_user.id,
            session=db_session,
            page=1,
            page_size=10,
            is_active=None,
        )
        
        assert result.total >= 2  # At least admin and test user
        assert len(result.items) >= 2
        user_ids = [u.id for u in result.items]
        assert test_admin_user.id in user_ids
        assert test_user.id in user_ids
    
    @pytest.mark.asyncio
    async def test_list_users_pagination(self, db_session, test_admin_user):
        """Test pagination works."""
        result = await list_users(
            current_user_id=test_admin_user.id,
            session=db_session,
            page=1,
            page_size=1,
            is_active=None,
        )
        
        assert len(result.items) == 1
        assert result.page == 1
        assert result.page_size == 1


class TestGetUser:
    """Tests for GET /users/{user_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_user_success(self, db_session, test_admin_user, test_user):
        """Test getting specific user."""
        result = await get_user(
            user_id=test_user.id,
            current_user_id=test_admin_user.id,
            session=db_session,
        )
        
        assert result.id == test_user.id
        assert result.email == str(test_user.email)
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, db_session, test_admin_user):
        """Test getting non-existent user."""
        non_existent_id = uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_user(
                user_id=non_existent_id,
                current_user_id=test_admin_user.id,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 404
        assert "USER_NOT_FOUND" in str(exc_info.value.detail)


class TestUpdateUser:
    """Tests for PUT /users/{user_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_user_first_name(self, db_session, test_admin_user, test_user):
        """Test admin updating user's first name."""
        update_req = UserUpdate(
            first_name="AdminUpdated",
            last_name=None,
        )
        
        result = await update_user(
            user_id=test_user.id,
            request=update_req,
            superuser_id=test_admin_user.id,
            session=db_session,
        )
        
        assert result.first_name == "AdminUpdated"
    
    @pytest.mark.asyncio
    async def test_update_user_last_name(self, db_session, test_admin_user, test_user):
        """Test admin updating user's last name."""
        update_req = UserUpdate(
            first_name=None,
            last_name="AdminUpdatedLast",
        )
        
        result = await update_user(
            user_id=test_user.id,
            request=update_req,
            superuser_id=test_admin_user.id,
            session=db_session,
        )
        
        assert result.last_name == "AdminUpdatedLast"
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(self, db_session, test_admin_user):
        """Test updating non-existent user."""
        non_existent_id = uuid4()
        update_req = UserUpdate(
            first_name="Test",
            last_name=None,
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id=non_existent_id,
                request=update_req,
                superuser_id=test_admin_user.id,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 404
        assert "USER_NOT_FOUND" in str(exc_info.value.detail)


class TestDeleteUser:
    """Tests for DELETE /users/{user_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self, db_session, test_admin_user, test_user):
        """Test deleting a user (soft delete)."""
        result = await delete_user(
            user_id=test_user.id,
            superuser_id=test_admin_user.id,
            session=db_session,
        )
        
        assert result.success is True
        assert str(test_user.id) in result.message
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, db_session, test_admin_user):
        """Test deleting non-existent user."""
        non_existent_id = uuid4()
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_user(
                user_id=non_existent_id,
                superuser_id=test_admin_user.id,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 404
        assert "ENTITY_NOT_FOUND" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_delete_self_forbidden(self, db_session, test_admin_user):
        """Test that user cannot delete themselves."""
        with pytest.raises(HTTPException) as exc_info:
            await delete_user(
                user_id=test_admin_user.id,
                superuser_id=test_admin_user.id,
                session=db_session,
            )
        
        assert exc_info.value.status_code == 400
        assert "CANNOT_DELETE_SELF" in str(exc_info.value.detail)
