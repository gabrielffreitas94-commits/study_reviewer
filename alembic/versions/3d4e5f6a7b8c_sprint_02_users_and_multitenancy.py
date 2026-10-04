"""sprint_02_users_and_multitenancy

Revision ID: 3d4e5f6a7b8c
Revises: 2c3e4f5a6b7c
Create Date: 2026-10-04 18:30:00.000000

"""

from collections.abc import Sequence
from datetime import date
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d4e5f6a7b8c"
down_revision: str | Sequence[str] | None = "2c3e4f5a6b7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica migração da Sprint 02: tabela users, colunas de tenancy e índices."""
    # 1. Cria tabela users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("google_sub", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. Usuário de migração para backfill de integridade relacional
    default_user_id = uuid4()
    users_table = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("google_sub", sa.String()),
        sa.column("email", sa.String()),
        sa.column("name", sa.String()),
        sa.column("created_at", sa.Date()),
    )
    op.bulk_insert(
        users_table,
        [
            {
                "id": default_user_id,
                "google_sub": "system-migration-sub",
                "email": "sistema@studyreviewer.local",
                "name": "Usuário do Sistema",
                "created_at": date.today(),
            }
        ],
    )

    # 3. Adiciona colunas owner_id e is_public em subjects
    with op.batch_alter_table("subjects", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "owner_id",
                sa.Uuid(),
                nullable=False,
                server_default=str(default_user_id),
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_public",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0" if op.get_bind().dialect.name == "sqlite" else "false"),
            )
        )
        batch_op.create_foreign_key(
            "fk_subjects_owner_id_users",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_subjects_owner_public", ["owner_id", "is_public"], unique=False)

    # 4. Adiciona coluna user_id em flashcard_pool_sessions
    with op.batch_alter_table("flashcard_pool_sessions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "user_id",
                sa.Uuid(),
                nullable=False,
                server_default=str(default_user_id),
            )
        )
        batch_op.create_foreign_key(
            "fk_sessions_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_sessions_user_filters",
            ["user_id", "subject_id_filter", "topic_id_filter"],
            unique=False,
        )


def downgrade() -> None:
    """Reverte alterações da Sprint 02."""
    with op.batch_alter_table("flashcard_pool_sessions", schema=None) as batch_op:
        batch_op.drop_index("ix_sessions_user_filters")
        batch_op.drop_constraint("fk_sessions_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("subjects", schema=None) as batch_op:
        batch_op.drop_index("ix_subjects_owner_public")
        batch_op.drop_constraint("fk_subjects_owner_id_users", type_="foreignkey")
        batch_op.drop_column("is_public")
        batch_op.drop_column("owner_id")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_table("users")
