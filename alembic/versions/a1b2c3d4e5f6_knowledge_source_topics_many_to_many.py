"""knowledge_source_topics_many_to_many

Revision ID: a1b2c3d4e5f6
Revises: 9d0e1f2a3b4c
Create Date: 2026-10-11 22:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "9d0e1f2a3b4c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica migração para associação N:N entre knowledge_sources e topics."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if "knowledge_source_topics" not in existing_tables:
        op.create_table(
            "knowledge_source_topics",
            sa.Column("source_id", sa.Uuid(), nullable=False),
            sa.Column("topic_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("source_id", "topic_id"),
        )
        op.create_index(
            "ix_knowledge_source_topics_topic_id",
            "knowledge_source_topics",
            ["topic_id"],
            unique=False,
        )

        # Migração de dados existente: preserva relacionamentos 1:N no modelo N:N (Zero Data Loss)
        op.execute(
            "INSERT INTO knowledge_source_topics (source_id, topic_id) "
            "SELECT id, topic_id FROM knowledge_sources WHERE topic_id IS NOT NULL"
        )

    # Torna topic_id opcional em knowledge_sources
    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.alter_column("topic_id", existing_type=sa.Uuid(), nullable=True)

    # Torna topic_id opcional em knowledge_chunks
    with op.batch_alter_table("knowledge_chunks") as batch_op:
        batch_op.alter_column("topic_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    """Reverte associação N:N."""
    op.execute(
        "UPDATE knowledge_sources SET topic_id = ("
        "  SELECT topic_id FROM knowledge_source_topics "
        "  WHERE knowledge_source_topics.source_id = knowledge_sources.id LIMIT 1"
        ") WHERE topic_id IS NULL"
    )

    op.drop_index("ix_knowledge_source_topics_topic_id", table_name="knowledge_source_topics")
    op.drop_table("knowledge_source_topics")
