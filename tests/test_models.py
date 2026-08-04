from backend.app.models import Base


def test_critical_tables_are_registered() -> None:
    tables = set(Base.metadata.tables)

    assert {
        "users",
        "wallets",
        "products",
        "product_skus",
        "orders",
        "agent_runs",
        "agent_steps",
        "function_tools",
        "knowledge_chunks",
        "recommendations",
    } <= tables

