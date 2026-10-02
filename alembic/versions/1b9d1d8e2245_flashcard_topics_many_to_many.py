"""flashcard_topics_many_to_many

Revision ID: 1b9d1d8e2245
Revises: fe2367db7277
Create Date: 2026-10-02 16:59:54.153660

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b9d1d8e2245"
down_revision: str | Sequence[str] | None = "fe2367db7277"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "flashcard_topics",
        sa.Column("flashcard_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["flashcard_id"], ["flashcards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("flashcard_id", "topic_id"),
    )
    op.create_index(
        op.f("ix_flashcard_topics_topic_id"), "flashcard_topics", ["topic_id"], unique=False
    )

    # Migração de dados existente: preserva relacionamentos 1:N no modelo N:N (Zero Data Loss)
    op.execute(
        "INSERT INTO flashcard_topics (flashcard_id, topic_id) "
        "SELECT id, topic_id FROM flashcards WHERE topic_id IS NOT NULL"
    )

    with op.batch_alter_table("flashcards") as batch_op:
        batch_op.drop_index(batch_op.f("ix_flashcards_topic_id"))
        batch_op.drop_column("topic_id")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("flashcards") as batch_op:
        batch_op.add_column(sa.Column("topic_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_flashcards_topic_id_topics", "topics", ["topic_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_index("ix_flashcards_topic_id", ["topic_id"], unique=False)

    op.execute(
        "UPDATE flashcards SET topic_id = ("
        "  SELECT topic_id FROM flashcard_topics "
        "  WHERE flashcard_topics.flashcard_id = flashcards.id LIMIT 1"
        ")"
    )

    op.drop_index(op.f("ix_flashcard_topics_topic_id"), table_name="flashcard_topics")
    op.drop_table("flashcard_topics")
