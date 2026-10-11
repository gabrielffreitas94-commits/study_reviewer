"""covering_indexes_include

Revision ID: 2c3e4f5a6b7c
Revises: 1b9d1d8e2245
Create Date: 2026-10-03 05:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2c3e4f5a6b7c"
down_revision: str | Sequence[str] | None = "1b9d1d8e2245"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria índices covering com cláusula INCLUDE para garantir buscas Index Scan Only."""
    op.create_index(
        "ix_topics_subject_id_include_id_name",
        "topics",
        ["subject_id"],
        unique=False,
        postgresql_include=["id", "name"],
    )
    op.create_index(
        "ix_subjects_id_include_name",
        "subjects",
        ["id"],
        unique=False,
        postgresql_include=["name"],
    )


def downgrade() -> None:
    """Remove os índices covering."""
    op.drop_index("ix_subjects_id_include_name", table_name="subjects")
    op.drop_index("ix_topics_subject_id_include_id_name", table_name="topics")
