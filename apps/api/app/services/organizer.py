import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx
from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from apps.api.app.config import Settings


@dataclass(frozen=True)
class OrganizeInput:
    title: str
    topic: str | None
    raw_text: str
    attachments: list["OrganizerAttachment"]


@dataclass(frozen=True)
class OrganizerAttachment:
    name: str
    media_type: str
    path: Path


@dataclass(frozen=True)
class OrganizeResult:
    title: str
    summary: str
    markdown: str
    metadata: dict


class Organizer(Protocol):
    async def organize(self, payload: OrganizeInput) -> OrganizeResult: ...


class ModelOrganizeOutput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=500)
    markdown: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def organize_prompt(payload: OrganizeInput) -> str:
    topic = payload.topic or "按内容本身整理"
    attachment_names = [attachment.name for attachment in payload.attachments]
    return f"""请围绕用户要求整理下面的知识块。

用户标题：{payload.title}
整理要求：{topic}
附件名称：{json.dumps(attachment_names, ensure_ascii=False)}

原始文本：
{payload.raw_text}

返回严格 JSON，字段结构如下：
{{
  "title": "准确、简洁的标题",
  "summary": "不超过 200 字的摘要",
  "markdown": "# 标题\\n\\n结构清晰且忠于原文的 Markdown 正文",
  "keywords": ["关键词"],
  "warnings": ["资料缺失、冲突或不确定信息"]
}}
"""


class LocalOrganizer:
    """Deterministic development adapter with the same boundary as a model provider."""

    async def organize(self, payload: OrganizeInput) -> OrganizeResult:
        normalized = " ".join(payload.raw_text.split())
        summary = normalized[:160] + ("…" if len(normalized) > 160 else "")
        sections = [f"# {payload.title}"]
        if payload.topic:
            sections.extend(["", f"> 整理要求：{payload.topic}"])
        sections.extend(["", "## 整理内容", "", payload.raw_text.strip()])
        attachment_names = [attachment.name for attachment in payload.attachments]
        if attachment_names:
            sections.extend(
                [
                    "",
                    "## 附件",
                    "",
                    *[f"- {name}" for name in attachment_names],
                ]
            )
        return OrganizeResult(
            title=payload.title,
            summary=summary,
            markdown="\n".join(sections),
            metadata={
                "provider": "local",
                "attachment_names": attachment_names,
                "warnings": ["当前使用本地整理适配器，尚未解析图片或 PDF 内容。"],
            },
        )


class MiniMaxOrganizer:
    def __init__(self, settings: Settings):
        if not settings.minimax_api_key:
            raise ValueError("MINIMAX_API_KEY is required for the MiniMax organizer")
        self.client = AsyncAnthropic(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
        )
        self.model = settings.minimax_model
        self.max_tokens = settings.minimax_max_tokens

    async def organize(self, payload: OrganizeInput) -> OrganizeResult:
        content: list[dict] = [{"type": "text", "text": self._prompt(payload)}]
        attachment_names: list[str] = []
        warnings: list[str] = []

        for attachment in payload.attachments:
            attachment_names.append(attachment.name)
            if attachment.media_type.startswith("image/"):
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": attachment.media_type,
                            "data": base64.b64encode(attachment.path.read_bytes()).decode(),
                        },
                    }
                )
            elif attachment.media_type in {"text/plain", "text/markdown"}:
                text = attachment.path.read_text(encoding="utf-8", errors="replace")
                content.append(
                    {
                        "type": "text",
                        "text": f"\n附件 {attachment.name} 的内容：\n{text}",
                    }
                )
            else:
                warnings.append(f"附件 {attachment.name} 暂未提取正文，仅提供文件名。")

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=(
                "你是个人知识库的内容整理器。忠实整理用户资料，不补充资料中不存在的事实。"
                "完成整理后必须调用指定工具提交结果。"
            ),
            messages=[{"role": "user", "content": content}],
            thinking={"type": "disabled"},
            tools=[
                {
                    "name": "submit_organized_knowledge",
                    "description": "提交结构化知识整理结果",
                    "input_schema": ModelOrganizeOutput.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "submit_organized_knowledge"},
        )
        tool_result = next(
            (
                block.input
                for block in response.content
                if block.type == "tool_use"
                and block.name == "submit_organized_knowledge"
            ),
            None,
        )
        if tool_result is None:
            raise ValueError("MiniMax did not return the organize tool result")
        output = ModelOrganizeOutput.model_validate(tool_result)
        return OrganizeResult(
            title=output.title,
            summary=output.summary,
            markdown=output.markdown,
            metadata={
                "provider": "minimax",
                "model": self.model,
                "attachment_names": attachment_names,
                "keywords": output.keywords,
                "warnings": [*output.warnings, *warnings],
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            },
        )

    @staticmethod
    def _prompt(payload: OrganizeInput) -> str:
        return organize_prompt(payload)


class DeepSeekOrganizer:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for the DeepSeek organizer")
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url
        self.model = settings.deepseek_model
        self.max_tokens = settings.deepseek_max_tokens
        self.timeout = settings.deepseek_timeout_seconds
        self.thinking_enabled = settings.deepseek_thinking_enabled
        self.transport = transport

    async def organize(self, payload: OrganizeInput) -> OrganizeResult:
        prompt_parts = [organize_prompt(payload)]
        attachment_names: list[str] = []
        warnings: list[str] = []

        for attachment in payload.attachments:
            attachment_names.append(attachment.name)
            if attachment.media_type in {"text/plain", "text/markdown"}:
                text = attachment.path.read_text(encoding="utf-8", errors="replace")
                prompt_parts.append(f"\n附件 {attachment.name} 的内容：\n{text}")
            else:
                warnings.append(f"附件 {attachment.name} 暂未提取正文，仅提供文件名。")

        request_body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是个人知识库的内容整理器。忠实整理用户资料，不补充资料中不存在的事实。"
                        "返回内容必须是一个 JSON 对象，不要使用 Markdown 代码块。"
                    ),
                },
                {"role": "user", "content": "\n\n".join(prompt_parts)},
            ],
        }
        if not self.thinking_enabled:
            request_body["thinking"] = {"type": "disabled"}

        async with httpx.AsyncClient(
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.post(
                self._chat_completions_url(),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )

        data = self._response_json(response)
        if response.status_code >= 400:
            message = self._error_message(data) or response.text
            raise ValueError(
                f"DeepSeek organizer request failed: HTTP {response.status_code}: {message}"
            )

        content = self._message_content(data)
        output = ModelOrganizeOutput.model_validate(self._json_object(content))
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        return OrganizeResult(
            title=output.title,
            summary=output.summary,
            markdown=output.markdown,
            metadata={
                "provider": "deepseek",
                "model": self.model,
                "attachment_names": attachment_names,
                "keywords": output.keywords,
                "warnings": [*output.warnings, *warnings],
                "usage": {
                    "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"),
                },
            },
        )

    def _chat_completions_url(self) -> str:
        base_url = self.base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    @staticmethod
    def _response_json(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as error:
            raise ValueError(
                f"DeepSeek organizer returned non-JSON response: HTTP {response.status_code}"
            ) from error
        if not isinstance(data, dict):
            raise ValueError("DeepSeek organizer response must be a JSON object")
        return data

    @staticmethod
    def _message_content(data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError(
                "DeepSeek organizer response does not contain message content"
            ) from error
        if not isinstance(content, str):
            raise ValueError("DeepSeek organizer message content must be a string")
        return content

    @staticmethod
    def _json_object(content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError("DeepSeek organizer did not return valid JSON") from error
        if not isinstance(data, dict):
            raise ValueError("DeepSeek organizer JSON result must be an object")
        return data

    @staticmethod
    def _error_message(data: dict[str, Any]) -> str | None:
        error = data.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
        return None


def create_organizer(settings: Settings) -> Organizer:
    if settings.organizer_provider == "deepseek":
        return DeepSeekOrganizer(settings)
    if settings.organizer_provider == "minimax":
        return MiniMaxOrganizer(settings)
    if settings.organizer_provider == "local":
        return LocalOrganizer()
    raise ValueError(f"Unsupported organizer provider: {settings.organizer_provider}")
