from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=50)
    category_id: UUID | None = None

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized


class SearchHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    knowledge_block_id: UUID
    knowledge_chunk_id: UUID
    title: str
    summary: str | None
    category_id: UUID | None
    heading_path: list[str]
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    total: int
    limit: int
    items: list[SearchHit]
