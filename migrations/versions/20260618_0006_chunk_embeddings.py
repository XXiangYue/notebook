"""add chunk embeddings

Revision ID: 20260618_0006
Revises: 20260618_0005
Create Date: 2026-06-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260618_0006"
down_revision: str | None = "20260618_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "chunk_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_block_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_version_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_chunk_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding_vector", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_block_id"],
            ["knowledge_blocks.id"],
            name=op.f("fk_chunk_embeddings_knowledge_block_id_knowledge_blocks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_chunk_id"],
            ["knowledge_chunks.id"],
            name=op.f("fk_chunk_embeddings_knowledge_chunk_id_knowledge_chunks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_version_id"],
            ["knowledge_versions.id"],
            name=op.f("fk_chunk_embeddings_knowledge_version_id_knowledge_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunk_embeddings")),
        sa.UniqueConstraint(
            "knowledge_chunk_id",
            "embedding_model",
            name="uq_chunk_embeddings_chunk_model",
        ),
    )
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
    op.create_index(
        "ix_chunk_embeddings_model",
        "chunk_embeddings",
        ["embedding_model"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chunk_embeddings_model", table_name="chunk_embeddings")
    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector")
    op.drop_table("chunk_embeddings")
