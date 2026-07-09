import base64
import json
from pathlib import Path
from types import SimpleNamespace

import httpx

from apps.api.app.config import Settings
from apps.api.app.services.organizer import (
    DeepSeekOrganizer,
    MiniMaxOrganizer,
    OrganizeInput,
    OrganizerAttachment,
    create_organizer,
)


def test_minimax_prompt_contains_source_material(tmp_path: Path) -> None:
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("附件正文", encoding="utf-8")
    prompt = MiniMaxOrganizer._prompt(
        OrganizeInput(
            title="测试标题",
            topic="提炼重点",
            raw_text="原始正文",
            attachments=[
                OrganizerAttachment(
                    name="notes.md",
                    media_type="text/markdown",
                    path=attachment_path,
                )
            ],
        )
    )

    assert "测试标题" in prompt
    assert "提炼重点" in prompt
    assert "原始正文" in prompt
    assert "notes.md" in prompt


async def test_minimax_organizer_sends_base64_image(tmp_path: Path) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.write_bytes(b"png-content")
    settings = Settings(
        _env_file=None,
        minimax_api_key="test-key",
        minimax_base_url="https://example.test/anthropic",
    )
    organizer = MiniMaxOrganizer(settings)
    captured: dict = {}

    class FakeMessages:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="tool_use",
                        name="submit_organized_knowledge",
                        input={
                            "title": "图片整理",
                            "summary": "识别图片内容",
                            "markdown": "# 图片整理\n\n正文",
                            "keywords": ["图片"],
                            "warnings": [],
                        },
                    )
                ],
                usage=SimpleNamespace(input_tokens=10, output_tokens=20),
            )

    organizer.client = SimpleNamespace(messages=FakeMessages())
    result = await organizer.organize(
        OrganizeInput(
            title="图片知识",
            topic="识别图片",
            raw_text="结合图片整理",
            attachments=[
                OrganizerAttachment(
                    name="diagram.png",
                    media_type="image/png",
                    path=image_path,
                )
            ],
        )
    )

    image_block = captured["messages"][0]["content"][1]
    assert image_block["type"] == "image"
    assert image_block["source"]["data"] == base64.b64encode(b"png-content").decode()
    assert captured["tool_choice"]["name"] == "submit_organized_knowledge"
    assert result.metadata["provider"] == "minimax"
    assert result.metadata["usage"] == {"input_tokens": 10, "output_tokens": 20}


def test_minimax_organizer_requires_api_key() -> None:
    settings = Settings(
        _env_file=None,
        organizer_provider="minimax",
        minimax_api_key=None,
    )

    try:
        MiniMaxOrganizer(settings)
    except ValueError as error:
        assert str(error) == "MINIMAX_API_KEY is required for the MiniMax organizer"
    else:
        raise AssertionError("MiniMaxOrganizer accepted a missing API key")


async def test_deepseek_organizer_uses_chat_completions_json(tmp_path: Path) -> None:
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("附件正文", encoding="utf-8")
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "DeepSeek 整理",
                                    "summary": "摘要",
                                    "markdown": "# DeepSeek 整理\n\n正文",
                                    "keywords": ["deepseek"],
                                    "warnings": [],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 22},
            },
        )

    settings = Settings(
        _env_file=None,
        organizer_provider="deepseek",
        deepseek_api_key="test-key",
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-v4-flash",
        deepseek_max_tokens=4096,
    )
    organizer = DeepSeekOrganizer(settings, transport=httpx.MockTransport(handler))

    result = await organizer.organize(
        OrganizeInput(
            title="测试标题",
            topic="整理重点",
            raw_text="原始正文",
            attachments=[
                OrganizerAttachment(
                    name="notes.md",
                    media_type="text/markdown",
                    path=attachment_path,
                )
            ],
        )
    )

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["body"]["model"] == "deepseek-v4-flash"
    assert captured["body"]["max_tokens"] == 4096
    assert captured["body"]["thinking"] == {"type": "disabled"}
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert "附件正文" in captured["body"]["messages"][1]["content"]
    assert result.title == "DeepSeek 整理"
    assert result.metadata["provider"] == "deepseek"
    assert result.metadata["usage"] == {"input_tokens": 11, "output_tokens": 22}


def test_deepseek_organizer_requires_api_key() -> None:
    settings = Settings(
        _env_file=None,
        organizer_provider="deepseek",
        deepseek_api_key=None,
    )

    try:
        DeepSeekOrganizer(settings)
    except ValueError as error:
        assert str(error) == "DEEPSEEK_API_KEY is required for the DeepSeek organizer"
    else:
        raise AssertionError("DeepSeekOrganizer accepted a missing API key")


def test_create_organizer_supports_deepseek() -> None:
    settings = Settings(
        _env_file=None,
        organizer_provider="deepseek",
        deepseek_api_key="test-key",
    )

    assert isinstance(create_organizer(settings), DeepSeekOrganizer)
