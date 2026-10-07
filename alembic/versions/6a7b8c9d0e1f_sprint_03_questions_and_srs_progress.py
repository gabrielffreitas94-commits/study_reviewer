"""sprint_03_questions_and_srs_progress

Revision ID: 6a7b8c9d0e1f
Revises: 5f6a7b8c9d0e
Create Date: 2026-10-07 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a7b8c9d0e1f"
down_revision: str | Sequence[str] | None = "5f6a7b8c9d0e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica migração da Sprint 03: tabelas questions e user_question_progress."""
    # 1. Cria tabela questions
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_questions_topic_id", "questions", ["topic_id"], unique=False)

    # 2. Cria tabela user_question_progress
    op.create_table(
        "user_question_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("current_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_review_date", sa.Date(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_id", name="uq_user_question_progress"),
    )
    op.create_index(
        "ix_user_question_progress_user_id",
        "user_question_progress",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_question_progress_question_id",
        "user_question_progress",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_question_progress_next_review_date",
        "user_question_progress",
        ["next_review_date"],
        unique=False,
    )
    op.create_index(
        "ix_user_question_due_covering",
        "user_question_progress",
        ["user_id", "next_review_date"],
        unique=False,
        postgresql_include=["question_id", "current_level", "last_reviewed_at"],
    )


def downgrade() -> None:
    """Remove tabelas da Sprint 03 em ordem reversa estrita para manter integridade referencial."""
    op.drop_index("ix_user_question_due_covering", table_name="user_question_progress")
    op.drop_index("ix_user_question_progress_next_review_date", table_name="user_question_progress")
    op.drop_index("ix_user_question_progress_question_id", table_name="user_question_progress")
    op.drop_index("ix_user_question_progress_user_id", table_name="user_question_progress")
    op.drop_table("user_question_progress")

    op.drop_index("ix_questions_topic_id", table_name="questions")
    op.drop_table("questions")
