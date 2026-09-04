"""Add Poster order forwarding state.

Revision ID: 20260904_0002
Revises: 20260807_0001
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "20260904_0002"
down_revision = "20260807_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "forwarding_status",
            sa.String(length=24),
            server_default="not_requested",
            nullable=False,
        ),
    )
    op.add_column("orders", sa.Column("poster_order_id", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("forwarding_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "forwarding_error")
    op.drop_column("orders", "poster_order_id")
    op.drop_column("orders", "forwarding_status")
