import hashlib

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.api.app.models.knowledge import (
    Category,
    ChunkEmbedding,
    CreatedBy,
    KnowledgeBlock,
    KnowledgeChunk,
    KnowledgeStatus,
    KnowledgeVersion,
    SourceType,
    VersionType,
)
from apps.api.app.services.embeddings import chunk_embeddings_from_chunks


async def create_searchable_block(
    session: AsyncSession,
    *,
    title: str,
    markdown: str,
    summary: str | None = None,
    category: Category | None = None,
    status: str = KnowledgeStatus.SEARCHABLE.value,
    deleted: bool = False,
    active: bool = True,
) -> KnowledgeBlock:
    block = KnowledgeBlock(
        title=title,
        summary=summary,
        category=category,
        status=status,
        source_type=SourceType.MANUAL.value,
    )
    version = KnowledgeVersion(
        knowledge_block=block,
        version_number=1,
        version_type=VersionType.USER_CONFIRMED.value,
        markdown_content=markdown,
        structured_metadata={},
        created_by=CreatedBy.USER.value,
        content_hash=hashlib.sha256(markdown.encode()).hexdigest(),
    )
    chunks = [
        KnowledgeChunk(
            knowledge_block=block,
            knowledge_version=version,
            chunk_index=0,
            heading_path=[title],
            content=markdown,
            token_count=len(markdown),
            char_start=0,
            char_end=len(markdown),
            content_hash=hashlib.sha256(markdown.encode()).hexdigest(),
            is_active=active,
        )
    ]
    block.current_version = version
    if deleted:
        block.deleted_at = version.created_at
    session.add_all([block, version, *chunks])
    await session.flush()
    if active and status == KnowledgeStatus.SEARCHABLE.value and not deleted:
        session.add_all(await chunk_embeddings_from_chunks(chunks))
    await session.commit()
    await session.refresh(block)
    return block


async def create_block_with_chunks(
    session: AsyncSession,
    *,
    title: str,
    chunks: list[str],
) -> KnowledgeBlock:
    block = KnowledgeBlock(
        title=title,
        status=KnowledgeStatus.SEARCHABLE.value,
        source_type=SourceType.MANUAL.value,
    )
    version = KnowledgeVersion(
        knowledge_block=block,
        version_number=1,
        version_type=VersionType.USER_CONFIRMED.value,
        markdown_content="\n\n".join(chunks),
        structured_metadata={},
        created_by=CreatedBy.USER.value,
        content_hash=hashlib.sha256("\n\n".join(chunks).encode()).hexdigest(),
    )
    chunk_models = [
        KnowledgeChunk(
            knowledge_block=block,
            knowledge_version=version,
            chunk_index=index,
            heading_path=[title, f"片段 {index + 1}"],
            content=content,
            token_count=len(content),
            char_start=0,
            char_end=len(content),
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            is_active=True,
        )
        for index, content in enumerate(chunks)
    ]
    block.current_version = version
    session.add_all([block, version, *chunk_models])
    await session.flush()
    session.add_all(await chunk_embeddings_from_chunks(chunk_models))
    await session.commit()
    await session.refresh(block)
    return block


async def create_block_without_embedding(
    session: AsyncSession,
    *,
    title: str,
    markdown: str,
) -> KnowledgeBlock:
    block = KnowledgeBlock(
        title=title,
        status=KnowledgeStatus.SEARCHABLE.value,
        source_type=SourceType.MANUAL.value,
    )
    version = KnowledgeVersion(
        knowledge_block=block,
        version_number=1,
        version_type=VersionType.USER_CONFIRMED.value,
        markdown_content=markdown,
        structured_metadata={},
        created_by=CreatedBy.USER.value,
        content_hash=hashlib.sha256(markdown.encode()).hexdigest(),
    )
    chunk = KnowledgeChunk(
        knowledge_block=block,
        knowledge_version=version,
        chunk_index=0,
        heading_path=[title],
        content=markdown,
        token_count=len(markdown),
        char_start=0,
        char_end=len(markdown),
        content_hash=hashlib.sha256(markdown.encode()).hexdigest(),
        is_active=True,
    )
    block.current_version = version
    session.add_all([block, version, chunk])
    await session.commit()
    await session.refresh(block)
    return block


async def test_search_returns_active_chunks_from_searchable_blocks(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        block = await create_searchable_block(
            session,
            title="RAG 检索笔记",
            summary="混合检索摘要",
            markdown="# RAG 检索笔记\n\n向量索引适合语义召回，全文检索适合关键词召回。",
        )

    response = await api_client.post("/search", json={"query": "向量索引"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "向量索引"
    assert payload["total"] == 1
    assert payload["items"][0]["knowledge_block_id"] == str(block.id)
    assert payload["items"][0]["title"] == "RAG 检索笔记"
    assert payload["items"][0]["heading_path"] == ["RAG 检索笔记"]
    assert "向量索引" in payload["items"][0]["snippet"]


async def test_search_excludes_inactive_chunks_and_non_searchable_blocks(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        visible = await create_searchable_block(
            session,
            title="可搜索知识",
            markdown="# 可搜索知识\n\n目标词只应该命中这一条。",
        )
        await create_searchable_block(
            session,
            title="旧分块",
            markdown="# 旧分块\n\n目标词在旧版本里。",
            active=False,
        )
        await create_searchable_block(
            session,
            title="草稿分块",
            markdown="# 草稿分块\n\n目标词在草稿里。",
            status=KnowledgeStatus.DRAFT.value,
        )

    response = await api_client.post("/search", json={"query": "目标词"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["knowledge_block_id"] == str(visible.id)


async def test_search_can_filter_by_category(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        finance = Category(name="金融", sort_order=1)
        work = Category(name="工作", sort_order=2)
        session.add_all([finance, work])
        await session.flush()
        finance_block = await create_searchable_block(
            session,
            title="金融笔记",
            markdown="# 金融笔记\n\n现金流分析方法。",
            category=finance,
        )
        await create_searchable_block(
            session,
            title="工作笔记",
            markdown="# 工作笔记\n\n现金流排期方法。",
            category=work,
        )

    response = await api_client.post(
        "/search",
        json={"query": "现金流", "category_id": str(finance.id)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["knowledge_block_id"] == str(finance_block.id)


async def test_search_uses_vector_recall_when_keyword_does_not_match_phrase(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        semantic_block = await create_block_with_chunks(
            session,
            title="语义检索资料",
            chunks=[
                "# 语义检索资料\n\n向量索引可以按照语义相似度找到资料。",
                "# 烹饪笔记\n\n番茄炒蛋需要控制火候。",
            ],
        )

    response = await api_client.post("/search", json={"query": "语义召回", "limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["knowledge_block_id"] == str(semantic_block.id)
    assert "语义相似度" in payload["items"][0]["snippet"]


async def test_search_backfills_missing_embeddings(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        block = await create_block_without_embedding(
            session,
            title="历史分块",
            markdown="# 历史分块\n\n历史数据在升级前没有 embedding。",
        )
        before = await session.scalar(
            select_count_embeddings_for_block(block.id)
        )
        assert before == 0

    response = await api_client.post("/search", json={"query": "历史数据", "limit": 1})

    assert response.status_code == 200
    async with session_factory() as session:
        after = await session.scalar(select_count_embeddings_for_block(block.id))
    assert after == 1


def select_count_embeddings_for_block(block_id):
    from sqlalchemy import func, select

    return (
        select(func.count())
        .select_from(ChunkEmbedding)
        .where(ChunkEmbedding.knowledge_block_id == block_id)
    )
