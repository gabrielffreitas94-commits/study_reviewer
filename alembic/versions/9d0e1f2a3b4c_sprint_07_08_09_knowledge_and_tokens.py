"""sprint_07_08_09_knowledge_and_tokens

Revision ID: 9d0e1f2a3b4c
Revises: 8c9d0e1f2a3b
Create Date: 2026-10-08 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d0e1f2a3b4c"
down_revision: str | Sequence[str] | None = "8c9d0e1f2a3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica migração das Sprints 07, 08 e 09: RAG e Token Ledger com idempotência estrita."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. Tabela knowledge_sources
    if "knowledge_sources" not in existing_tables:
        op.create_table(
            "knowledge_sources",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("topic_id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("content_type", sa.String(length=50), nullable=False, server_default="TEXT"),
            sa.Column("total_chunks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.Date(), nullable=False),
            sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_knowledge_sources_topic_id",
            "knowledge_sources",
            ["topic_id"],
            unique=False,
        )
        op.create_index(
            "ix_knowledge_sources_topic_created",
            "knowledge_sources",
            ["topic_id", "created_at"],
            unique=False,
        )

    # 2. Tabela knowledge_chunks
    if "knowledge_chunks" not in existing_tables:
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("source_id", sa.Uuid(), nullable=False),
            sa.Column("topic_id", sa.Uuid(), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", sa.JSON(), nullable=False),
            sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.Date(), nullable=False),
            sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_knowledge_chunks_source",
            "knowledge_chunks",
            ["source_id"],
            unique=False,
        )
        op.create_index(
            "ix_knowledge_chunks_topic",
            "knowledge_chunks",
            ["topic_id"],
            unique=False,
        )

    # 3. Tabela token_ledgers
    if "token_ledgers" not in existing_tables:
        op.create_table(
            "token_ledgers",
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("balance", sa.Integer(), nullable=False, server_default="1000"),
            sa.Column("held_balance", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id"),
        )
        op.create_index(
            "ix_token_ledgers_user_id",
            "token_ledgers",
            ["user_id"],
            unique=False,
        )

    # 4. Tabela token_transactions
    if "token_transactions" not in existing_tables:
        op.create_table(
            "token_transactions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("transaction_type", sa.String(length=20), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("reference_id", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_token_transactions_user_id",
            "token_transactions",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            "ix_token_transactions_user_created",
            "token_transactions",
            ["user_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Remove tabelas das Sprints 07, 08 e 09 em ordem reversa estrita."""
    op.drop_index("ix_token_transactions_user_created", table_name="token_transactions")
    op.drop_index("ix_token_transactions_user_id", table_name="token_transactions")
    op.drop_table("token_transactions")

    op.drop_index("ix_token_ledgers_user_id", table_name="token_ledgers")
    op.drop_table("token_ledgers")

    op.drop_index("ix_knowledge_chunks_topic", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_source", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index("ix_knowledge_sources_topic_created", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_topic_id", table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
