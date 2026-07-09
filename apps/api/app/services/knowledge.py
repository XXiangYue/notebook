import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.app.models.knowledge import (
    Category,
    CreatedBy,
    KnowledgeBlock,
    KnowledgeChunk,
    KnowledgeStatus,
    KnowledgeVersion,
    SourceType,
    VersionType,
)
from apps.api.app.schemas.knowledge import (
    CategoryCreate,
    CategoryUpdate,
    KnowledgeBlockUpdate,
    KnowledgeConfirm,
    KnowledgeDraftCreate,
    KnowledgeDraftUpdate,
)
from apps.api.app.services.chunking import chunk_markdown
from apps.api.app.services.embeddings import chunk_embeddings_from_chunks

UNTITLED_DRAFT = "未命名知识"


class KnowledgeBlockNotFoundError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class CategoryNameConflictError(Exception):
    pass


class SystemCategoryProtectedError(Exception):
    pass


class KnowledgeBlockNotEditableError(Exception):
    pass


class KnowledgeBlockNotConfirmableError(Exception):
    pass


def draft_title(payload: KnowledgeDraftCreate) -> str:
    return payload.title or payload.topic or UNTITLED_DRAFT


async def create_draft(
    session: AsyncSession,
    payload: KnowledgeDraftCreate,
) -> KnowledgeBlock:
    await ensure_category_exists(session, payload.category_id)
    block = KnowledgeBlock(
        title=draft_title(payload),
        status=KnowledgeStatus.DRAFT.value,
        source_type=SourceType.MANUAL.value,
        language=payload.language,
        category_id=payload.category_id,
    )
    version = KnowledgeVersion(
        knowledge_block=block,
        version_number=1,
        version_type=VersionType.ORIGINAL.value,
        topic_instruction=payload.topic,
        raw_text=payload.raw_text,
        structured_metadata={},
        created_by=CreatedBy.USER.value,
        content_hash=hashlib.sha256(payload.raw_text.encode()).hexdigest(),
    )
    session.add_all([block, version])

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return await get_block(session, block.id)


async def update_draft(
    session: AsyncSession,
    block_id: UUID,
    payload: KnowledgeDraftUpdate,
) -> KnowledgeBlock:
    block = await get_block(session, block_id)
    if block.status != KnowledgeStatus.DRAFT.value:
        raise KnowledgeBlockNotEditableError

    await ensure_category_exists(session, payload.category_id)
    next_version_number = max(version.version_number for version in block.versions) + 1
    version = KnowledgeVersion(
        knowledge_block=block,
        version_number=next_version_number,
        version_type=VersionType.USER_EDITED.value,
        topic_instruction=payload.topic,
        raw_text=payload.raw_text,
        structured_metadata={},
        created_by=CreatedBy.USER.value,
        content_hash=hashlib.sha256(payload.raw_text.encode()).hexdigest(),
    )
    block.title = draft_title(payload)
    block.language = payload.language
    block.category_id = payload.category_id
    block.current_version = version
    session.add(version)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return await get_block(session, block.id)


async def update_block(
    session: AsyncSession,
    block_id: UUID,
    payload: KnowledgeBlockUpdate,
) -> KnowledgeBlock:
    block = await get_block(session, block_id)
    if block.status == KnowledgeStatus.ORGANIZING.value:
        raise KnowledgeBlockNotEditableError

    await ensure_category_exists(session, payload.category_id)
    fields_set = payload.model_fields_set
    if "title" in fields_set and payload.title:
        block.title = payload.title
    if "summary" in fields_set:
        block.summary = payload.summary
    if "language" in fields_set:
        block.language = payload.language
    if "category_id" in fields_set:
        block.category_id = payload.category_id

    content = payload.markdown_content or payload.raw_text
    if content is None:
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        return await get_block(session, block.id)

    current = block.current_version or block.versions[-1]
    is_markdown = payload.markdown_content is not None
    next_version_number = max(version.version_number for version in block.versions) + 1
    version = KnowledgeVersion(
        knowledge_block=block,
        version_number=next_version_number,
        version_type=VersionType.USER_EDITED.value,
        topic_instruction=payload.topic
        if "topic" in fields_set
        else current.topic_instruction,
        raw_text=None if is_markdown else content,
        markdown_content=content if is_markdown else None,
        structured_metadata={
            "source_version_id": str(current.id),
            "source_version_type": current.version_type,
        },
        created_by=CreatedBy.USER.value,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    block.current_version = version
    session.add(version)

    if is_markdown:
        for chunk in block.chunks:
            chunk.is_active = False
        chunks = [
            KnowledgeChunk(
                knowledge_block=block,
                knowledge_version=version,
                chunk_index=chunk.chunk_index,
                heading_path=chunk.heading_path,
                content=chunk.content,
                token_count=chunk.token_count,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                content_hash=chunk.content_hash,
                is_active=True,
            )
            for chunk in chunk_markdown(content)
        ]
        session.add_all(chunks)
        await session.flush()
        session.add_all(await chunk_embeddings_from_chunks(chunks))

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return await get_block(session, block.id)


async def soft_delete_block(session: AsyncSession, block_id: UUID) -> None:
    block = await get_block(session, block_id)
    block.status = KnowledgeStatus.DELETED.value
    block.deleted_at = datetime.now(UTC)
    await session.commit()


async def restore_block(session: AsyncSession, block_id: UUID) -> None:
    block = await get_deleted_block(session, block_id)
    block.deleted_at = None
    if block.confirmed_at is not None:
        block.status = KnowledgeStatus.SEARCHABLE.value
    else:
        block.status = KnowledgeStatus.DRAFT.value
    await session.commit()


async def purge_block(session: AsyncSession, block_id: UUID) -> None:
    block = await get_deleted_block(session, block_id)
    await session.delete(block)
    await session.commit()


async def confirm_ai_result(
    session: AsyncSession,
    block_id: UUID,
    payload: KnowledgeConfirm,
) -> KnowledgeBlock:
    block = await get_block(session, block_id)
    if block.status != KnowledgeStatus.PENDING_CONFIRMATION.value:
        raise KnowledgeBlockNotConfirmableError

    await ensure_category_exists(session, payload.category_id)
    generated = next(
        (
            version
            for version in reversed(block.versions)
            if version.version_type == VersionType.AI_GENERATED.value
        ),
        None,
    )
    if generated is None or not generated.markdown_content:
        raise KnowledgeBlockNotConfirmableError

    markdown = payload.markdown_content
    next_version_number = max(version.version_number for version in block.versions) + 1
    version = KnowledgeVersion(
        knowledge_block=block,
        version_number=next_version_number,
        version_type=VersionType.USER_CONFIRMED.value,
        topic_instruction=generated.topic_instruction,
        raw_text=generated.raw_text,
        markdown_content=markdown,
        structured_metadata={
            "source_version_id": str(generated.id),
            "source_version_type": generated.version_type,
        },
        created_by=CreatedBy.USER.value,
        content_hash=hashlib.sha256(markdown.encode()).hexdigest(),
    )
    now = datetime.now(UTC)
    block.title = payload.title
    block.summary = payload.summary
    block.category_id = payload.category_id
    block.current_version = version
    block.status = KnowledgeStatus.SEARCHABLE.value
    block.confirmed_at = block.confirmed_at or now
    session.add(version)
    for chunk in block.chunks:
        chunk.is_active = False
    chunks = [
        KnowledgeChunk(
            knowledge_block=block,
            knowledge_version=version,
            chunk_index=chunk.chunk_index,
            heading_path=chunk.heading_path,
            content=chunk.content,
            token_count=chunk.token_count,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            content_hash=chunk.content_hash,
            is_active=True,
        )
        for chunk in chunk_markdown(markdown)
    ]
    session.add_all(chunks)
    await session.flush()
    session.add_all(await chunk_embeddings_from_chunks(chunks))

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return await get_block(session, block.id)


async def list_blocks(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    category_id: UUID | None = None,
    uncategorized: bool = False,
    statuses: Sequence[str] | None = None,
) -> tuple[list[KnowledgeBlock], int]:
    filters = [KnowledgeBlock.deleted_at.is_(None)]
    if uncategorized:
        filters.append(KnowledgeBlock.category_id.is_(None))
    elif category_id is not None:
        filters.append(KnowledgeBlock.category_id == category_id)
    if statuses:
        filters.append(KnowledgeBlock.status.in_(statuses))
    total = await session.scalar(
        select(func.count()).select_from(KnowledgeBlock).where(*filters)
    )
    result = await session.scalars(
        select(KnowledgeBlock)
        .where(*filters)
        .order_by(KnowledgeBlock.created_at.desc(), KnowledgeBlock.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result), total or 0


async def list_deleted_blocks(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
) -> tuple[list[KnowledgeBlock], int]:
    filters = [KnowledgeBlock.deleted_at.is_not(None)]
    total = await session.scalar(
        select(func.count()).select_from(KnowledgeBlock).where(*filters)
    )
    result = await session.scalars(
        select(KnowledgeBlock)
        .where(*filters)
        .order_by(KnowledgeBlock.deleted_at.desc(), KnowledgeBlock.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result), total or 0


async def get_block(session: AsyncSession, block_id: UUID) -> KnowledgeBlock:
    block = await session.scalar(
        select(KnowledgeBlock)
        .where(
            KnowledgeBlock.id == block_id,
            KnowledgeBlock.deleted_at.is_(None),
        )
        .options(selectinload(KnowledgeBlock.versions))
        .options(selectinload(KnowledgeBlock.attachments))
        .options(selectinload(KnowledgeBlock.ingestion_jobs))
        .options(selectinload(KnowledgeBlock.chunks))
    )
    if block is None:
        raise KnowledgeBlockNotFoundError
    return block


async def get_deleted_block(session: AsyncSession, block_id: UUID) -> KnowledgeBlock:
    block = await session.scalar(
        select(KnowledgeBlock).where(
            KnowledgeBlock.id == block_id,
            KnowledgeBlock.deleted_at.is_not(None),
        )
    )
    if block is None:
        raise KnowledgeBlockNotFoundError
    return block


async def ensure_category_exists(
    session: AsyncSession,
    category_id: UUID | None,
) -> None:
    if category_id is None:
        return
    if await session.get(Category, category_id) is None:
        raise CategoryNotFoundError


async def list_categories(session: AsyncSession) -> list[Category]:
    result = await session.scalars(
        select(Category).order_by(Category.sort_order, Category.name)
    )
    return list(result)


async def get_category(session: AsyncSession, category_id: UUID) -> Category:
    category = await session.get(Category, category_id)
    if category is None:
        raise CategoryNotFoundError
    return category


async def create_category(
    session: AsyncSession,
    payload: CategoryCreate,
) -> Category:
    category = Category(
        name=payload.name,
        description=payload.description,
        color=payload.color,
        is_system=False,
        sort_order=100,
    )
    session.add(category)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise CategoryNameConflictError from error
    await session.refresh(category)
    return category


async def update_category(
    session: AsyncSession,
    category_id: UUID,
    payload: CategoryUpdate,
) -> Category:
    category = await get_category(session, category_id)
    if category.is_system:
        raise SystemCategoryProtectedError

    if payload.name is not None:
        category.name = payload.name
    if "description" in payload.model_fields_set:
        category.description = payload.description
    if "color" in payload.model_fields_set:
        category.color = payload.color

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise CategoryNameConflictError from error
    await session.refresh(category)
    return category


async def delete_category(session: AsyncSession, category_id: UUID) -> None:
    category = await get_category(session, category_id)
    if category.is_system:
        raise SystemCategoryProtectedError

    await session.execute(
        update(KnowledgeBlock)
        .where(KnowledgeBlock.category_id == category_id)
        .values(category_id=None)
    )
    await session.delete(category)
    await session.commit()
