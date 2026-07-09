"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { KnowledgeStatus } from "@/components/knowledge-status";
import {
  deleteKnowledgeBlock,
  KnowledgeApiError,
  purgeKnowledgeBlock,
  restoreKnowledgeBlock,
  type Category,
  type KnowledgeBlockSummary,
} from "@/lib/knowledge-api";

type PanelView = "default" | "deleted";

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "未知时间";
  }
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(
    new Date(value),
  );
}

export function KnowledgeListPanel({
  blocks,
  categories,
  view = "default",
}: {
  blocks: KnowledgeBlockSummary[];
  categories: Category[];
  view?: PanelView;
}) {
  const router = useRouter();
  const [bulkMode, setBulkMode] = useState(false);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [removedIds, setRemovedIds] = useState<ReadonlySet<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categoryById = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );
  const items = blocks.filter((block) => !removedIds.has(block.id));
  const selectedItems = items.filter((block) => selected.has(block.id));
  const allSelected = items.length > 0 && selectedItems.length === items.length;

  function toggleSelected(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function exitBulkMode() {
    setBulkMode(false);
    setSelected(new Set());
    setError(null);
  }

  function confirmLabel(targets: KnowledgeBlockSummary[]) {
    const names = targets.map((block) => block.title || "未命名知识");
    return names.length <= 3
      ? names.join("、")
      : `${names.slice(0, 3).join("、")} 等 ${names.length} 条`;
  }

  async function runAction(
    targets: KnowledgeBlockSummary[],
    action: (id: string) => Promise<void>,
    failureMessage: string,
  ) {
    setBusy(true);
    setError(null);
    const done: string[] = [];
    try {
      for (const block of targets) {
        await action(block.id);
        done.push(block.id);
      }
    } catch (caught) {
      setError(
        caught instanceof KnowledgeApiError ? caught.message : failureMessage,
      );
    } finally {
      if (done.length > 0) {
        setRemovedIds((current) => new Set([...current, ...done]));
        setSelected((current) => {
          const next = new Set(current);
          for (const id of done) {
            next.delete(id);
          }
          return next;
        });
        router.refresh();
      }
      setBusy(false);
    }
  }

  async function handleDelete(targets: KnowledgeBlockSummary[]) {
    if (targets.length === 0) return;
    if (
      !window.confirm(
        `确认删除 ${confirmLabel(targets)} 吗？删除后会移入“最近删除”。`,
      )
    ) {
      return;
    }
    await runAction(targets, deleteKnowledgeBlock, "删除失败，请稍后重试。");
  }

  async function handleRestore(targets: KnowledgeBlockSummary[]) {
    if (targets.length === 0) return;
    await runAction(targets, restoreKnowledgeBlock, "恢复失败，请稍后重试。");
  }

  async function handlePurge(targets: KnowledgeBlockSummary[]) {
    if (targets.length === 0) return;
    if (
      !window.confirm(
        `确认彻底清除 ${confirmLabel(targets)} 吗？这个操作不能撤销。`,
      )
    ) {
      return;
    }
    await runAction(targets, purgeKnowledgeBlock, "彻底清除失败，请稍后重试。");
  }

  return (
    <section className="knowledge-list-panel" aria-label="知识块列表">
      <div className="knowledge-list-toolbar">
        {bulkMode ? (
          <>
            <div className="knowledge-list-bulk-actions">
              <button
                className="secondary-button secondary-button-small"
                disabled={busy || items.length === 0}
                onClick={() =>
                  setSelected(
                    allSelected
                      ? new Set()
                      : new Set(items.map((block) => block.id)),
                  )
                }
                type="button"
              >
                {allSelected ? "取消全选" : "全选"}
              </button>
              <span>
                {selectedItems.length > 0
                  ? `已选择 ${selectedItems.length} 条`
                  : "未选择知识"}
              </span>
            </div>
            <div className="knowledge-list-bulk-actions">
              {view === "default" ? (
                <button
                  className="danger-button danger-button-small"
                  disabled={busy || selectedItems.length === 0}
                  onClick={() => handleDelete(selectedItems)}
                  type="button"
                >
                  删除已选
                </button>
              ) : (
                <>
                  <button
                    className="secondary-button secondary-button-small"
                    disabled={busy || selectedItems.length === 0}
                    onClick={() => handleRestore(selectedItems)}
                    type="button"
                  >
                    恢复已选
                  </button>
                  <button
                    className="danger-button danger-button-small"
                    disabled={busy || selectedItems.length === 0}
                    onClick={() => handlePurge(selectedItems)}
                    type="button"
                  >
                    彻底清除
                  </button>
                </>
              )}
              <button
                className="secondary-button secondary-button-small"
                disabled={busy}
                onClick={exitBulkMode}
                type="button"
              >
                完成
              </button>
            </div>
          </>
        ) : (
          <>
            <span className="knowledge-list-count">{items.length} 条知识</span>
            <button
              className="secondary-button secondary-button-small"
              disabled={items.length === 0}
              onClick={() => setBulkMode(true)}
              type="button"
            >
              批量选择
            </button>
          </>
        )}
      </div>

      {error ? (
        <p className="list-error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="knowledge-list">
        {items.map((block) => {
          const category = block.category_id
            ? categoryById.get(block.category_id)
            : undefined;
          const body = (
            <>
              <div className="knowledge-row-line">
                <h2>{block.title}</h2>
                <span className="knowledge-row-meta">
                  <KnowledgeStatus
                    status={view === "deleted" ? "deleted" : block.status}
                  />
                  {category ? (
                    <span className="knowledge-row-category">
                      <i
                        style={{ background: category.color ?? "var(--accent)" }}
                      />
                      {category.name}
                    </span>
                  ) : null}
                  <span>
                    {view === "deleted"
                      ? `删除于 ${formatDate(block.deleted_at)}`
                      : formatDate(block.updated_at)}
                  </span>
                </span>
              </div>
              <p className="knowledge-row-summary">
                {block.summary ?? "尚未经过 AI 整理，当前仅保存原始资料。"}
              </p>
            </>
          );

          return (
            <article
              className="knowledge-row"
              data-selected={selected.has(block.id)}
              key={block.id}
            >
              {bulkMode ? (
                <label
                  className="knowledge-select-control"
                  aria-label={`选择 ${block.title}`}
                >
                  <input
                    checked={selected.has(block.id)}
                    onChange={() => toggleSelected(block.id)}
                    type="checkbox"
                  />
                </label>
              ) : null}
              {view === "deleted" ? (
                <div className="knowledge-row-main">{body}</div>
              ) : (
                <Link
                  className="knowledge-row-main"
                  href={`/knowledge/${block.id}`}
                >
                  {body}
                </Link>
              )}
              {!bulkMode ? (
                <div className="knowledge-row-actions">
                  {view === "default" ? (
                    <button
                      className="danger-icon-button"
                      disabled={busy}
                      onClick={() => handleDelete([block])}
                      type="button"
                    >
                      删除
                    </button>
                  ) : (
                    <>
                      <button
                        className="secondary-button secondary-button-small"
                        disabled={busy}
                        onClick={() => handleRestore([block])}
                        type="button"
                      >
                        恢复
                      </button>
                      <button
                        className="danger-icon-button"
                        disabled={busy}
                        onClick={() => handlePurge([block])}
                        type="button"
                      >
                        清除
                      </button>
                    </>
                  )}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
