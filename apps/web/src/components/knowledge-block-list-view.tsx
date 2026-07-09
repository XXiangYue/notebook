import Link from "next/link";

import { KnowledgeStatus } from "@/components/knowledge-status";
import type { KnowledgeBlockSummary } from "@/lib/knowledge-api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function KnowledgeBlockListView({
  blocks,
  title,
}: {
  blocks: KnowledgeBlockSummary[];
  title: string;
}) {
  return (
    <section
      className="knowledge-list-panel"
      aria-label={`${title} 知识块列表`}
      data-bulk-mode="false"
    >
        <div className="knowledge-list-toolbar">
          <span className="knowledge-list-count" data-list-count>
            {blocks.length} 条知识
          </span>
          <button
            className="secondary-button secondary-button-small"
            data-bulk-enter
            disabled={blocks.length === 0}
            type="button"
          >
            批量选择
          </button>

          <div className="knowledge-list-bulk-actions" data-bulk-controls>
            <button
              className="secondary-button secondary-button-small"
              data-select-all
              type="button"
            >
              全选
            </button>
            <span data-selection-count>未选择知识</span>
          </div>
          <div className="knowledge-list-bulk-actions" data-bulk-controls>
            <button
              className="danger-button danger-button-small"
              data-delete-selected
              disabled
              type="button"
            >
              删除已选
            </button>
            <button
              className="secondary-button secondary-button-small"
              data-bulk-done
              type="button"
            >
              完成
            </button>
          </div>
        </div>

        <p className="list-error" data-list-error hidden role="alert" />

        <div className="knowledge-list">
          {blocks.map((block) => (
            <article
              className="knowledge-list-item"
              data-id={block.id}
              data-knowledge-item
              data-selected="false"
              data-title={block.title}
              key={block.id}
            >
              <label
                className="knowledge-select-control"
                aria-label={`选择 ${block.title}`}
                data-bulk-controls
              >
                <input data-knowledge-checkbox type="checkbox" />
              </label>
              <Link className="knowledge-list-main" href={`/knowledge/${block.id}`}>
                <div className="knowledge-list-meta">
                  <KnowledgeStatus status={block.status} />
                  <span>{block.language ?? "未识别语言"}</span>
                  <span>{formatDate(block.created_at)}</span>
                </div>
                <h2>{block.title}</h2>
                <p>{block.summary ?? "尚未经过 AI 整理，当前仅保存原始资料。"}</p>
              </Link>
              <div className="knowledge-list-actions">
                <button
                  className="danger-icon-button"
                  data-delete-one
                  title="删除知识"
                  type="button"
                >
                  删除
                </button>
                <Link
                  aria-label={`打开 ${block.title}`}
                  className="list-arrow"
                  href={`/knowledge/${block.id}`}
                >
                  ↗
                </Link>
              </div>
            </article>
          ))}
        </div>
    </section>
  );
}
