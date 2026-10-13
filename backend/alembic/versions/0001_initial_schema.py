"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dsa_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("mode", sa.String(length=100), nullable=True),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("difficulty", sa.String(length=50), nullable=False),
        sa.Column("problem_name", sa.String(length=255), nullable=True),
        sa.Column("problem", sa.Text(), nullable=True),
        sa.Column("solution", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("tier", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dsa_attempts_id"), "dsa_attempts", ["id"], unique=False)
    op.create_index(op.f("ix_dsa_attempts_session_id"), "dsa_attempts", ["session_id"], unique=False)

    op.create_table(
        "interview_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("rounds", sa.Integer(), nullable=True),
        sa.Column("average_score", sa.Float(), nullable=True),
        sa.Column("strong_points", sa.Text(), nullable=True),
        sa.Column("weak_points", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interview_reports_id"), "interview_reports", ["id"], unique=False)
    op.create_index(op.f("ix_interview_reports_session_id"), "interview_reports", ["session_id"], unique=False)

    op.create_table(
        "ml_practice_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("verdict", sa.String(length=50), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("missing_points", sa.Text(), nullable=True),
        sa.Column("corrected_answer", sa.Text(), nullable=True),
        sa.Column("improvement", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ml_practice_attempts_id"), "ml_practice_attempts", ["id"], unique=False)
    op.create_index(op.f("ix_ml_practice_attempts_session_id"), "ml_practice_attempts", ["session_id"], unique=False)

    op.create_table(
        "project_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("challenge_id", sa.String(length=255), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column("project_title", sa.String(length=255), nullable=True),
        sa.Column("challenge_json", sa.Text(), nullable=True),
        sa.Column("submission", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("verdict", sa.String(length=50), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("missing_points", sa.Text(), nullable=True),
        sa.Column("improved_approach", sa.Text(), nullable=True),
        sa.Column("next_steps", sa.Text(), nullable=True),
        sa.Column("architecture_review", sa.Text(), nullable=True),
        sa.Column("file_findings", sa.Text(), nullable=True),
        sa.Column("bugs", sa.Text(), nullable=True),
        sa.Column("security_issues", sa.Text(), nullable=True),
        sa.Column("missing_requirements", sa.Text(), nullable=True),
        sa.Column("files_reviewed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_attempts_challenge_id"), "project_attempts", ["challenge_id"], unique=False)
    op.create_index(op.f("ix_project_attempts_id"), "project_attempts", ["id"], unique=False)
    op.create_index(op.f("ix_project_attempts_session_id"), "project_attempts", ["session_id"], unique=False)

    op.create_table(
        "project_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("challenge_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column("project_title", sa.String(length=255), nullable=True),
        sa.Column("challenge_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_challenges_challenge_id"), "project_challenges", ["challenge_id"], unique=True)
    op.create_index(op.f("ix_project_challenges_id"), "project_challenges", ["id"], unique=False)
    op.create_index(op.f("ix_project_challenges_session_id"), "project_challenges", ["session_id"], unique=False)

    op.create_table(
        "revoked_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_revoked_sessions_id"), "revoked_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_revoked_sessions_session_id"), "revoked_sessions", ["session_id"], unique=False)
    op.create_index(op.f("ix_revoked_sessions_token_hash"), "revoked_sessions", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_revoked_sessions_token_hash"), table_name="revoked_sessions")
    op.drop_index(op.f("ix_revoked_sessions_session_id"), table_name="revoked_sessions")
    op.drop_index(op.f("ix_revoked_sessions_id"), table_name="revoked_sessions")
    op.drop_table("revoked_sessions")

    op.drop_index(op.f("ix_project_challenges_session_id"), table_name="project_challenges")
    op.drop_index(op.f("ix_project_challenges_id"), table_name="project_challenges")
    op.drop_index(op.f("ix_project_challenges_challenge_id"), table_name="project_challenges")
    op.drop_table("project_challenges")

    op.drop_index(op.f("ix_project_attempts_session_id"), table_name="project_attempts")
    op.drop_index(op.f("ix_project_attempts_id"), table_name="project_attempts")
    op.drop_index(op.f("ix_project_attempts_challenge_id"), table_name="project_attempts")
    op.drop_table("project_attempts")

    op.drop_index(op.f("ix_ml_practice_attempts_session_id"), table_name="ml_practice_attempts")
    op.drop_index(op.f("ix_ml_practice_attempts_id"), table_name="ml_practice_attempts")
    op.drop_table("ml_practice_attempts")

    op.drop_index(op.f("ix_interview_reports_session_id"), table_name="interview_reports")
    op.drop_index(op.f("ix_interview_reports_id"), table_name="interview_reports")
    op.drop_table("interview_reports")

    op.drop_index(op.f("ix_dsa_attempts_session_id"), table_name="dsa_attempts")
    op.drop_index(op.f("ix_dsa_attempts_id"), table_name="dsa_attempts")
    op.drop_table("dsa_attempts")
