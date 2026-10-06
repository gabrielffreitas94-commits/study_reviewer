"""add_current_index_and_card_queue_to_sessions

Revision ID: 5f6a7b8c9d0e
Revises: 4e5f6a7b8c9d
Create Date: 2026-10-06 06:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f6a7b8c9d0e"
down_revision: str | Sequence[str] | None = "4e5f6a7b8c9d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona colunas current_index e card_queue à tabela flashcard_pool_sessions."""
    with op.batch_alter_table("flashcard_pool_sessions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "current_index",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "card_queue",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )


def downgrade() -> None:
    """Remove colunas current_index e card_queue da tabela flashcard_pool_sessions."""
    with op.batch_alter_table("flashcard_pool_sessions", schema=None) as batch_op:
        batch_op.drop_column("card_queue")
        batch_op.drop_column("current_index")
