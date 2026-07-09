import hashlib
import re
from dataclasses import dataclass

TARGET_CHARS = 900
MAX_CHARS = 1400
MIN_CHARS = 120


@dataclass(frozen=True)
class ChunkDraft:
    chunk_index: int
    heading_path: list[str]
    content: str
    token_count: int
    char_start: int
    char_end: int
    content_hash: str


@dataclass(frozen=True)
class MarkdownBlock:
    heading_path: list[str]
    content: str
    char_start: int
    char_end: int


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def chunk_markdown(markdown: str) -> list[ChunkDraft]:
    normalized = markdown.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    blocks = parse_markdown_blocks(normalized)
    chunks: list[ChunkDraft] = []
    buffer: list[MarkdownBlock] = []
    buffer_size = 0

    def flush() -> None:
        nonlocal buffer, buffer_size
        if not buffer:
            return
        content = "\n\n".join(block.content.strip() for block in buffer if block.content.strip())
        if not content:
            buffer = []
            buffer_size = 0
            return
        chunks.append(
            ChunkDraft(
                chunk_index=len(chunks),
                heading_path=buffer[-1].heading_path,
                content=content,
                token_count=estimate_tokens(content),
                char_start=buffer[0].char_start,
                char_end=buffer[-1].char_end,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
            )
        )
        buffer = []
        buffer_size = 0

    for block in blocks:
        content_len = len(block.content)
        if (
            buffer
            and block.content.lstrip().startswith("#")
            and any(not item.content.lstrip().startswith("#") for item in buffer)
        ):
            flush()

        if content_len > MAX_CHARS:
            flush()
            for part, start, end in split_large_block(block):
                chunks.append(
                    ChunkDraft(
                        chunk_index=len(chunks),
                        heading_path=block.heading_path,
                        content=part,
                        token_count=estimate_tokens(part),
                        char_start=start,
                        char_end=end,
                        content_hash=hashlib.sha256(part.encode()).hexdigest(),
                    )
                )
            continue

        would_exceed = buffer and buffer_size + content_len > TARGET_CHARS
        is_large_enough = buffer_size >= MIN_CHARS
        if would_exceed and is_large_enough:
            flush()

        buffer.append(block)
        buffer_size += content_len

    flush()
    return chunks


def parse_markdown_blocks(markdown: str) -> list[MarkdownBlock]:
    blocks: list[MarkdownBlock] = []
    heading_stack: list[tuple[int, str]] = []
    block_lines: list[str] = []
    block_start: int | None = None
    offset = 0
    in_code = False

    def heading_path() -> list[str]:
        return [title for _, title in heading_stack]

    def flush(end: int) -> None:
        nonlocal block_lines, block_start
        if not block_lines or block_start is None:
            block_lines = []
            block_start = None
            return
        content = "\n".join(block_lines).strip()
        if content:
            blocks.append(
                MarkdownBlock(
                    heading_path=heading_path(),
                    content=content,
                    char_start=block_start,
                    char_end=end,
                )
            )
        block_lines = []
        block_start = None

    lines = markdown.splitlines(keepends=True)
    for raw_line in lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        line_start = offset
        line_end = offset + len(raw_line)
        offset = line_end

        if stripped.startswith("```"):
            if block_start is None:
                block_start = line_start
            block_lines.append(line)
            in_code = not in_code
            continue

        if not in_code:
            heading_match = HEADING_PATTERN.match(line)
            if heading_match:
                flush(line_start)
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                heading_stack = [
                    (existing_level, existing_title)
                    for existing_level, existing_title in heading_stack
                    if existing_level < level
                ]
                heading_stack.append((level, title))
                block_start = line_start
                block_lines.append(line)
                flush(line_end)
                continue

            if not stripped:
                flush(line_start)
                continue

        if block_start is None:
            block_start = line_start
        block_lines.append(line)

    flush(len(markdown))
    return blocks


def split_large_block(block: MarkdownBlock) -> list[tuple[str, int, int]]:
    parts: list[tuple[str, int, int]] = []
    start = 0
    content = block.content
    while start < len(content):
        end = min(start + TARGET_CHARS, len(content))
        if end < len(content):
            paragraph_break = content.rfind("\n\n", start, end)
            sentence_break = max(content.rfind("。", start, end), content.rfind(".", start, end))
            split_at = paragraph_break if paragraph_break > start + MIN_CHARS else sentence_break
            if split_at > start + MIN_CHARS:
                end = split_at + 1
        part = content[start:end].strip()
        if part:
            parts.append((part, block.char_start + start, block.char_start + end))
        start = end
    return parts


def estimate_tokens(content: str) -> int:
    ascii_words = re.findall(r"[A-Za-z0-9_]+", content)
    non_ascii_chars = re.findall(r"[^\x00-\x7F\s]", content)
    punctuation = re.findall(r"[^\w\s]", content)
    return max(1, len(ascii_words) + len(non_ascii_chars) + len(punctuation) // 2)
