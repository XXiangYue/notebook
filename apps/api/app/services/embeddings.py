import hashlib
import math
import re
from typing import Any

import httpx
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.config import Settings, get_settings
from apps.api.app.models.knowledge import (
    ChunkEmbedding,
    KnowledgeBlock,
    KnowledgeChunk,
    KnowledgeStatus,
)

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")
DOCUMENT_EMBEDDING_TYPE = "db"
QUERY_EMBEDDING_TYPE = "query"


class EmbeddingProviderError(Exception):
    pass


async def embed_text(
    text: str,
    *,
    input_type: str,
    settings: Settings | None = None,
) -> list[float]:
    vectors = await embed_texts([text], input_type=input_type, settings=settings)
    return vectors[0]


async def embed_texts(
    texts: list[str],
    *,
    input_type: str,
    settings: Settings | None = None,
) -> list[list[float]]:
    settings = settings or get_settings()
    if not texts:
        return []
    if settings.embedding_provider == "local":
        return [
            local_hash_embedding(f"{input_type}:{text}", settings.embedding_dimensions)
            for text in texts
        ]
    if settings.embedding_provider == "minimax":
        return await embed_texts_minimax(texts, input_type=input_type, settings=settings)
    raise EmbeddingProviderError(f"Unsupported embedding provider: {settings.embedding_provider}")


async def embed_texts_minimax(
    texts: list[str],
    *,
    input_type: str,
    settings: Settings,
) -> list[list[float]]:
    api_key = settings.embedding_api_key or settings.minimax_api_key
    if not api_key:
        raise EmbeddingProviderError("EMBEDDING_API_KEY or MINIMAX_API_KEY is required")

    url = f"{settings.embedding_base_url.rstrip('/')}/embeddings"
    params = {}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if settings.embedding_group_id:
        params["GroupId"] = settings.embedding_group_id
        headers["GroupId"] = settings.embedding_group_id

    payload = {
        "model": settings.embedding_model,
        "type": input_type,
        "texts": texts,
    }
    async with httpx.AsyncClient(timeout=settings.embedding_timeout_seconds) as client:
        response = await client.post(url, params=params, headers=headers, json=payload)

    try:
        data = response.json()
    except ValueError as error:
        raise EmbeddingProviderError(
            f"Embedding provider returned non-JSON response: HTTP {response.status_code}"
        ) from error

    if response.status_code >= 400:
        message = _provider_error_message(data) or response.text
        raise EmbeddingProviderError(
            f"Embedding provider request failed: HTTP {response.status_code}: {message}"
        )

    provider_status = _provider_status(data)
    if provider_status not in (None, 0):
        message = _provider_error_message(data) or str(data)
        raise EmbeddingProviderError(f"Embedding provider returned error: {message}")

    vectors = _extract_vectors(data)
    if len(vectors) != len(texts):
        raise EmbeddingProviderError(
            f"Embedding provider returned {len(vectors)} vectors for {len(texts)} texts"
        )
    for vector in vectors:
        if len(vector) != settings.embedding_dimensions:
            raise EmbeddingProviderError(
                "Embedding dimension mismatch: "
                f"expected {settings.embedding_dimensions}, got {len(vector)}"
            )
    return vectors


def local_hash_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    tokens = _tokens(text)
    for token in tokens:
        _add_token(vector, token, 1.0)
    for left, right in zip(tokens, tokens[1:], strict=False):
        _add_token(vector, f"{left}{right}", 0.55)

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


async def ensure_active_chunk_embeddings(
    session: AsyncSession,
    settings: Settings | None = None,
) -> int:
    settings = settings or get_settings()
    statement = (
        select(KnowledgeChunk)
        .join(KnowledgeBlock, KnowledgeBlock.id == KnowledgeChunk.knowledge_block_id)
        .where(KnowledgeChunk.is_active.is_(True))
        .where(KnowledgeBlock.status == KnowledgeStatus.SEARCHABLE.value)
        .where(KnowledgeBlock.deleted_at.is_(None))
        .where(
            ~exists()
            .where(ChunkEmbedding.knowledge_chunk_id == KnowledgeChunk.id)
            .where(ChunkEmbedding.embedding_model == settings.embedding_model)
        )
    )
    chunks = list(await session.scalars(statement))
    if not chunks:
        return 0

    embeddings = await chunk_embeddings_from_chunks(chunks, settings=settings)
    session.add_all(embeddings)
    await session.flush()
    return len(chunks)


async def chunk_embeddings_from_chunks(
    chunks: list[KnowledgeChunk],
    *,
    settings: Settings | None = None,
) -> list[ChunkEmbedding]:
    settings = settings or get_settings()
    vectors = await embed_texts(
        [chunk.content for chunk in chunks],
        input_type=DOCUMENT_EMBEDDING_TYPE,
        settings=settings,
    )
    return [
        ChunkEmbedding(
            knowledge_block_id=chunk.knowledge_block_id,
            knowledge_version_id=chunk.knowledge_version_id,
            knowledge_chunk_id=chunk.id,
            embedding_model=settings.embedding_model,
            embedding_dimensions=settings.embedding_dimensions,
            embedding_vector=vector,
            content_hash=chunk.content_hash,
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=False)
    )


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def _extract_vectors(data: dict[str, Any]) -> list[list[float]]:
    if isinstance(data.get("vectors"), list):
        return [_normalize_vector(vector) for vector in data["vectors"]]
    if isinstance(data.get("embeddings"), list):
        return [_normalize_vector(vector) for vector in data["embeddings"]]
    if isinstance(data.get("data"), list):
        return [_normalize_vector(item["embedding"]) for item in data["data"]]
    nested_data = data.get("data")
    if isinstance(nested_data, dict):
        return _extract_vectors(nested_data)
    raise EmbeddingProviderError("Embedding provider response does not contain vectors")


def _normalize_vector(vector: Any) -> list[float]:
    if not isinstance(vector, list):
        raise EmbeddingProviderError("Embedding vector is not a list")
    return [float(value) for value in vector]


def _provider_status(data: dict[str, Any]) -> int | None:
    base_resp = data.get("base_resp")
    if isinstance(base_resp, dict) and "status_code" in base_resp:
        return int(base_resp["status_code"])
    if "status_code" in data:
        return int(data["status_code"])
    return None


def _provider_error_message(data: dict[str, Any]) -> str | None:
    base_resp = data.get("base_resp")
    if isinstance(base_resp, dict):
        return base_resp.get("status_msg") or base_resp.get("message")
    return data.get("error_msg") or data.get("message") or data.get("error")


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def _add_token(vector: list[float], token: str, weight: float) -> None:
    digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
    index = int.from_bytes(digest[:4], "big") % len(vector)
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    vector[index] += sign * weight
