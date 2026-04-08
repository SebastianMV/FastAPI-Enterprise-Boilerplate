"""Script to create test user for E2E testing."""

import asyncio
from uuid import uuid4

import bcrypt
from sqlalchemy import select

from app.infrastructure.database.connection import get_db_context
from app.infrastructure.database.models import TenantModel, UserModel


async def create_test_user():
    """Create test user and tenant."""
    async with get_db_context() as session:
        # Get or create tenant
        result = await session.execute(select(TenantModel).limit(1))
        tenant = result.scalar_one_or_none()

        if not tenant:
            tenant = TenantModel(
                id=uuid4(),
                name="Test Tenant",
                slug="test-tenant",
                domain="test.com",
                is_active=True,
                is_deleted=False,
            )
            session.add(tenant)
            await session.flush()
            print(f"Created tenant: {tenant.name}")
        else:
            print(f"Using existing tenant: {tenant.name}")

        # Get or create user
        result = await session.execute(
            select(UserModel).where(UserModel.email == "test@example.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            password = b"Test123!"
            password_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")

            user = UserModel(
                id=uuid4(),
                tenant_id=tenant.id,
                email="test@example.com",
                password_hash=password_hash,
                first_name="Test",
                last_name="User",
                is_active=True,
                is_superuser=False,
                is_deleted=False,
            )
            session.add(user)
            await session.commit()
            print(f"✅ Created user: {user.email}")
            print("   Password: Test123!")
            print(f"   Tenant: {tenant.name}")
        else:
            print(f"✅ User already exists: {user.email}")
            print("   Password: Test123!")


if __name__ == "__main__":
    asyncio.run(create_test_user())
