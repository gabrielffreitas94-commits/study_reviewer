"""sprint_11_rpg_study_tree

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-25 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica migração para Árvore de Estudos RPG e tabelas associadas."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. Tabelas Principais do Grafo de Estudos
    if "study_maps" not in existing_tables:
        op.create_table(
            "study_maps",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("owner_id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("parent_node_id", sa.Uuid(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_study_maps_owner_public", "study_maps", ["owner_id", "is_public"])
        op.create_index("ix_study_maps_parent_node", "study_maps", ["parent_node_id"])

    if "study_nodes" not in existing_tables:
        op.create_table(
            "study_nodes",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("map_id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(150), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("pos_x", sa.Float(), nullable=False, server_default=sa.text("0.0")),
            sa.Column("pos_y", sa.Float(), nullable=False, server_default=sa.text("0.0")),
            sa.Column("icon", sa.String(50), nullable=False, server_default="brain"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["map_id"], ["study_maps.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_study_nodes_map", "study_nodes", ["map_id"])

    if "study_edges" not in existing_tables:
        op.create_table(
            "study_edges",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("map_id", sa.Uuid(), nullable=False),
            sa.Column("source_node_id", sa.Uuid(), nullable=False),
            sa.Column("target_node_id", sa.Uuid(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["map_id"], ["study_maps.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["source_node_id"], ["study_nodes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["target_node_id"], ["study_nodes.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("map_id", "source_node_id", "target_node_id", name="uq_study_edge"),
        )
        op.create_index("ix_study_edges_map", "study_edges", ["map_id"])
        op.create_index("ix_study_edges_source", "study_edges", ["source_node_id"])
        op.create_index("ix_study_edges_target", "study_edges", ["target_node_id"])

    # 2. Tabelas Associativas N:N de Conteúdo dos Nós
    if "node_knowledge_sources" not in existing_tables:
        op.create_table(
            "node_knowledge_sources",
            sa.Column("node_id", sa.Uuid(), nullable=False),
            sa.Column("source_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["node_id"], ["study_nodes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("node_id", "source_id"),
        )

    if "node_questions" not in existing_tables:
        op.create_table(
            "node_questions",
            sa.Column("node_id", sa.Uuid(), nullable=False),
            sa.Column("question_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["node_id"], ["study_nodes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("node_id", "question_id"),
        )

    if "node_flashcards" not in existing_tables:
        op.create_table(
            "node_flashcards",
            sa.Column("node_id", sa.Uuid(), nullable=False),
            sa.Column("flashcard_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["node_id"], ["study_nodes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["flashcard_id"], ["flashcards.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("node_id", "flashcard_id"),
        )

    # 3. Adicionar coluna owner_id às entidades de conteúdo para biblioteca pessoal
    for table_name in ("questions", "flashcards", "knowledge_sources"):
        columns = {c["name"] for c in insp.get_columns(table_name)}
        if "owner_id" not in columns:
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.add_column(sa.Column("owner_id", sa.Uuid(), nullable=True))
                batch_op.create_foreign_key(
                    f"fk_{table_name}_owner_id_users",
                    "users",
                    ["owner_id"],
                    ["id"],
                    ondelete="CASCADE",
                )
                batch_op.create_index(f"ix_{table_name}_owner_id", ["owner_id"])


def downgrade() -> None:
    """Reverte as alterações da Sprint 11."""
    op.drop_table("node_flashcards")
    op.drop_table("node_questions")
    op.drop_table("node_knowledge_sources")
    op.drop_table("study_edges")
    op.drop_table("study_nodes")
    op.drop_table("study_maps")

    for table_name in ("knowledge_sources", "flashcards", "questions"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_owner_id")
            batch_op.drop_constraint(f"fk_{table_name}_owner_id_users", type_="foreignkey")
            batch_op.drop_column("owner_id")
