import type { KnowledgeBlockSummary } from "@/lib/knowledge-api";

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "未知时间";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function DeletedKnowledgeListView({
  blocks,
}: {
  blocks: KnowledgeBlockSummary[];
}) {
  return (
    <section
      className="knowledge-list-panel deleted-list-panel"
      aria-label="最近删除的知识块列表"
      data-deleted-panel
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
            className="secondary-button secondary-button-small"
            data-restore-selected
            disabled
            type="button"
          >
            恢复已选
          </button>
          <button
            className="danger-button danger-button-small"
            data-purge-selected
            disabled
            type="button"
          >
            彻底清除
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
            <div className="knowledge-list-main">
              <div className="knowledge-list-meta">
                <span className="status status-deleted">已删除</span>
                <span>{block.language ?? "未识别语言"}</span>
                <span>删除于 {formatDate(block.deleted_at)}</span>
              </div>
              <h2>{block.title}</h2>
              <p>{block.summary ?? "没有摘要。"}</p>
            </div>
            <div className="knowledge-list-actions">
              <button
                className="secondary-button secondary-button-small"
                data-restore-one
                type="button"
              >
                恢复
              </button>
              <button
                className="danger-icon-button"
                data-purge-one
                title="彻底清除知识"
                type="button"
              >
                清除
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
