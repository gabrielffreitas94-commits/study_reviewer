"""add_required_level_to_study_edges

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-26 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona coluna required_level à tabela study_edges."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    edge_cols = {c["name"] for c in insp.get_columns("study_edges")}
    if "required_level" not in edge_cols:
        with op.batch_alter_table("study_edges") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "required_level",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                )
            )


def downgrade() -> None:
    """Reverte adição da coluna required_level em study_edges."""
    with op.batch_alter_table("study_edges") as batch_op:
        batch_op.drop_column("required_level")
