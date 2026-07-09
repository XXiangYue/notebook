import Link from "next/link";

import { KnowledgeBlockListView } from "@/components/knowledge-block-list-view";
import { listKnowledgeBlocks } from "@/lib/knowledge-api";
import type {
  KnowledgeBlockList,
  KnowledgeBlockStatus,
} from "@/lib/knowledge-api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type PendingBucket = {
  id: string;
  title: string;
  eyebrow: string;
  description: string;
  emptyTitle: string;
  emptyDescription: string;
  status: KnowledgeBlockStatus;
};

const pendingBuckets: PendingBucket[] = [
  {
    id: "drafts",
    title: "草稿",
    eyebrow: "Saved drafts",
    description: "已保存原始内容，等待补充附件或启动 AI 整理。",
    emptyTitle: "没有草稿",
    emptyDescription: "保存但尚未进入整理流程的知识会显示在这里。",
    status: "draft",
  },
  {
    id: "organizing",
    title: "AI 整理中",
    eyebrow: "AI organizing",
    description: "后台异步整理任务已经启动，完成后会进入待确认入库。",
    emptyTitle: "没有正在整理的知识",
    emptyDescription: "异步整理中的知识会显示在这里，可打开详情查看任务状态。",
    status: "organizing",
  },
  {
    id: "pending-confirmation",
    title: "待确认入库",
    eyebrow: "Ready to confirm",
    description: "AI 整理结果已生成，打开详情即可编辑并确认写入知识库。",
    emptyTitle: "没有待确认的整理结果",
    emptyDescription: "AI 生成结果完成后，会先停在这里等待你检查和确认。",
    status: "pending_confirmation",
  },
];

export default async function PendingKnowledgePage() {
  let results: KnowledgeBlockList[];
  try {
    results = await Promise.all(
      pendingBuckets.map((bucket) =>
        listKnowledgeBlocks({ statuses: [bucket.status] }),
      ),
    );
  } catch {
    return (
      <main className="page-shell">
        <section className="error-state">
          <p className="eyebrow">Service unavailable</p>
          <h1>暂时无法读取待整理入库列表</h1>
          <p>请确认 FastAPI 服务运行在 {API_URL}，然后刷新页面。</p>
        </section>
      </main>
    );
  }

  const total = results.reduce((count, result) => count + result.total, 0);

  return (
    <main className="page-shell">
      <Link className="back-link" href="/knowledge">
        ← 返回知识库
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Pending knowledge</p>
          <h1>待整理入库</h1>
          <p className="page-description">
            这里集中查看已保存草稿、AI 后台整理中、以及 AI 结果已生成但还没确认入库的知识。当前共有{" "}
            {total} 条待处理知识。
          </p>
        </div>
        <div className="page-heading-actions">
          <Link className="secondary-button" href="/knowledge">
            查看知识库
          </Link>
          <Link className="button" href="/knowledge/new">
            新增知识
          </Link>
        </div>
      </div>

      <section className="pending-summary-grid" aria-label="待处理状态概览">
        {pendingBuckets.map((bucket, index) => (
          <Link
            className="pending-summary-card"
            href={`/knowledge/pending#${bucket.id}`}
            key={bucket.id}
          >
            <span>{bucket.title}</span>
            <strong>{results[index].total}</strong>
          </Link>
        ))}
      </section>

      <div className="pending-buckets">
        {pendingBuckets.map((bucket, index) => {
          const result = results[index];
          return (
            <section className="pending-bucket" id={bucket.id} key={bucket.id}>
              <div className="section-heading pending-section-heading">
                <div>
                  <p className="eyebrow">{bucket.eyebrow}</p>
                  <h2>{bucket.title}</h2>
                  <p>{bucket.description}</p>
                </div>
                <span>{result.total} 条</span>
              </div>

              {result.items.length === 0 ? (
                <div className="pending-empty">
                  <h3>{bucket.emptyTitle}</h3>
                  <p>{bucket.emptyDescription}</p>
                </div>
              ) : (
                <KnowledgeBlockListView blocks={result.items} title={bucket.title} />
              )}
            </section>
          );
        })}
      </div>
    </main>
  );
}
