from pathlib import Path
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.api.app.routers import ingestion as ingestion_router
from apps.api.app.services.ingestion import process_organize_job
from apps.api.app.services.organizer import LocalOrganizer


async def test_upload_attachment_and_run_organize_job(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    original_storage_root = ingestion_router.settings.storage_root
    ingestion_router.settings.storage_root = str(tmp_path)
    try:
        created = await api_client.post(
            "/knowledge-blocks",
            json={
                "title": "混合检索笔记",
                "topic": "整理核心概念",
                "raw_text": "混合检索同时使用关键词召回和向量召回。",
            },
        )
        block_id = created.json()["id"]

        uploaded = await api_client.post(
            f"/knowledge-blocks/{block_id}/attachments",
            files={"file": ("notes.md", b"# attachment", "text/markdown")},
        )
        assert uploaded.status_code == 201
        assert uploaded.json()["original_filename"] == "notes.md"
        assert uploaded.json()["processing_status"] == "pending"
        assert list((tmp_path / "attachments" / block_id).iterdir())

        queued = await api_client.post(f"/knowledge-blocks/{block_id}/organize")
        assert queued.status_code == 202
        job_id = queued.json()["id"]
        assert queued.json()["status"] == "queued"

        async with session_factory() as session:
            await process_organize_job(session, UUID(job_id), organizer=LocalOrganizer())

        job = await api_client.get(f"/jobs/{job_id}")
        detail = await api_client.get(f"/knowledge-blocks/{block_id}")
        assert job.json()["status"] == "succeeded"
        assert detail.json()["status"] == "pending_confirmation"
        assert detail.json()["summary"] == "混合检索同时使用关键词召回和向量召回。"
        assert detail.json()["attachments"][0]["processing_status"] == "processed"
        generated = detail.json()["versions"][-1]
        assert generated["version_type"] == "ai_generated"
        assert "# 混合检索笔记" in generated["markdown_content"]
        assert "- notes.md" in generated["markdown_content"]
    finally:
        ingestion_router.settings.storage_root = original_storage_root


async def test_reject_unsupported_attachment(api_client: AsyncClient) -> None:
    created = await api_client.post(
        "/knowledge-blocks",
        json={"raw_text": "原始内容"},
    )
    response = await api_client.post(
        f"/knowledge-blocks/{created.json()['id']}/attachments",
        files={"file": ("payload.exe", b"binary", "application/octet-stream")},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Unsupported attachment type"}


async def test_confirm_ai_result_creates_user_confirmed_version(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    created = await api_client.post(
        "/knowledge-blocks",
        json={
            "title": "待确认知识",
            "topic": "整理为 Markdown",
            "raw_text": "原始内容",
        },
    )
    block_id = created.json()["id"]
    queued = await api_client.post(f"/knowledge-blocks/{block_id}/organize")
    job_id = queued.json()["id"]
    async with session_factory() as session:
        await process_organize_job(session, UUID(job_id), organizer=LocalOrganizer())

    category = await api_client.post("/categories", json={"name": "确认分类"})
    response = await api_client.post(
        f"/knowledge-blocks/{block_id}/confirm",
        json={
            "title": "确认后的标题",
            "summary": "用户确认摘要",
            "markdown_content": "# 确认后的标题\n\n用户修订后的正文。",
            "category_id": category.json()["id"],
        },
    )

    assert response.status_code == 200
    confirmed = response.json()
    assert confirmed["title"] == "确认后的标题"
    assert confirmed["summary"] == "用户确认摘要"
    assert confirmed["status"] == "searchable"
    assert confirmed["category_id"] == category.json()["id"]
    assert confirmed["confirmed_at"] is not None
    assert confirmed["current_version_id"] == confirmed["versions"][-1]["id"]
    assert len(confirmed["chunks"]) == 1
    assert confirmed["chunks"][0]["chunk_index"] == 0
    assert confirmed["chunks"][0]["is_active"] is True
    assert confirmed["chunks"][0]["knowledge_version_id"] == confirmed["current_version_id"]
    assert confirmed["chunks"][0]["heading_path"] == ["确认后的标题"]
    assert "用户修订后的正文" in confirmed["chunks"][0]["content"]
    assert [version["version_type"] for version in confirmed["versions"]] == [
        "original",
        "ai_generated",
        "user_confirmed",
    ]
    current = confirmed["versions"][-1]
    assert current["created_by"] == "user"
    assert current["markdown_content"] == "# 确认后的标题\n\n用户修订后的正文。"
    assert current["structured_metadata"]["source_version_type"] == "ai_generated"


async def test_confirm_requires_pending_ai_result(api_client: AsyncClient) -> None:
    created = await api_client.post(
        "/knowledge-blocks",
        json={"raw_text": "还没有整理"},
    )

    response = await api_client.post(
        f"/knowledge-blocks/{created.json()['id']}/confirm",
        json={
            "title": "不能确认",
            "markdown_content": "# 不能确认",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Knowledge block has no AI result to confirm"}
