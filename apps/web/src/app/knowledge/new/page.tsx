import Link from "next/link";

import { KnowledgeDraftForm } from "@/components/knowledge-draft-form";
import { listCategories } from "@/lib/knowledge-api";

export default async function NewKnowledgePage() {
  const categories = await listCategories();

  return (
    <main className="page-shell narrow-shell">
      <Link className="back-link" href="/knowledge">
        ← 返回知识库
      </Link>
      <div className="page-heading compact-heading">
        <div>
          <p className="eyebrow">New knowledge</p>
          <h1>保存一块新知识</h1>
          <p className="page-description">
            先保存原始资料，避免信息丢失。标题和主题都可以稍后补充。
          </p>
        </div>
      </div>
      <KnowledgeDraftForm categories={categories} />
    </main>
  );
}
