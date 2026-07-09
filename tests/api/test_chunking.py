from apps.api.app.services.chunking import chunk_markdown


def test_chunk_markdown_tracks_heading_path() -> None:
    chunks = chunk_markdown(
        """# RAG

系统概览。

## 召回

- 关键词检索
- 向量检索

## 重排

使用 reranker 处理候选。"""
    )

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert [chunk.heading_path for chunk in chunks] == [
        ["RAG"],
        ["RAG", "召回"],
        ["RAG", "重排"],
    ]
    assert "# RAG" in chunks[0].content
    assert "系统概览" in chunks[0].content
    assert "关键词检索" in chunks[1].content
    assert chunks[0].token_count > 0
    assert chunks[0].char_start == 0
    assert chunks[0].char_end <= len(
        """# RAG

系统概览。

## 召回

- 关键词检索
- 向量检索

## 重排

使用 reranker 处理候选。"""
    )


def test_chunk_markdown_splits_large_blocks() -> None:
    content = "# 长文\n\n" + "这是一个很长的段落。" * 220

    chunks = chunk_markdown(content)

    assert len(chunks) > 1
    assert all(chunk.heading_path == ["长文"] for chunk in chunks)
    assert all(chunk.content for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
