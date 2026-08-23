import asyncio
from dataclasses import dataclass
from enum import StrEnum

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from backend.app.core.config import PROJECT_ROOT
from backend.app.core.database import engine

LEGACY_BASELINE_TABLES: frozenset[str] = frozenset(
    {
        "after_sale_rules",
        "agent_runs",
        "agent_steps",
        "ai_model_configs",
        "brands",
        "cart_items",
        "categories",
        "conversation_messages",
        "conversations",
        "favorites",
        "function_tools",
        "knowledge_chunks",
        "knowledge_documents",
        "operation_reports",
        "order_items",
        "orders",
        "payment_transactions",
        "product_images",
        "product_skus",
        "products",
        "prompt_templates",
        "recommendation_items",
        "recommendations",
        "review_analyses",
        "reviews",
        "tool_call_logs",
        "user_addresses",
        "users",
        "wallet_transactions",
        "wallets",
    }
)


class SchemaKind(StrEnum):
    EMPTY = "empty"
    VERSIONED = "versioned"
    RECOGNIZED_LEGACY = "recognized_legacy"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DatabaseState:
    kind: SchemaKind
    table_names: frozenset[str]
    has_image_blob: bool = False


def inspect_database(connection: Connection) -> DatabaseState:
    inspector = inspect(connection)
    table_names = frozenset(inspector.get_table_names())
    if not table_names:
        return DatabaseState(SchemaKind.EMPTY, table_names)
    if "alembic_version" in table_names:
        return DatabaseState(SchemaKind.VERSIONED, table_names)
    if not LEGACY_BASELINE_TABLES.issubset(table_names):
        return DatabaseState(SchemaKind.UNKNOWN, table_names)

    image_columns = {
        str(column["name"]) for column in inspector.get_columns("product_images")
    }
    has_image_blob = {"content_type", "content"}.issubset(image_columns)
    return DatabaseState(SchemaKind.RECOGNIZED_LEGACY, table_names, has_image_blob)


def stamp_revision_for(state: DatabaseState) -> str | None:
    if state.kind is SchemaKind.UNKNOWN:
        raise RuntimeError(
            "Unknown or partial unversioned database schema: automatic stamping was refused; "
            "manual remediation is required before migrations can continue."
        )
    if state.kind is SchemaKind.RECOGNIZED_LEGACY:
        return "imageblob01" if state.has_image_blob else "cba50cd9b79b"
    return None


async def _database_state() -> DatabaseState:
    async with engine.connect() as connection:
        state = await connection.run_sync(inspect_database)

    await engine.dispose()
    return state


def migrate() -> None:
    state = asyncio.run(_database_state())
    config = Config(PROJECT_ROOT / "alembic.ini")
    stamp_revision = stamp_revision_for(state)
    if stamp_revision is not None:
        # Existing deployments were created from the initial metadata before Alembic was enabled.
        command.stamp(config, stamp_revision)
    command.upgrade(config, "head")


if __name__ == "__main__":
    migrate()
