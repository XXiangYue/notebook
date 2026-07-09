"""set embedding vectors to 1536 dimensions

Revision ID: 20260623_0007
Revises: 20260618_0006
Create Date: 2026-06-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260623_0007"
down_revision: str | None = "20260618_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Embeddings are derived data. Clear old 384-dimensional local vectors so the
    # search path can rebuild active chunk embeddings with the configured provider.
    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector")
    op.execute("DELETE FROM chunk_embeddings")
    op.execute(
        "ALTER TABLE chunk_embeddings "
        "ALTER COLUMN embedding_vector TYPE vector(1536) "
        "USING embedding_vector::vector(1536)"
    )
    op.execute(
        "CREATE INDEX ix_chunk_embeddings_vector "
        "ON chunk_embeddings USING ivfflat (embedding_vector vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector")
    op.execute("DELETE FROM chunk_embeddings")
    op.execute(
        "ALTER TABLE chunk_embeddings "
        "ALTER COLUMN embedding_vector TYPE vector(384) "
        "USING embedding_vector::vector(384)"
    )
    op.execute(
        "CREATE INDEX ix_chunk_embeddings_vector "
        "ON chunk_embeddings USING ivfflat (embedding_vector vector_cosine_ops) "
        "WITH (lists = 100)"
    )
