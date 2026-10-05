"""sprint_02_study_events_partitioned

Revision ID: 4e5f6a7b8c9d
Revises: 3d4e5f6a7b8c
Create Date: 2026-10-05 08:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e5f6a7b8c9d"
down_revision: str | Sequence[str] | None = "3d4e5f6a7b8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica migração: tabela de histórico study_events com particionamento temporal."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # DDL nativo particionado para PostgreSQL 16
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS study_events (
                id UUID DEFAULT gen_random_uuid(),
                reviewed_at TIMESTAMPTZ NOT NULL,
                user_id UUID,
                card_id UUID NOT NULL,
                session_id UUID NOT NULL,
                status VARCHAR(20) NOT NULL,
                device_id VARCHAR(50),
                CONSTRAINT pk_study_events PRIMARY KEY (reviewed_at, user_id, id),
                CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            ) PARTITION BY RANGE (reviewed_at);
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_study_events_user_card_review
            ON study_events (user_id, card_id, reviewed_at DESC)
            INCLUDE (status);
            """
        )
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS study_events_default PARTITION OF study_events DEFAULT;
            """
        )
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS study_events_y2026w41 PARTITION OF study_events
                FOR VALUES FROM ('2026-10-05 00:00:00+00') TO ('2026-10-12 00:00:00+00');
            """
        )
    else:
        # Fallback relacional padrão para SQLite (desenvolvimento / testes)
        op.create_table(
            "study_events",
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=True),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("card_id", sa.Uuid(), nullable=False),
            sa.Column("session_id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("device_id", sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("reviewed_at", "user_id", "id", name="pk_study_events"),
        )
        op.create_index(
            "ix_study_events_user_card_review",
            "study_events",
            ["user_id", "card_id", "reviewed_at"],
            unique=False,
        )


def downgrade() -> None:
    """Reverte tabela study_events."""
    op.drop_table("study_events")
