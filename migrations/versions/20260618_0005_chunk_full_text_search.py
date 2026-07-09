"""add chunk full text search index

Revision ID: 20260618_0005
Revises: 20260618_0004
Create Date: 2026-06-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260618_0005"
down_revision: str | None = "20260618_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_content_fts "
        "ON knowledge_chunks USING gin (to_tsvector('simple', content))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_content_fts")
