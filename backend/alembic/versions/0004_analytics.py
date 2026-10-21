"""privacy-conscious daily analytics counters

Revision ID: 0004_analytics
Revises: 0003_auth
Create Date: 2026-10-21 00:00:02.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_analytics"
down_revision: Union[str, Sequence[str], None] = "0003_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analytics_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("event", sa.String(length=50), nullable=False),
        sa.Column("dimension", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ux_analytics_day_event_dim", "analytics_daily", ["day", "event", "dimension"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_analytics_day_event_dim", table_name="analytics_daily")
    op.drop_table("analytics_daily")
