from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.database import get_session
from apps.api.app.models.knowledge import KnowledgeStatus
from apps.api.app.schemas.knowledge import (
    KnowledgeBlockDetail,
    KnowledgeBlockList,
    KnowledgeBlockSummary,
    KnowledgeBlockUpdate,
    KnowledgeConfirm,
    KnowledgeDraftCreate,
)
from apps.api.app.services.knowledge import (
    CategoryNotFoundError,
    KnowledgeBlockNotConfirmableError,
    KnowledgeBlockNotEditableError,
    KnowledgeBlockNotFoundError,
    confirm_ai_result,
    create_draft,
    get_block,
    list_blocks,
    list_deleted_blocks,
    purge_block,
    restore_block,
    soft_delete_block,
    update_block,
)

router = APIRouter(prefix="/knowledge-blocks", tags=["knowledge-blocks"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=KnowledgeBlockDetail, status_code=status.HTTP_201_CREATED)
async def create_knowledge_draft(
    payload: KnowledgeDraftCreate,
    session: SessionDependency,
) -> KnowledgeBlockDetail:
    try:
        block = await create_draft(session, payload)
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Category not found",
        ) from error
    return KnowledgeBlockDetail.model_validate(block)


@router.get("", response_model=KnowledgeBlockList)
async def get_knowledge_blocks(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    category_id: UUID | None = None,
    uncategorized: bool = False,
    status_filter: Annotated[list[KnowledgeStatus] | None, Query(alias="status")] = None,
) -> KnowledgeBlockList:
    blocks, total = await list_blocks(
        session,
        limit=limit,
        offset=offset,
        category_id=category_id,
        uncategorized=uncategorized,
        statuses=[item.value for item in status_filter] if status_filter else None,
    )
    return KnowledgeBlockList(
        items=[KnowledgeBlockSummary.model_validate(block) for block in blocks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/deleted", response_model=KnowledgeBlockList)
async def get_deleted_knowledge_blocks(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> KnowledgeBlockList:
    blocks, total = await list_deleted_blocks(session, limit=limit, offset=offset)
    return KnowledgeBlockList(
        items=[KnowledgeBlockSummary.model_validate(block) for block in blocks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{block_id}", response_model=KnowledgeBlockDetail)
async def get_knowledge_block(
    block_id: UUID,
    session: SessionDependency,
) -> KnowledgeBlockDetail:
    try:
        block = await get_block(session, block_id)
    except KnowledgeBlockNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge block not found",
        ) from error
    return KnowledgeBlockDetail.model_validate(block)


@router.post("/{block_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_knowledge_block(
    block_id: UUID,
    session: SessionDependency,
) -> None:
    try:
        await restore_block(session, block_id)
    except KnowledgeBlockNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted knowledge block not found",
        ) from error


@router.delete("/{block_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
async def purge_knowledge_block(
    block_id: UUID,
    session: SessionDependency,
) -> None:
    try:
        await purge_block(session, block_id)
    except KnowledgeBlockNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted knowledge block not found",
        ) from error


@router.post("/{block_id}/confirm", response_model=KnowledgeBlockDetail)
async def confirm_knowledge_block(
    block_id: UUID,
    payload: KnowledgeConfirm,
    session: SessionDependency,
) -> KnowledgeBlockDetail:
    try:
        block = await confirm_ai_result(session, block_id, payload)
    except KnowledgeBlockNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge block not found",
        ) from error
    except KnowledgeBlockNotConfirmableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Knowledge block has no AI result to confirm",
        ) from error
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Category not found",
        ) from error
    return KnowledgeBlockDetail.model_validate(block)


@router.patch("/{block_id}", response_model=KnowledgeBlockDetail)
async def update_knowledge_draft(
    block_id: UUID,
    payload: KnowledgeBlockUpdate,
    session: SessionDependency,
) -> KnowledgeBlockDetail:
    try:
        block = await update_block(session, block_id, payload)
    except KnowledgeBlockNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge block not found",
        ) from error
    except KnowledgeBlockNotEditableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Knowledge block cannot be edited while organizing",
        ) from error
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Category not found",
        ) from error
    return KnowledgeBlockDetail.model_validate(block)


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_block(
    block_id: UUID,
    session: SessionDependency,
) -> None:
    try:
        await soft_delete_block(session, block_id)
    except KnowledgeBlockNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge block not found",
        ) from error
