"use client";

import Link from "next/link";

export default function KnowledgeDetailError() {
  return (
    <main className="page-shell">
      <section className="error-state">
        <p className="eyebrow">Unable to load</p>
        <h1>无法读取这条知识</h1>
        <p>API 服务可能暂时不可用，请稍后重试。</p>
        <Link className="text-link" href="/knowledge">
          返回知识库 →
        </Link>
      </section>
    </main>
  );
}

