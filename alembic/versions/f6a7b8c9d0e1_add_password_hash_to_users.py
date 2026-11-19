"""add_password_hash_to_users

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-19 10:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona coluna password_hash à tabela users de forma idempotente."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "password_hash" not in user_cols:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "password_hash",
                    sa.String(255),
                    nullable=True,
                )
            )


def downgrade() -> None:
    """Reverte adição da coluna password_hash em users de forma idempotente."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "password_hash" in user_cols:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("password_hash")
