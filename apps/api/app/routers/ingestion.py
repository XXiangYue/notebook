from typing import Annotated
from uuid import UUID

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.config import get_settings
from apps.api.app.database import get_session
from apps.api.app.dependencies import get_job_queue
from apps.api.app.schemas.knowledge import AttachmentResponse, IngestionJobResponse
from apps.api.app.services.ingestion import (
    IngestionJobConflictError,
    IngestionJobNotFoundError,
    create_attachment,
    create_organize_job,
    get_ingestion_job,
)
from apps.api.app.services.knowledge import (
    KnowledgeBlockNotEditableError,
    KnowledgeBlockNotFoundError,
)
from apps.api.app.services.storage import AttachmentValidationError

router = APIRouter(tags=["ingestion"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
QueueDependency = Annotated[ArqRedis, Depends(get_job_queue)]
settings = get_settings()


@router.post(
    "/knowledge-blocks/{block_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    block_id: UUID,
    session: SessionDependency,
    file: Annotated[UploadFile, File()],
) -> AttachmentResponse:
    try:
        attachment = await create_attachment(session, settings, block_id, file)
    except KnowledgeBlockNotFoundError as error:
        raise HTTPException(status_code=404, detail="Knowledge block not found") from error
    except KnowledgeBlockNotEditableError as error:
        raise HTTPException(status_code=409, detail="Knowledge block is not editable") from error
    except AttachmentValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return AttachmentResponse.model_validate(attachment)


@router.post(
    "/knowledge-blocks/{block_id}/organize",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def organize_knowledge_block(
    block_id: UUID,
    session: SessionDependency,
    queue: QueueDependency,
) -> IngestionJobResponse:
    try:
        job = await create_organize_job(session, queue, block_id)
    except KnowledgeBlockNotFoundError as error:
        raise HTTPException(status_code=404, detail="Knowledge block not found") from error
    except IngestionJobConflictError as error:
        raise HTTPException(
            status_code=409,
            detail="Knowledge block already has an active organize job",
        ) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return IngestionJobResponse.model_validate(job)


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_job(
    job_id: UUID,
    session: SessionDependency,
) -> IngestionJobResponse:
    try:
        job = await get_ingestion_job(session, job_id)
    except IngestionJobNotFoundError as error:
        raise HTTPException(status_code=404, detail="Job not found") from error
    return IngestionJobResponse.model_validate(job)
