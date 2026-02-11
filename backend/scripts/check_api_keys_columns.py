"""Check actual API keys columns in database."""

import asyncio

from sqlalchemy import text

from app.infrastructure.database.connection import engine


async def check():
    """Check columns."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'api_keys' ORDER BY ordinal_position"
            )
        )
        print("API Keys table columns:")
        for row in result:
            print(f"  - {row[0]}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check())
