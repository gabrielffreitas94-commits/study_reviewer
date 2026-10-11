"""add_audit_logs_pagination_index

Revision ID: 8c9d0e1f2a3b
Revises: 7b8c9d0e1f2a
Create Date: 2026-10-07 17:07:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c9d0e1f2a3b"
down_revision: str | Sequence[str] | None = "7b8c9d0e1f2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Adiciona o índice composto de paginação na tabela review_audit_logs."""
    op.create_index(
        "ix_review_audit_logs_pagination",
        "review_audit_logs",
        ["user_id", "review_date", "logged_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove o índice composto de paginação da tabela review_audit_logs."""
    op.drop_index("ix_review_audit_logs_pagination", table_name="review_audit_logs")
