"""add product view events

Revision ID: analytics01
Revises: imageblob01
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "analytics01"
down_revision: str | Sequence[str] | None = "imageblob01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "product_view_events" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "product_view_events",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("session_key", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "product_id", "session_key", "source", "viewed_at"):
        op.create_index(f"ix_product_view_events_{column}", "product_view_events", [column])


def downgrade() -> None:
    if "product_view_events" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("product_view_events")
