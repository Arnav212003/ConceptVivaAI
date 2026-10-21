"""evaluation status and grading provenance

Adds evaluation_status / prompt_version / model_name / integrity_flags to scored
attempt tables, plus judge result columns on dsa_attempts. Purely additive:
existing rows become evaluation_status='completed' and keep their scores.

Revision ID: 0002_evaluation_status
Revises: 0001_initial_schema
Create Date: 2026-10-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_evaluation_status"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCORED_TABLES = ("ml_practice_attempts", "dsa_attempts", "project_attempts")


def upgrade() -> None:
    for table in SCORED_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("evaluation_status", sa.String(length=20), nullable=False, server_default="completed"))
            batch.add_column(sa.Column("prompt_version", sa.String(length=60), nullable=True))
            batch.add_column(sa.Column("model_name", sa.String(length=100), nullable=True))
            batch.add_column(sa.Column("integrity_flags", sa.Text(), nullable=True))

    with op.batch_alter_table("dsa_attempts") as batch:
        batch.add_column(sa.Column("scoring_method", sa.String(length=30), nullable=True))
        batch.add_column(sa.Column("judge_verdict", sa.String(length=40), nullable=True))
        batch.add_column(sa.Column("judge_submission_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("tests_passed", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("tests_total", sa.Integer(), nullable=True))

    for table in SCORED_TABLES:
        op.create_index(f"ix_{table}_session_status", table, ["session_id", "evaluation_status"])


def downgrade() -> None:
    for table in SCORED_TABLES:
        op.drop_index(f"ix_{table}_session_status", table_name=table)

    with op.batch_alter_table("dsa_attempts") as batch:
        for column in ("tests_total", "tests_passed", "judge_submission_id", "judge_verdict", "scoring_method"):
            batch.drop_column(column)

    for table in SCORED_TABLES:
        with op.batch_alter_table(table) as batch:
            for column in ("integrity_flags", "model_name", "prompt_version", "evaluation_status"):
                batch.drop_column(column)
