import asyncio

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from backend.app.core.config import PROJECT_ROOT
from backend.app.core.database import engine


async def _database_state() -> tuple[bool, bool, bool]:
    async with engine.connect() as connection:
        def inspect_database(sync: Connection) -> tuple[list[str], list[str]]:
            inspector = inspect(sync)
            tables = inspector.get_table_names()
            image_columns = (
                [column["name"] for column in inspector.get_columns("product_images")]
                if "product_images" in tables
                else []
            )
            return tables, image_columns

        table_names, image_columns = await connection.run_sync(inspect_database)
    await engine.dispose()
    has_image_blob = {"content_type", "content"}.issubset(image_columns)
    return bool(table_names), "alembic_version" in table_names, has_image_blob


def migrate() -> None:
    has_tables, has_version_table, has_image_blob = asyncio.run(_database_state())
    config = Config(PROJECT_ROOT / "alembic.ini")
    if has_tables and not has_version_table:
        # Existing deployments were created from the initial metadata before Alembic was enabled.
        command.stamp(config, "imageblob01" if has_image_blob else "cba50cd9b79b")
        command.upgrade(config, "head")
    else:
        command.upgrade(config, "head")


if __name__ == "__main__":
    migrate()
