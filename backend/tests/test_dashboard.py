"""Test dashboard activity endpoint."""
import asyncio
from app.infrastructure.database.connection import get_db_context
from app.infrastructure.database.models import UserModel, APIKeyModel
from sqlalchemy import select


async def test():
    """Test that we can query users and api keys."""
    async with get_db_context() as session:
        # Test user query
        result = await session.execute(
            select(UserModel)
            .where(UserModel.deleted_at.is_(None))
            .order_by(UserModel.created_at.desc())
            .limit(5)
        )
        users = result.scalars().all()
        print(f"Found {len(users)} users")
        
        for user in users:
            print(f"  - {user.email}, created: {user.created_at}")
        
        # Test API key query
        result = await session.execute(
            select(APIKeyModel)
            .order_by(APIKeyModel.created_at.desc())
            .limit(5)
        )
        keys = result.scalars().all()
        print(f"Found {len(keys)} API keys")
        
        for key in keys:
            print(f"  - {key.name}, created: {key.created_at}")


if __name__ == "__main__":
    asyncio.run(test())
