import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.api.app.models.knowledge import Category, KnowledgeBlock


async def test_create_and_get_draft(api_client: AsyncClient) -> None:
    create_response = await api_client.post(
        "/knowledge-blocks",
        json={
            "topic": "RAG 检索",
            "raw_text": "混合检索结合关键词召回与向量召回。",
            "language": "zh-CN",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == "RAG 检索"
    assert created["status"] == "draft"
    assert created["source_type"] == "manual"
    assert created["current_version_id"] is None
    assert len(created["versions"]) == 1

    version = created["versions"][0]
    assert version["version_type"] == "original"
    assert version["created_by"] == "user"
    assert version["raw_text"] == "混合检索结合关键词召回与向量召回。"
    assert version["content_hash"] == hashlib.sha256(
        "混合检索结合关键词召回与向量召回。".encode()
    ).hexdigest()

    detail_response = await api_client.get(f"/knowledge-blocks/{created['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json() == created


async def test_explicit_title_has_priority(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/knowledge-blocks",
        json={
            "title": "自定义标题",
            "topic": "模型建议主题",
            "raw_text": "原始内容",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "自定义标题"


async def test_create_edit_and_delete_draft_with_category(api_client: AsyncClient) -> None:
    category_response = await api_client.post(
        "/categories",
        json={"name": "技术", "description": "技术资料", "color": "#176B4D"},
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    create_response = await api_client.post(
        "/knowledge-blocks",
        json={
            "title": "初始标题",
            "topic": "初始主题",
            "raw_text": "初始原始内容",
        },
    )
    block_id = create_response.json()["id"]

    update_response = await api_client.patch(
        f"/knowledge-blocks/{block_id}",
        json={
            "title": "编辑后的标题",
            "topic": "编辑后的主题",
            "raw_text": "编辑后的原始内容",
            "language": "zh-CN",
            "category_id": category_id,
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["title"] == "编辑后的标题"
    assert updated["category_id"] == category_id
    assert updated["current_version_id"] == updated["versions"][1]["id"]
    assert [version["version_type"] for version in updated["versions"]] == [
        "original",
        "user_edited",
    ]
    assert updated["versions"][0]["raw_text"] == "初始原始内容"
    assert updated["versions"][1]["raw_text"] == "编辑后的原始内容"

    delete_response = await api_client.delete(f"/knowledge-blocks/{block_id}")
    assert delete_response.status_code == 204
    assert (await api_client.get(f"/knowledge-blocks/{block_id}")).status_code == 404
    assert (await api_client.get("/knowledge-blocks")).json()["total"] == 0


async def test_reject_unknown_category(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/knowledge-blocks",
        json={"raw_text": "内容", "category_id": str(uuid4())},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Category not found"}


async def test_categories_are_listed_and_names_are_unique(api_client: AsyncClient) -> None:
    first = await api_client.post("/categories", json={"name": "金融"})
    duplicate = await api_client.post("/categories", json={"name": "金融"})
    categories = await api_client.get("/categories")

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert categories.status_code == 200
    assert [category["name"] for category in categories.json()] == ["金融"]


async def test_custom_categories_can_be_updated(api_client: AsyncClient) -> None:
    first = await api_client.post("/categories", json={"name": "金融"})
    second = await api_client.post("/categories", json={"name": "工作"})
    category_id = first.json()["id"]

    updated = await api_client.patch(
        f"/categories/{category_id}",
        json={"name": "投资", "description": "  ", "color": "#123456"},
    )
    duplicate = await api_client.patch(
        f"/categories/{category_id}",
        json={"name": second.json()["name"]},
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "投资"
    assert updated.json()["description"] is None
    assert updated.json()["color"] == "#123456"
    assert duplicate.status_code == 409


async def test_custom_category_delete_uncategorizes_blocks(
    api_client: AsyncClient,
) -> None:
    category = await api_client.post("/categories", json={"name": "资料"})
    category_id = category.json()["id"]
    block = await api_client.post(
        "/knowledge-blocks",
        json={
            "title": "分类知识",
            "raw_text": "有分类的内容",
            "category_id": category_id,
        },
    )

    deleted = await api_client.delete(f"/categories/{category_id}")
    block_detail = await api_client.get(f"/knowledge-blocks/{block.json()['id']}")
    categorized = await api_client.get(f"/knowledge-blocks?category_id={category_id}")
    uncategorized = await api_client.get("/knowledge-blocks?uncategorized=true")

    assert deleted.status_code == 204
    assert block_detail.json()["category_id"] is None
    assert categorized.json()["total"] == 0
    assert [item["id"] for item in uncategorized.json()["items"]] == [block.json()["id"]]


async def test_system_categories_cannot_be_modified_or_deleted(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        category = Category(name="系统", is_system=True, sort_order=0)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        category_id = str(category.id)

    updated = await api_client.patch(
        f"/categories/{category_id}",
        json={"name": "新系统分类"},
    )
    deleted = await api_client.delete(f"/categories/{category_id}")

    assert updated.status_code == 403
    assert updated.json() == {"detail": "System categories cannot be modified"}
    assert deleted.status_code == 403
    assert deleted.json() == {"detail": "System categories cannot be deleted"}


async def test_list_drafts_with_pagination(api_client: AsyncClient) -> None:
    for index in range(3):
        response = await api_client.post(
            "/knowledge-blocks",
            json={"title": f"知识 {index}", "raw_text": f"内容 {index}"},
        )
        assert response.status_code == 201

    response = await api_client.get("/knowledge-blocks?limit=2&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert len(payload["items"]) == 2
    assert "versions" not in payload["items"][0]


async def test_list_blocks_can_filter_by_category_and_uncategorized(
    api_client: AsyncClient,
) -> None:
    category_response = await api_client.post("/categories", json={"name": "资料"})
    category_id = category_response.json()["id"]

    categorized = await api_client.post(
        "/knowledge-blocks",
        json={
            "title": "分类知识",
            "raw_text": "有分类的内容",
            "category_id": category_id,
        },
    )
    uncategorized = await api_client.post(
        "/knowledge-blocks",
        json={"title": "未分类知识", "raw_text": "未分类内容"},
    )

    categorized_list = await api_client.get(
        f"/knowledge-blocks?category_id={category_id}"
    )
    uncategorized_list = await api_client.get("/knowledge-blocks?uncategorized=true")

    assert categorized_list.status_code == 200
    assert [item["id"] for item in categorized_list.json()["items"]] == [
        categorized.json()["id"]
    ]
    assert uncategorized_list.status_code == 200
    assert [item["id"] for item in uncategorized_list.json()["items"]] == [
        uncategorized.json()["id"]
    ]


async def test_list_blocks_can_filter_by_multiple_statuses(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    draft = await api_client.post(
        "/knowledge-blocks",
        json={"title": "草稿知识", "raw_text": "草稿内容"},
    )
    organizing = await api_client.post(
        "/knowledge-blocks",
        json={"title": "整理中知识", "raw_text": "整理中内容"},
    )
    pending = await api_client.post(
        "/knowledge-blocks",
        json={"title": "待确认知识", "raw_text": "待确认内容"},
    )
    searchable = await api_client.post(
        "/knowledge-blocks",
        json={"title": "已入库知识", "raw_text": "已入库内容"},
    )

    async with session_factory() as session:
        organizing_block = await session.get(KnowledgeBlock, UUID(organizing.json()["id"]))
        pending_block = await session.get(KnowledgeBlock, UUID(pending.json()["id"]))
        searchable_block = await session.get(KnowledgeBlock, UUID(searchable.json()["id"]))
        assert organizing_block is not None
        assert pending_block is not None
        assert searchable_block is not None
        organizing_block.status = "organizing"
        pending_block.status = "pending_confirmation"
        searchable_block.status = "searchable"
        await session.commit()

    response = await api_client.get(
        "/knowledge-blocks?status=draft&status=pending_confirmation"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert {item["id"] for item in payload["items"]} == {
        draft.json()["id"],
        pending.json()["id"],
    }


async def test_reject_blank_raw_text(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/knowledge-blocks",
        json={"raw_text": "   "},
    )

    assert response.status_code == 422


async def test_get_missing_block_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/knowledge-blocks/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Knowledge block not found"}


async def test_soft_deleted_block_is_hidden(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    create_response = await api_client.post(
        "/knowledge-blocks",
        json={"raw_text": "即将软删除的内容"},
    )
    block_id = create_response.json()["id"]

    async with session_factory() as session:
        block = await session.get(KnowledgeBlock, UUID(block_id))
        assert block is not None
        block.deleted_at = datetime.now(UTC)
        block.status = "deleted"
        await session.commit()

    detail_response = await api_client.get(f"/knowledge-blocks/{block_id}")
    list_response = await api_client.get("/knowledge-blocks")

    assert detail_response.status_code == 404
    assert list_response.json()["total"] == 0


async def test_deleted_blocks_can_be_listed_restored_and_purged(
    api_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    create_response = await api_client.post(
        "/knowledge-blocks",
        json={"title": "可恢复知识", "raw_text": "删除后恢复"},
    )
    block_id = create_response.json()["id"]

    delete_response = await api_client.delete(f"/knowledge-blocks/{block_id}")
    deleted_list = await api_client.get("/knowledge-blocks/deleted")

    assert delete_response.status_code == 204
    assert deleted_list.status_code == 200
    assert deleted_list.json()["total"] == 1
    assert deleted_list.json()["items"][0]["id"] == block_id
    assert deleted_list.json()["items"][0]["deleted_at"] is not None

    restore_response = await api_client.post(f"/knowledge-blocks/{block_id}/restore")
    restored_detail = await api_client.get(f"/knowledge-blocks/{block_id}")
    deleted_after_restore = await api_client.get("/knowledge-blocks/deleted")

    assert restore_response.status_code == 204
    assert restored_detail.status_code == 200
    assert restored_detail.json()["status"] == "draft"
    assert restored_detail.json()["deleted_at"] is None
    assert deleted_after_restore.json()["total"] == 0

    await api_client.delete(f"/knowledge-blocks/{block_id}")
    purge_response = await api_client.delete(f"/knowledge-blocks/{block_id}/purge")

    assert purge_response.status_code == 204
    async with session_factory() as session:
        assert await session.get(KnowledgeBlock, UUID(block_id)) is None
