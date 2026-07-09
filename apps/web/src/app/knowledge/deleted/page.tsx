import Link from "next/link";

import { DeletedKnowledgeListView } from "@/components/deleted-knowledge-list-view";
import { listDeletedKnowledgeBlocks } from "@/lib/knowledge-api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default async function DeletedKnowledgePage() {
  let result;
  try {
    result = await listDeletedKnowledgeBlocks();
  } catch {
    return (
      <main className="page-shell">
        <section className="error-state">
          <p className="eyebrow">Service unavailable</p>
          <h1>暂时无法读取最近删除</h1>
          <p>请确认 FastAPI 服务运行在 {API_URL}，然后刷新页面。</p>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <Link className="back-link" href="/knowledge">
        ← 返回知识库
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Recently deleted</p>
          <h1>最近删除</h1>
          <p className="page-description">
            这里显示已软删除的知识块。可以恢复到知识库，或彻底清除数据库记录。
          </p>
        </div>
      </div>

      {result.items.length === 0 ? (
        <section className="empty-state">
          <span>00</span>
          <h2>最近删除为空</h2>
          <p>删除后的知识块会先出现在这里。</p>
        </section>
      ) : (
        <DeletedKnowledgeListView blocks={result.items} />
      )}
    </main>
  );
}
