import pytest
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

INITIAL_REVISION_TABLES = frozenset(
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


def create_tables(
    connection: Connection,
    table_names: set[str] | frozenset[str],
    *,
    image_blob: bool = False,
) -> None:
    for table_name in table_names:
        columns = (
            "id INTEGER, content_type TEXT, content BLOB"
            if table_name == "product_images" and image_blob
            else "id INTEGER"
        )
        connection.exec_driver_sql(f'CREATE TABLE "{table_name}" ({columns})')


def test_alembic_config_round_trips_percent_encoded_database_url() -> None:
    from backend.alembic.config import set_database_url

    database_url = "postgresql+asyncpg://shop:p%40ss@db.example.com/store"
    config = Config()

    set_database_url(config, database_url)

    assert config.get_main_option("sqlalchemy.url") == database_url


def test_unrelated_unversioned_schema_refuses_automatic_stamp() -> None:
    from backend.scripts.migrate import SchemaKind, inspect_database, stamp_revision_for

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        create_tables(connection, {"unrelated"})
        state = inspect_database(connection)

    assert state.kind is SchemaKind.UNKNOWN
    with pytest.raises(
        RuntimeError,
        match="automatic stamping was refused.*manual remediation is required",
    ):
        stamp_revision_for(state)


def test_partial_legacy_schema_refuses_automatic_stamp() -> None:
    from backend.scripts.migrate import SchemaKind, inspect_database, stamp_revision_for

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        create_tables(connection, INITIAL_REVISION_TABLES - {"tool_call_logs"})
        state = inspect_database(connection)

    assert state.kind is SchemaKind.UNKNOWN
    with pytest.raises(RuntimeError, match="manual remediation is required"):
        stamp_revision_for(state)


@pytest.mark.parametrize(
    "extra_tables",
    [set(), {"deployment_metadata"}],
    ids=["exact", "superset"],
)
def test_complete_legacy_schema_is_accepted(extra_tables: set[str]) -> None:
    from backend.scripts.migrate import SchemaKind, inspect_database, stamp_revision_for

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        create_tables(connection, INITIAL_REVISION_TABLES | extra_tables)
        state = inspect_database(connection)

    assert state.kind is SchemaKind.RECOGNIZED_LEGACY
    assert stamp_revision_for(state) == "cba50cd9b79b"


def test_legacy_image_blob_columns_select_image_blob_revision() -> None:
    from backend.scripts.migrate import inspect_database, stamp_revision_for

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        create_tables(connection, INITIAL_REVISION_TABLES, image_blob=True)
        state = inspect_database(connection)

    assert stamp_revision_for(state) == "imageblob01"


@pytest.mark.parametrize(
    ("table_names", "expected_kind"),
    [
        (set(), "empty"),
        ({"alembic_version", "unrelated"}, "versioned"),
    ],
    ids=["empty", "versioned"],
)
def test_empty_and_versioned_schemas_upgrade_without_stamping(
    table_names: set[str], expected_kind: str
) -> None:
    from backend.scripts.migrate import inspect_database, stamp_revision_for

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        create_tables(connection, table_names)
        state = inspect_database(connection)

    assert state.kind.value == expected_kind
    assert stamp_revision_for(state) is None
