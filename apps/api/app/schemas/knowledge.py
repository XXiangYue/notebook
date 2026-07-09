from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeDraftCreate(BaseModel):
    topic: str | None = Field(default=None, max_length=500)
    raw_text: str = Field(min_length=1, max_length=2_000_000)
    title: str | None = Field(default=None, max_length=300)
    language: str | None = Field(default=None, max_length=16)
    category_id: UUID | None = None

    @field_validator("raw_text")
    @classmethod
    def raw_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("raw_text must not be blank")
        return value

    @field_validator("topic", "title", "language")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class KnowledgeDraftUpdate(KnowledgeDraftCreate):
    pass


class KnowledgeBlockUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    topic: str | None = Field(default=None, max_length=500)
    raw_text: str | None = Field(default=None, max_length=2_000_000)
    markdown_content: str | None = Field(default=None, max_length=2_000_000)
    summary: str | None = Field(default=None, max_length=2000)
    language: str | None = Field(default=None, max_length=16)
    category_id: UUID | None = None

    @field_validator("raw_text", "markdown_content")
    @classmethod
    def content_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("content must not be blank")
        return normalized

    @field_validator("title", "topic", "summary", "language")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class KnowledgeConfirm(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    summary: str | None = Field(default=None, max_length=2000)
    markdown_content: str = Field(min_length=1, max_length=2_000_000)
    category_id: UUID | None = None

    @field_validator("title", "summary", "markdown_content")
    @classmethod
    def normalize_confirm_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("field must not be blank")
        return normalized


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    color: str | None = Field(default=None, max_length=20)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized

    @field_validator("description", "color")
    @classmethod
    def normalize_category_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    color: str | None = Field(default=None, max_length=20)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized

    @field_validator("description", "color")
    @classmethod
    def normalize_category_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    color: str | None
    is_system: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class KnowledgeVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_number: int
    version_type: str
    topic_instruction: str | None
    raw_text: str | None
    markdown_content: str | None
    structured_metadata: dict
    created_by: str
    content_hash: str
    created_at: datetime


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    width: int | None
    height: int | None
    extracted_text: str | None
    processing_status: str
    created_at: datetime


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    knowledge_block_id: UUID
    job_type: str
    status: str
    attempt_count: int
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class KnowledgeChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    knowledge_version_id: UUID
    chunk_index: int
    heading_path: list[str]
    content: str
    token_count: int
    char_start: int | None
    char_end: int | None
    content_hash: str
    is_active: bool
    created_at: datetime


class KnowledgeBlockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str | None
    status: str
    source_type: str
    language: str | None
    category_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class KnowledgeBlockDetail(KnowledgeBlockSummary):
    current_version_id: UUID | None
    source_uri: str | None
    confirmed_at: datetime | None
    archived_at: datetime | None
    deleted_at: datetime | None
    versions: list[KnowledgeVersionResponse]
    attachments: list[AttachmentResponse]
    ingestion_jobs: list[IngestionJobResponse]
    chunks: list[KnowledgeChunkResponse]


class KnowledgeBlockList(BaseModel):
    items: list[KnowledgeBlockSummary]
    total: int
    limit: int
    offset: int
