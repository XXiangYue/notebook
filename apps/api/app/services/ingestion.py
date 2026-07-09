import hashlib
import uuid
from datetime import UTC, datetime
from uuid import UUID

from arq.connections import ArqRedis
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.app.config import Settings
from apps.api.app.models.knowledge import (
    Attachment,
    AttachmentStatus,
    CreatedBy,
    IngestionJob,
    JobStatus,
    JobType,
    KnowledgeBlock,
    KnowledgeStatus,
    KnowledgeVersion,
    VersionType,
)
from apps.api.app.services.ai_settings import load_effective_settings
from apps.api.app.services.knowledge import (
    KnowledgeBlockNotEditableError,
    get_block,
)
from apps.api.app.services.organizer import (
    OrganizeInput,
    Organizer,
    OrganizerAttachment,
    create_organizer,
)
from apps.api.app.services.storage import LocalAttachmentStorage


class IngestionJobNotFoundError(Exception):
    pass


class IngestionJobConflictError(Exception):
    pass


async def create_attachment(
    session: AsyncSession,
    settings: Settings,
    block_id: UUID,
    upload: UploadFile,
) -> Attachment:
    block = await get_block(session, block_id)
    if block.status not in {
        KnowledgeStatus.DRAFT.value,
        KnowledgeStatus.PENDING_CONFIRMATION.value,
    }:
        raise KnowledgeBlockNotEditableError

    storage = LocalAttachmentStorage(settings)
    stored = await storage.save(block_id, upload)
    attachment = Attachment(
        knowledge_block_id=block.id,
        storage_key=stored.storage_key,
        original_filename=stored.original_filename,
        media_type=stored.media_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        processing_status=AttachmentStatus.PENDING.value,
    )
    session.add(attachment)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        storage.delete(stored.storage_key)
        raise
    await session.refresh(attachment)
    return attachment


async def create_organize_job(
    session: AsyncSession,
    queue: ArqRedis,
    block_id: UUID,
) -> IngestionJob:
    block = await get_block(session, block_id)
    if block.status not in {
        KnowledgeStatus.DRAFT.value,
        KnowledgeStatus.PENDING_CONFIRMATION.value,
    }:
        raise IngestionJobConflictError

    active_job = await session.scalar(
        select(IngestionJob).where(
            IngestionJob.knowledge_block_id == block_id,
            IngestionJob.job_type == JobType.ORGANIZE.value,
            IngestionJob.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
        )
    )
    if active_job is not None:
        raise IngestionJobConflictError

    job = IngestionJob(
        knowledge_block_id=block_id,
        job_type=JobType.ORGANIZE.value,
        status=JobStatus.QUEUED.value,
        idempotency_key=f"organize:{block_id}:{uuid.uuid4().hex}",
    )
    block.status = KnowledgeStatus.ORGANIZING.value
    session.add(job)
    await session.commit()
    await session.refresh(job)

    try:
        queued = await queue.enqueue_job(
            "organize_knowledge",
            str(job.id),
            _job_id=str(job.id),
        )
        if queued is None:
            raise RuntimeError("Queue rejected duplicate job")
    except Exception as error:
        job.status = JobStatus.FAILED.value
        job.error_code = "queue_unavailable"
        job.error_message = "Unable to enqueue organize task"
        job.finished_at = datetime.now(UTC)
        block.status = KnowledgeStatus.DRAFT.value
        await session.commit()
        raise RuntimeError("Unable to enqueue organize task") from error

    return job


async def get_ingestion_job(session: AsyncSession, job_id: UUID) -> IngestionJob:
    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise IngestionJobNotFoundError
    return job


async def process_organize_job(
    session: AsyncSession,
    job_id: UUID,
    organizer: Organizer | None = None,
) -> None:
    job = await session.scalar(
        select(IngestionJob)
        .where(IngestionJob.id == job_id)
        .options(
            selectinload(IngestionJob.knowledge_block).selectinload(
                KnowledgeBlock.versions
            ),
            selectinload(IngestionJob.knowledge_block).selectinload(
                KnowledgeBlock.current_version
            ),
            selectinload(IngestionJob.knowledge_block).selectinload(
                KnowledgeBlock.attachments
            ),
        )
    )
    if job is None:
        raise IngestionJobNotFoundError
    if job.status == JobStatus.SUCCEEDED.value:
        return

    block = job.knowledge_block
    job.status = JobStatus.RUNNING.value
    job.attempt_count += 1
    job.started_at = datetime.now(UTC)
    block.status = KnowledgeStatus.ORGANIZING.value
    await session.commit()

    try:
        source = block.current_version or block.versions[-1]
        raw_text = source.raw_text or source.markdown_content or ""
        settings = load_effective_settings()
        storage = LocalAttachmentStorage(settings)
        result = await (organizer or create_organizer(settings)).organize(
            OrganizeInput(
                title=block.title,
                topic=source.topic_instruction,
                raw_text=raw_text,
                attachments=[
                    OrganizerAttachment(
                        name=attachment.original_filename,
                        media_type=attachment.media_type,
                        path=storage.path_for(attachment.storage_key),
                    )
                    for attachment in block.attachments
                ],
            )
        )
        next_version_number = max(version.version_number for version in block.versions) + 1
        version = KnowledgeVersion(
            knowledge_block=block,
            version_number=next_version_number,
            version_type=VersionType.AI_GENERATED.value,
            topic_instruction=source.topic_instruction,
            raw_text=raw_text,
            markdown_content=result.markdown,
            structured_metadata=result.metadata,
            created_by=CreatedBy.MODEL.value,
            content_hash=hashlib.sha256(result.markdown.encode()).hexdigest(),
        )
        session.add(version)
        block.title = result.title
        block.summary = result.summary
        block.status = KnowledgeStatus.PENDING_CONFIRMATION.value
        for attachment in block.attachments:
            attachment.processing_status = AttachmentStatus.PROCESSED.value
        job.status = JobStatus.SUCCEEDED.value
        job.finished_at = datetime.now(UTC)
        job.error_code = None
        job.error_message = None
        await session.commit()
    except Exception as error:
        await session.rollback()
        failed_job = await session.get(IngestionJob, job_id)
        if failed_job is not None:
            failed_job.status = JobStatus.FAILED.value
            failed_job.error_code = "organize_failed"
            failed_job.error_message = str(error)[:1000]
            failed_job.finished_at = datetime.now(UTC)
            failed_block = await session.get(KnowledgeBlock, failed_job.knowledge_block_id)
            if failed_block is not None:
                failed_block.status = KnowledgeStatus.DRAFT.value
            await session.commit()
        raise
