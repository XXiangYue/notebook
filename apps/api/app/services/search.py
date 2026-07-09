import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Float, case, cast, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.config import get_settings
from apps.api.app.models.knowledge import (
    ChunkEmbedding,
    KnowledgeBlock,
    KnowledgeChunk,
    KnowledgeStatus,
)
from apps.api.app.schemas.search import SearchHit, SearchRequest
from apps.api.app.services.embeddings import (
    QUERY_EMBEDDING_TYPE,
    cosine_similarity,
    embed_text,
    ensure_active_chunk_embeddings,
    vector_literal,
)

SNIPPET_LENGTH = 180
RRF_K = 60


@dataclass(frozen=True)
class SearchRow:
    knowledge_block_id: UUID
    knowledge_chunk_id: UUID
    title: str
    summary: str | None
    category_id: UUID | None
    heading_path: list[str]
    content: str
    score: float


@dataclass(frozen=True)
class RankedRow:
    row: SearchRow
    rank: int


async def search_chunks(
    session: AsyncSession,
    payload: SearchRequest,
) -> tuple[list[SearchHit], int]:
    inserted = await ensure_active_chunk_embeddings(session)
    if inserted:
        await session.commit()

    dialect_name = session.get_bind().dialect.name
    candidate_limit = max(payload.limit * 3, 30)
    if dialect_name == "postgresql":
        keyword_rows = await _keyword_search_postgres(session, payload, candidate_limit)
        vector_rows = await _vector_search_postgres(session, payload, candidate_limit)
    else:
        keyword_rows = await _keyword_search_fallback(session, payload, candidate_limit)
        vector_rows = await _vector_search_fallback(session, payload, candidate_limit)

    rows = _rrf_fuse(keyword_rows, vector_rows)[: payload.limit]
    hits = [
        SearchHit(
            knowledge_block_id=row.knowledge_block_id,
            knowledge_chunk_id=row.knowledge_chunk_id,
            title=row.title,
            summary=row.summary,
            category_id=row.category_id,
            heading_path=row.heading_path,
            snippet=make_snippet(row.content, payload.query),
            score=round(row.score, 6),
        )
        for row in rows
    ]
    return hits, len(hits)


async def _keyword_search_postgres(
    session: AsyncSession,
    payload: SearchRequest,
    limit: int,
) -> list[RankedRow]:
    pattern = f"%{payload.query}%"
    title_match = KnowledgeBlock.title.ilike(pattern)
    content_match = KnowledgeChunk.content.ilike(pattern)
    vector = func.to_tsvector("simple", KnowledgeChunk.content)
    ts_query = func.websearch_to_tsquery("simple", payload.query)
    ts_match = vector.op("@@")(ts_query)
    rank = func.ts_rank_cd(vector, ts_query)
    score = (
        cast(rank, Float)
        + case((title_match, 2.0), else_=0.0)
        + case((content_match, 1.0), else_=0.0)
    )

    statement = (
        _base_select(score)
        .where(or_(ts_match, title_match, content_match))
        .order_by(score.desc(), KnowledgeBlock.updated_at.desc(), KnowledgeChunk.chunk_index)
        .limit(limit)
    )
    if payload.category_id is not None:
        statement = statement.where(KnowledgeBlock.category_id == payload.category_id)

    result = await session.execute(statement)
    return [
        RankedRow(row=_row_to_search_row(row), rank=index)
        for index, row in enumerate(result.all(), start=1)
    ]


async def _vector_search_postgres(
    session: AsyncSession,
    payload: SearchRequest,
    limit: int,
) -> list[RankedRow]:
    settings = get_settings()
    query_vector = vector_literal(
        await embed_text(payload.query, input_type=QUERY_EMBEDDING_TYPE, settings=settings)
    )
    category_filter = ""
    params: dict[str, object] = {
        "query_vector": query_vector,
        "embedding_model": settings.embedding_model,
        "limit": limit,
    }
    if payload.category_id is not None:
        category_filter = "AND kb.category_id = :category_id"
        params["category_id"] = payload.category_id

    statement = text(
        f"""
        SELECT
            kb.id AS knowledge_block_id,
            kc.id AS knowledge_chunk_id,
            kb.title AS title,
            kb.summary AS summary,
            kb.category_id AS category_id,
            kc.heading_path AS heading_path,
            kc.content AS content,
            1 - (ce.embedding_vector <=> (:query_vector)::vector) AS score
        FROM chunk_embeddings ce
        JOIN knowledge_chunks kc ON kc.id = ce.knowledge_chunk_id
        JOIN knowledge_blocks kb ON kb.id = kc.knowledge_block_id
        WHERE ce.embedding_model = :embedding_model
          AND kc.is_active = true
          AND kb.status = 'searchable'
          AND kb.deleted_at IS NULL
          {category_filter}
        ORDER BY ce.embedding_vector <=> (:query_vector)::vector,
                 kb.updated_at DESC,
                 kc.chunk_index ASC
        LIMIT :limit
        """
    )
    result = await session.execute(statement, params)
    return [
        RankedRow(row=_row_to_search_row(row), rank=index)
        for index, row in enumerate(result.mappings().all(), start=1)
    ]


async def _keyword_search_fallback(
    session: AsyncSession,
    payload: SearchRequest,
    limit: int,
) -> list[RankedRow]:
    terms = _query_terms(payload.query)
    filters = []
    score = literal(0.0)
    for term in terms:
        pattern = f"%{term.lower()}%"
        title_match = func.lower(KnowledgeBlock.title).like(pattern)
        content_match = func.lower(KnowledgeChunk.content).like(pattern)
        filters.append(or_(title_match, content_match))
        score = score + case((title_match, 2.0), else_=0.0) + case(
            (content_match, 1.0), else_=0.0
        )

    statement = (
        _base_select(score)
        .where(or_(*filters))
        .order_by(score.desc(), KnowledgeBlock.updated_at.desc(), KnowledgeChunk.chunk_index)
        .limit(limit)
    )
    if payload.category_id is not None:
        statement = statement.where(KnowledgeBlock.category_id == payload.category_id)

    result = await session.execute(statement)
    return [
        RankedRow(row=_row_to_search_row(row), rank=index)
        for index, row in enumerate(result.all(), start=1)
    ]


async def _vector_search_fallback(
    session: AsyncSession,
    payload: SearchRequest,
    limit: int,
) -> list[RankedRow]:
    settings = get_settings()
    query_vector = await embed_text(
        payload.query,
        input_type=QUERY_EMBEDDING_TYPE,
        settings=settings,
    )
    statement = (
        select(
            KnowledgeBlock.id.label("knowledge_block_id"),
            KnowledgeChunk.id.label("knowledge_chunk_id"),
            KnowledgeBlock.title,
            KnowledgeBlock.summary,
            KnowledgeBlock.category_id,
            KnowledgeChunk.heading_path,
            KnowledgeChunk.content,
            literal(0.0).label("score"),
            ChunkEmbedding.embedding_vector.label("embedding_vector"),
        )
        .join(KnowledgeBlock, KnowledgeBlock.id == KnowledgeChunk.knowledge_block_id)
        .join(ChunkEmbedding, ChunkEmbedding.knowledge_chunk_id == KnowledgeChunk.id)
        .where(
            KnowledgeChunk.is_active.is_(True),
            KnowledgeBlock.status == KnowledgeStatus.SEARCHABLE.value,
            KnowledgeBlock.deleted_at.is_(None),
            ChunkEmbedding.embedding_model == settings.embedding_model,
        )
    )
    if payload.category_id is not None:
        statement = statement.where(KnowledgeBlock.category_id == payload.category_id)

    result = await session.execute(statement)
    scored = []
    for row in result.all():
        search_row = _row_to_search_row(
            row,
            score=cosine_similarity(row.embedding_vector, query_vector),
        )
        scored.append(search_row)

    scored.sort(key=lambda row: row.score, reverse=True)
    return [
        RankedRow(row=row, rank=index)
        for index, row in enumerate(scored[:limit], start=1)
    ]


def _base_select(score):
    return (
        select(
            KnowledgeBlock.id.label("knowledge_block_id"),
            KnowledgeChunk.id.label("knowledge_chunk_id"),
            KnowledgeBlock.title,
            KnowledgeBlock.summary,
            KnowledgeBlock.category_id,
            KnowledgeChunk.heading_path,
            KnowledgeChunk.content,
            score.label("score"),
        )
        .join(KnowledgeBlock, KnowledgeBlock.id == KnowledgeChunk.knowledge_block_id)
        .where(
            KnowledgeChunk.is_active.is_(True),
            KnowledgeBlock.status == KnowledgeStatus.SEARCHABLE.value,
            KnowledgeBlock.deleted_at.is_(None),
        )
    )


def _rrf_fuse(keyword_rows: list[RankedRow], vector_rows: list[RankedRow]) -> list[SearchRow]:
    by_chunk_id: dict[UUID, SearchRow] = {}
    scores: dict[UUID, float] = {}
    for ranked in [*keyword_rows, *vector_rows]:
        chunk_id = ranked.row.knowledge_chunk_id
        by_chunk_id[chunk_id] = ranked.row
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + ranked.rank)

    fused = [
        SearchRow(
            knowledge_block_id=row.knowledge_block_id,
            knowledge_chunk_id=row.knowledge_chunk_id,
            title=row.title,
            summary=row.summary,
            category_id=row.category_id,
            heading_path=row.heading_path,
            content=row.content,
            score=scores[row.knowledge_chunk_id],
        )
        for row in by_chunk_id.values()
    ]
    return sorted(fused, key=lambda row: row.score, reverse=True)


def _row_to_search_row(row, score: float | None = None) -> SearchRow:
    row_score = score if score is not None else row.score
    return SearchRow(
        knowledge_block_id=row.knowledge_block_id,
        knowledge_chunk_id=row.knowledge_chunk_id,
        title=row.title,
        summary=row.summary,
        category_id=row.category_id,
        heading_path=list(row.heading_path or []),
        content=row.content,
        score=float(row_score or 0.0),
    )


def make_snippet(content: str, query: str, max_length: int = SNIPPET_LENGTH) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= max_length:
        return normalized

    lowered_content = normalized.lower()
    match_positions = [
        lowered_content.find(term.lower())
        for term in _query_terms(query)
        if lowered_content.find(term.lower()) >= 0
    ]
    first_match = min(match_positions) if match_positions else 0
    half = max_length // 2
    start = max(0, first_match - half)
    end = min(len(normalized), start + max_length)
    if end - start < max_length:
        start = max(0, end - max_length)

    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(normalized) else ""
    return f"{prefix}{normalized[start:end]}{suffix}"


def _query_terms(query: str) -> list[str]:
    terms = [term for term in re.split(r"\s+", query.strip()) if term]
    return terms or [query.strip()]
