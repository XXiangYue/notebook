import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.models.base import Base, TimestampMixin
from apps.api.app.models.types import VectorString


class KnowledgeStatus(enum.StrEnum):
    DRAFT = "draft"
    ORGANIZING = "organizing"
    PENDING_CONFIRMATION = "pending_confirmation"
    INDEXING = "indexing"
    SEARCHABLE = "searchable"
    INDEX_FAILED = "index_failed"
    ARCHIVED = "archived"
    DELETED = "deleted"


class SourceType(enum.StrEnum):
    MANUAL = "manual"
    IMPORT = "import"
    DERIVED = "derived"


class VersionType(enum.StrEnum):
    ORIGINAL = "original"
    AI_GENERATED = "ai_generated"
    USER_CONFIRMED = "user_confirmed"
    USER_EDITED = "user_edited"


class CreatedBy(enum.StrEnum):
    USER = "user"
    SYSTEM = "system"
    MODEL = "model"


class AttachmentStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobType(enum.StrEnum):
    ORGANIZE = "organize"


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(20))
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)

    knowledge_blocks: Mapped[list["KnowledgeBlock"]] = relationship(back_populates="category")


class KnowledgeBlock(TimestampMixin, Base):
    __tablename__ = "knowledge_blocks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'organizing', 'pending_confirmation', 'indexing', "
            "'searchable', 'index_failed', 'archived', 'deleted')",
            name="status_values",
        ),
        CheckConstraint(
            "source_type IN ('manual', 'import', 'derived')",
            name="source_type_values",
        ),
        Index("ix_knowledge_blocks_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=KnowledgeStatus.DRAFT.value,
        nullable=False,
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "knowledge_versions.id",
            name="fk_knowledge_blocks_current_version_id_knowledge_versions",
            use_alter=True,
            ondelete="SET NULL",
        )
    )
    source_type: Mapped[str] = mapped_column(
        String(16),
        default=SourceType.MANUAL.value,
        nullable=False,
    )
    source_uri: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(16))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[Category | None] = relationship(back_populates="knowledge_blocks")
    versions: Mapped[list["KnowledgeVersion"]] = relationship(
        back_populates="knowledge_block",
        foreign_keys="KnowledgeVersion.knowledge_block_id",
        cascade="all, delete-orphan",
        order_by="KnowledgeVersion.version_number",
    )
    current_version: Mapped["KnowledgeVersion | None"] = relationship(
        foreign_keys=[current_version_id],
        post_update=True,
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="knowledge_block",
        cascade="all, delete-orphan",
        order_by="Attachment.created_at",
    )
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(
        back_populates="knowledge_block",
        cascade="all, delete-orphan",
        order_by="IngestionJob.created_at",
    )
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="knowledge_block",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_index",
    )
    chunk_embeddings: Mapped[list["ChunkEmbedding"]] = relationship(
        back_populates="knowledge_block",
        cascade="all, delete-orphan",
    )


class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_block_id",
            "version_number",
            name="uq_knowledge_versions_block_version",
        ),
        CheckConstraint(
            "version_type IN ('original', 'ai_generated', 'user_confirmed', 'user_edited')",
            name="version_type_values",
        ),
        CheckConstraint(
            "created_by IN ('user', 'system', 'model')",
            name="created_by_values",
        ),
        CheckConstraint(
            "raw_text IS NOT NULL OR markdown_content IS NOT NULL",
            name="content_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    knowledge_block_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_type: Mapped[str] = mapped_column(String(32), nullable=False)
    topic_instruction: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    markdown_content: Mapped[str | None] = mapped_column(Text)
    structured_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(16), nullable=False)
    model_run_id: Mapped[uuid.UUID | None] = mapped_column()
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    knowledge_block: Mapped[KnowledgeBlock] = relationship(
        back_populates="versions",
        foreign_keys=[knowledge_block_id],
    )
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="knowledge_version",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_index",
    )
    chunk_embeddings: Mapped[list["ChunkEmbedding"]] = relationship(
        back_populates="knowledge_version",
        cascade="all, delete-orphan",
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_version_id",
            "chunk_index",
            name="uq_knowledge_chunks_version_index",
        ),
        Index("ix_knowledge_chunks_block_active", "knowledge_block_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    knowledge_block_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    knowledge_block: Mapped[KnowledgeBlock] = relationship(back_populates="chunks")
    knowledge_version: Mapped[KnowledgeVersion] = relationship(back_populates="chunks")
    embeddings: Mapped[list["ChunkEmbedding"]] = relationship(
        back_populates="knowledge_chunk",
        cascade="all, delete-orphan",
    )


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_chunk_id",
            "embedding_model",
            name="uq_chunk_embeddings_chunk_model",
        ),
        Index("ix_chunk_embeddings_model", "embedding_model"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    knowledge_block_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_blocks.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_vector: Mapped[list[float]] = mapped_column(VectorString(1536), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    knowledge_block: Mapped[KnowledgeBlock] = relationship(back_populates="chunk_embeddings")
    knowledge_version: Mapped[KnowledgeVersion] = relationship(back_populates="chunk_embeddings")
    knowledge_chunk: Mapped[KnowledgeChunk] = relationship(back_populates="embeddings")


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('pending', 'processed', 'failed')",
            name="processing_status_values",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    knowledge_block_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(
        String(16),
        default=AttachmentStatus.PENDING.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    knowledge_block: Mapped[KnowledgeBlock] = relationship(back_populates="attachments")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint("job_type IN ('organize')", name="job_type_values"),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="job_status_values",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    knowledge_block_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    knowledge_block: Mapped[KnowledgeBlock] = relationship(back_populates="ingestion_jobs")
