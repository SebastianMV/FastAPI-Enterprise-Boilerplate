"""Script to cleanup E2E test users from the database."""
import asyncio
from sqlalchemy import delete, select

from app.infrastructure.database.connection import get_db_context
from app.infrastructure.database.models import UserModel


async def cleanup_e2e_users():
    """Delete all E2E test users from the database."""
    async with get_db_context() as session:
        # First, count how many users will be deleted
        count_stmt = select(UserModel).where(
            UserModel.email.like("e2e_%@example.com")
        )
        result = await session.execute(count_stmt)
        users_to_delete = result.scalars().all()
        count = len(users_to_delete)
        
        if count == 0:
            print("✅ No E2E test users found to cleanup")
            return
        
        # Delete the users
        delete_stmt = delete(UserModel).where(
            UserModel.email.like("e2e_%@example.com")
        )
        await session.execute(delete_stmt)
        await session.commit()
        
        print(f"✅ Cleaned up {count} E2E test users:")
        for user in users_to_delete:
            print(f"   - {user.email}")


if __name__ == "__main__":
    asyncio.run(cleanup_e2e_users())
