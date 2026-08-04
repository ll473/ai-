import asyncio

from backend.app.core.database import engine
from backend.app.models import Base


async def init_db() -> None:
    """Create tables for local development.

    Production deployments should use Alembic migrations instead.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())

