"""store uploaded images in database

Revision ID: imageblob01
Revises: cba50cd9b79b
Create Date: 2026-08-12 15:45:42.953070
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "imageblob01"
down_revision: str | Sequence[str] | None = "cba50cd9b79b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("product_images")}
    if "content_type" not in existing:
        op.add_column(
            "product_images",
            sa.Column("content_type", sa.String(length=100), nullable=True),
        )
    if "content" not in existing:
        op.add_column("product_images", sa.Column("content", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("product_images")}
    if "content" in existing:
        op.drop_column("product_images", "content")
    if "content_type" in existing:
        op.drop_column("product_images", "content_type")
