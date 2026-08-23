"""add search discovery events

Revision ID: search001
Revises: promotion01
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "search001"
down_revision: str | Sequence[str] | None = "promotion01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "search_events" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "search_events",
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("product_id", sa.BigInteger(), nullable=True),
        sa.Column("session_key", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("query", sa.String(length=200), nullable=True),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "user_id",
        "product_id",
        "session_key",
        "event_type",
        "query",
        "occurred_at",
    ):
        op.create_index(f"ix_search_events_{column}", "search_events", [column])


def downgrade() -> None:
    if "search_events" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("search_events")
