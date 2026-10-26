"""unify_rpg_grimoire_node_schema

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona theory_content, raw_text e node_id a study_nodes, knowledge_sources e questions."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1. study_nodes.theory_content
    node_cols = {c["name"] for c in insp.get_columns("study_nodes")}
    if "theory_content" not in node_cols:
        with op.batch_alter_table("study_nodes") as batch_op:
            batch_op.add_column(
                sa.Column("theory_content", sa.Text(), nullable=False, server_default="")
            )

    # 2. knowledge_sources.raw_text e knowledge_sources.node_id
    ks_cols = {c["name"] for c in insp.get_columns("knowledge_sources")}
    with op.batch_alter_table("knowledge_sources") as batch_op:
        if "raw_text" not in ks_cols:
            batch_op.add_column(
                sa.Column("raw_text", sa.Text(), nullable=False, server_default="")
            )
        if "node_id" not in ks_cols:
            batch_op.add_column(
                sa.Column("node_id", sa.Uuid(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_knowledge_sources_node_id_study_nodes",
                "study_nodes",
                ["node_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_index("ix_knowledge_sources_node_id", ["node_id"])

    # 3. questions.node_id
    q_cols = {c["name"] for c in insp.get_columns("questions")}
    if "node_id" not in q_cols:
        with op.batch_alter_table("questions") as batch_op:
            batch_op.add_column(
                sa.Column("node_id", sa.Uuid(), nullable=True)
            )
            batch_op.create_foreign_key(
                "fk_questions_node_id_study_nodes",
                "study_nodes",
                ["node_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_index("ix_questions_node_id", ["node_id"])


def downgrade() -> None:
    """Reverte adições de theory_content, raw_text e node_id."""
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_index("ix_questions_node_id")
        batch_op.drop_constraint("fk_questions_node_id_study_nodes", type_="foreignkey")
        batch_op.drop_column("node_id")

    with op.batch_alter_table("knowledge_sources") as batch_op:
        batch_op.drop_index("ix_knowledge_sources_node_id")
        batch_op.drop_constraint("fk_knowledge_sources_node_id_study_nodes", type_="foreignkey")
        batch_op.drop_column("node_id")
        batch_op.drop_column("raw_text")

    with op.batch_alter_table("study_nodes") as batch_op:
        batch_op.drop_column("theory_content")
