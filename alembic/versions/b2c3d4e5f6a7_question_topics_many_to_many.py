"""question_topics_many_to_many

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-12 06:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica migração para associação N:N entre questions e topics."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if "question_topics" not in existing_tables:
        op.create_table(
            "question_topics",
            sa.Column("question_id", sa.Uuid(), nullable=False),
            sa.Column("topic_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("question_id", "topic_id"),
        )
        op.create_index(
            "ix_question_topics_topic_id",
            "question_topics",
            ["topic_id"],
            unique=False,
        )

        # Migração de dados existente: preserva relacionamentos 1:N no modelo N:N (Zero Data Loss)
        op.execute(
            "INSERT INTO question_topics (question_id, topic_id) "
            "SELECT id, topic_id FROM questions WHERE topic_id IS NOT NULL"
        )

    # Torna topic_id opcional em questions
    with op.batch_alter_table("questions") as batch_op:
        batch_op.alter_column("topic_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    """Reverte associação N:N."""
    op.execute(
        "UPDATE questions SET topic_id = ("
        "  SELECT topic_id FROM question_topics "
        "  WHERE question_topics.question_id = questions.id LIMIT 1"
        ") WHERE topic_id IS NULL"
    )

    op.drop_index("ix_question_topics_topic_id", table_name="question_topics")
    op.drop_table("question_topics")
