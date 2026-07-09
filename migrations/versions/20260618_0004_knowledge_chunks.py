"""add knowledge chunks

Revision ID: 20260618_0004
Revises: 20260613_0003
Create Date: 2026-06-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260618_0004"
down_revision: str | None = "20260613_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_block_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_version_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.JSON(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_block_id"],
            ["knowledge_blocks.id"],
            name=op.f("fk_knowledge_chunks_knowledge_block_id_knowledge_blocks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_version_id"],
            ["knowledge_versions.id"],
            name=op.f("fk_knowledge_chunks_knowledge_version_id_knowledge_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_chunks")),
        sa.UniqueConstraint(
            "knowledge_version_id",
            "chunk_index",
            name="uq_knowledge_chunks_version_index",
        ),
    )
    op.create_index(
        "ix_knowledge_chunks_block_active",
        "knowledge_chunks",
        ["knowledge_block_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_block_active", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
