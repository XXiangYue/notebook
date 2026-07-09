import Link from "next/link";
import { notFound } from "next/navigation";

import { ConfirmAiResultForm } from "@/components/confirm-ai-result-form";
import { DeleteKnowledgeButton } from "@/components/delete-knowledge-button";
import { KnowledgeCategoryForm } from "@/components/knowledge-category-form";
import { KnowledgeContentViewer } from "@/components/knowledge-content-viewer";
import { KnowledgeIngestionActions } from "@/components/knowledge-ingestion-actions";
import { KnowledgeStatus } from "@/components/knowledge-status";
import { OrganizeJobWatcher } from "@/components/organize-job-watcher";
import {
  getKnowledgeBlock,
  KnowledgeApiError,
  listCategories,
} from "@/lib/knowledge-api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

export default async function KnowledgeDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams?: Promise<{ jobId?: string; organizeError?: string }>;
}) {
  const { id } = await params;
  const query = (await searchParams) ?? {};

  let block;
  try {
    block = await getKnowledgeBlock(id);
  } catch (error) {
    if (error instanceof KnowledgeApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
  const categories = await listCategories();
  const category = categories.find((item) => item.id === block.category_id);

  const current =
    block.versions.find((version) => version.id === block.current_version_id) ??
    block.versions
      .filter((version) => version.version_type !== "ai_generated")
      .at(-1);
  const generated = block.versions
    .filter((version) => version.version_type === "ai_generated")
    .at(-1);
  const currentContent =
    current?.markdown_content ?? current?.raw_text ?? "没有可展示的内容。";
  const activeChunks = block.chunks.filter((chunk) => chunk.is_active);
  const isIngestionReady = [
    "draft",
    "organizing",
    "pending_confirmation",
  ].includes(block.status);
  const isPendingConfirmation = block.status === "pending_confirmation";

  return (
    <main className="page-shell narrow-shell">
      <Link className="back-link" href="/knowledge">
        ← 返回知识库
      </Link>

      <article className="knowledge-detail">
        <header className="detail-header">
          <div className="knowledge-list-meta">
            <KnowledgeStatus status={block.status} />
            <span>{block.language ?? "未识别语言"}</span>
            <span>{formatDate(block.created_at)}</span>
          </div>
          <h1>{block.title}</h1>
          {current?.topic_instruction ? (
            <p className="detail-topic">{current.topic_instruction}</p>
          ) : null}
          <div className="detail-actions">
            <Link className="button" href={`/knowledge/${block.id}/edit`}>
              编辑内容
            </Link>
            <DeleteKnowledgeButton blockId={block.id} />
          </div>
        </header>

        {isIngestionReady ? (
          <section className="content-section workflow-section">
            <div className="workflow-panel">
              {query.organizeError === "1" && block.status === "draft" ? (
                <div className="form-error" role="alert">
                  草稿已保存，但 AI 整理没有启动成功。可以点击下方“AI 整理”重试。
                </div>
              ) : null}
              {query.jobId && !isPendingConfirmation ? (
                <OrganizeJobWatcher jobId={query.jobId} />
              ) : null}
              <div className="workflow-copy">
                <p className="eyebrow">Next steps</p>
                <h2>
                  {isPendingConfirmation
                    ? "确认整理结果并入库"
                    : block.status === "organizing"
                      ? "AI 正在整理"
                    : "继续整理这块知识"}
                </h2>
                <p>
                  {isPendingConfirmation
                    ? "AI 已生成整理结果。检查下方标题、摘要和 Markdown 正文，确认后会写入知识库并生成可搜索的分块索引。"
                    : block.status === "organizing"
                      ? "整理任务正在运行，完成后页面会自动刷新并显示确认表单。"
                    : "草稿已经保留在系统中。补充附件后点击 AI 整理，生成结果会在本页下方出现。"}
                </p>
              </div>
              <ol className="workflow-steps">
                <li data-active={block.status === "draft"}>
                  保存原始草稿
                </li>
                <li data-active={block.status === "organizing"}>
                  AI 整理内容
                </li>
                <li data-active={isPendingConfirmation}>
                  确认并入库
                </li>
              </ol>
              <KnowledgeIngestionActions
                blockId={block.id}
                canIngest={
                  block.status === "draft" || block.status === "pending_confirmation"
                }
                organizing={block.status === "organizing"}
              />
            </div>
          </section>
        ) : null}

        {generated?.markdown_content && block.status === "pending_confirmation" ? (
          <section
            className="content-section generated-section"
            id="confirm-ai-result"
          >
            <div className="section-heading">
              <div>
                <p className="eyebrow">AI generated</p>
                <h2>编辑并确认整理结果</h2>
              </div>
              <span>版本 {generated.version_number}</span>
            </div>
            <ConfirmAiResultForm
              blockId={block.id}
              categories={categories}
              initialCategoryId={block.category_id}
              initialMarkdown={generated.markdown_content}
              initialSummary={block.summary ?? ""}
              initialTitle={block.title}
            />
          </section>
        ) : null}

        <section className="content-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Original content</p>
              <h2>当前内容</h2>
            </div>
            <span>版本 {current?.version_number ?? 1}</span>
          </div>
          <KnowledgeContentViewer
            content={currentContent}
            markdownContent={current?.markdown_content ?? null}
          />
        </section>

        <section className="content-section compact-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Category</p>
              <h2>分类</h2>
            </div>
            <span>{category?.name ?? "未分类"}</span>
          </div>
          <KnowledgeCategoryForm
            blockId={block.id}
            categories={categories}
            initialCategoryId={block.category_id}
          />
        </section>

        <section className="content-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Attachments</p>
              <h2>附件</h2>
            </div>
            <span>{block.attachments.length} 个</span>
          </div>
          {block.attachments.length ? (
            <div className="attachment-list">
              {block.attachments.map((attachment) => (
                <div className="attachment-item" key={attachment.id}>
                  <div>
                    <strong>{attachment.original_filename}</strong>
                    <span>{attachment.media_type}</span>
                  </div>
                  <span>
                    {(attachment.size_bytes / 1024).toFixed(1)} KB ·{" "}
                    {attachment.processing_status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted-copy">还没有附件，可上传图片、文本、Markdown 或 PDF。</p>
          )}
        </section>

        <section className="detail-metadata">
          <div>
            <span>来源</span>
            <strong>
              {block.source_type === "manual" ? "手动输入" : block.source_type}
            </strong>
          </div>
          <div>
            <span>主分类</span>
            <strong>{category?.name ?? "未选择"}</strong>
          </div>
          <div className="hash-field">
            <span>内容哈希</span>
            <code>{current?.content_hash ?? "—"}</code>
          </div>
          <div>
            <span>活动分块</span>
            <strong>{activeChunks.length} 个</strong>
          </div>
        </section>
        <p className="version-note">共保留 {block.versions.length} 个内容版本。</p>
      </article>
    </main>
  );
}
