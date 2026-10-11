"""sprint_04_review_audit_logs

Revision ID: 7b8c9d0e1f2a
Revises: 6a7b8c9d0e1f
Create Date: 2026-10-07 07:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b8c9d0e1f2a"
down_revision: str | Sequence[str] | None = "6a7b8c9d0e1f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica migração da Sprint 04: tabela review_audit_logs e índices cobridores."""
    op.create_table(
        "review_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("historical_subject_name", sa.String(length=100), nullable=False),
        sa.Column("historical_topic_name", sa.String(length=100), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level_before", sa.Integer(), nullable=False),
        sa.Column("level_after", sa.Integer(), nullable=False),
        sa.Column("evaluation_mode", sa.String(length=20), nullable=False, server_default="MANUAL"),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_review_audit_logs_user_id",
        "review_audit_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_audit_logs_question_id",
        "review_audit_logs",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_audit_logs_subject_id",
        "review_audit_logs",
        ["subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_audit_logs_topic_id",
        "review_audit_logs",
        ["topic_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_audit_logs_review_date",
        "review_audit_logs",
        ["review_date"],
        unique=False,
    )
    op.create_index(
        "ix_review_audit_logs_user_subject",
        "review_audit_logs",
        ["user_id", "subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_audit_logs_user_date",
        "review_audit_logs",
        ["user_id", "review_date"],
        unique=False,
        postgresql_include=["score", "level_before", "level_after", "logged_at"],
    )


def downgrade() -> None:
    """Remove a tabela review_audit_logs e seus índices associados."""
    op.drop_index("ix_review_audit_logs_user_date", table_name="review_audit_logs")
    op.drop_index("ix_review_audit_logs_user_subject", table_name="review_audit_logs")
    op.drop_index("ix_review_audit_logs_review_date", table_name="review_audit_logs")
    op.drop_index("ix_review_audit_logs_topic_id", table_name="review_audit_logs")
    op.drop_index("ix_review_audit_logs_subject_id", table_name="review_audit_logs")
    op.drop_index("ix_review_audit_logs_question_id", table_name="review_audit_logs")
    op.drop_index("ix_review_audit_logs_user_id", table_name="review_audit_logs")
    op.drop_table("review_audit_logs")
