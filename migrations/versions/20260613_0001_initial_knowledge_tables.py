"""Create initial knowledge tables.

Revision ID: 20260613_0001
Revises:
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("name", name=op.f("uq_categories_name")),
    )
    op.create_table(
        "knowledge_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_type IN ('manual', 'import', 'derived')",
            name=op.f("ck_knowledge_blocks_source_type_values"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'organizing', 'pending_confirmation', 'indexing', "
            "'searchable', 'index_failed', 'archived', 'deleted')",
            name=op.f("ck_knowledge_blocks_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_knowledge_blocks_category_id_categories"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_blocks")),
    )
    op.create_index(
        "ix_knowledge_blocks_status_created_at",
        "knowledge_blocks",
        ["status", "created_at"],
        unique=False,
    )
    op.create_table(
        "knowledge_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_block_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("version_type", sa.String(length=32), nullable=False),
        sa.Column("topic_instruction", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("markdown_content", sa.Text(), nullable=True),
        sa.Column("structured_metadata", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=16), nullable=False),
        sa.Column("model_run_id", sa.Uuid(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "raw_text IS NOT NULL OR markdown_content IS NOT NULL",
            name=op.f("ck_knowledge_versions_content_present"),
        ),
        sa.CheckConstraint(
            "created_by IN ('user', 'system', 'model')",
            name=op.f("ck_knowledge_versions_created_by_values"),
        ),
        sa.CheckConstraint(
            "version_type IN ('original', 'ai_generated', 'user_confirmed', 'user_edited')",
            name=op.f("ck_knowledge_versions_version_type_values"),
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_block_id"],
            ["knowledge_blocks.id"],
            name=op.f("fk_knowledge_versions_knowledge_block_id_knowledge_blocks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_versions")),
        sa.UniqueConstraint(
            "knowledge_block_id",
            "version_number",
            name="uq_knowledge_versions_block_version",
        ),
    )
    op.create_foreign_key(
        "fk_knowledge_blocks_current_version_id_knowledge_versions",
        "knowledge_blocks",
        "knowledge_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_knowledge_blocks_current_version_id_knowledge_versions",
        "knowledge_blocks",
        type_="foreignkey",
    )
    op.drop_table("knowledge_versions")
    op.drop_index("ix_knowledge_blocks_status_created_at", table_name="knowledge_blocks")
    op.drop_table("knowledge_blocks")
    op.drop_table("categories")
