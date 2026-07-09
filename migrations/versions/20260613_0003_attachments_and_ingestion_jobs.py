"""add attachments and ingestion jobs

Revision ID: 20260613_0003
Revises: 20260613_0002
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0003"
down_revision: str | None = "20260613_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_block_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("processing_status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "processing_status IN ('pending', 'processed', 'failed')",
            name=op.f("ck_attachments_processing_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_block_id"],
            ["knowledge_blocks.id"],
            name=op.f("fk_attachments_knowledge_block_id_knowledge_blocks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_attachments_storage_key")),
    )
    op.create_index(
        op.f("ix_attachments_knowledge_block_id"),
        "attachments",
        ["knowledge_block_id"],
        unique=False,
    )
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_block_id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name=op.f("ck_ingestion_jobs_job_status_values"),
        ),
        sa.CheckConstraint(
            "job_type IN ('organize')",
            name=op.f("ck_ingestion_jobs_job_type_values"),
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_block_id"],
            ["knowledge_blocks.id"],
            name=op.f("fk_ingestion_jobs_knowledge_block_id_knowledge_blocks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_jobs")),
        sa.UniqueConstraint(
            "idempotency_key",
            name=op.f("uq_ingestion_jobs_idempotency_key"),
        ),
    )
    op.create_index(
        op.f("ix_ingestion_jobs_knowledge_block_id"),
        "ingestion_jobs",
        ["knowledge_block_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ingestion_jobs_knowledge_block_id"),
        table_name="ingestion_jobs",
    )
    op.drop_table("ingestion_jobs")
    op.drop_index(
        op.f("ix_attachments_knowledge_block_id"),
        table_name="attachments",
    )
    op.drop_table("attachments")
