"""Create orders table.

Revision ID: 20260807_0001
Revises:
Create Date: 2026-08-07
"""

import sqlalchemy as sa
from alembic import op

revision = "20260807_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_order_id", sa.String(length=128), nullable=False),
        sa.Column("restaurant_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_order_id", name="uq_order_provider_external_id"),
    )
    op.create_index("ix_orders_restaurant_id", "orders", ["restaurant_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_restaurant_id", table_name="orders")
    op.drop_table("orders")
