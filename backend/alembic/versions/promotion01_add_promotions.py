"""add promotions

Revision ID: promotion01
Revises: analytics01
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "promotion01"
down_revision: str | Sequence[str] | None = "analytics01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "promotions" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "promotions",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=True),
        sa.Column("promotion_type", sa.String(length=20), nullable=False),
        sa.Column("value", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "minimum_amount",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("product_id", "promotion_type", "starts_at", "ends_at", "enabled"):
        op.create_index(f"ix_promotions_{column}", "promotions", [column])


def downgrade() -> None:
    if "promotions" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("promotions")
