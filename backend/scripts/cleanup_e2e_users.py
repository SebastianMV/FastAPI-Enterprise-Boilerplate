"""Script to cleanup E2E test users from the database.

This script removes all test users created during E2E testing,
including related data (API keys, OAuth connections, etc.).
Test users are identified by email pattern: e2e_%@example.com
"""

import asyncio

from sqlalchemy import delete, select

from app.infrastructure.database.connection import get_db_context
from app.infrastructure.database.models import (
    APIKeyModel,
    UserModel,
)


async def cleanup_e2e_users():
    """Delete all E2E test users and their related data from the database."""
    async with get_db_context() as session:
        # First, count how many users will be deleted
        count_stmt = select(UserModel).where(UserModel.email.like("e2e_%@example.com"))
        result = await session.execute(count_stmt)
        users_to_delete = result.scalars().all()
        count = len(users_to_delete)

        if count == 0:
            print("✅ No E2E test users found to cleanup")
            return

        # Get user IDs for cascading deletion
        user_ids = [user.id for user in users_to_delete]

        # Delete related API keys (cascade should handle this, but explicit is better)
        api_keys_stmt = delete(APIKeyModel).where(APIKeyModel.user_id.in_(user_ids))
        api_keys_result = await session.execute(api_keys_stmt)
        deleted_api_keys = api_keys_result.rowcount

        # Delete the users (cascade will handle OAuth connections and other relations)
        delete_stmt = delete(UserModel).where(UserModel.email.like("e2e_%@example.com"))
        await session.execute(delete_stmt)
        await session.commit()

        print(f"✅ Cleaned up {count} E2E test users")
        if deleted_api_keys > 0:
            print(f"✅ Deleted {deleted_api_keys} related API keys")
        print("\nDeleted users:")
        for user in users_to_delete[:10]:  # Show first 10
            print(f"   - {user.email}")
        if count > 10:
            print(f"   ... and {count - 10} more")


if __name__ == "__main__":
    asyncio.run(cleanup_e2e_users())
