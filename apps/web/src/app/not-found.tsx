import Link from "next/link";

export default function NotFound() {
  return (
    <main className="page-shell">
      <section className="error-state">
        <p className="eyebrow">404</p>
        <h1>没有找到这条知识</h1>
        <p>它可能不存在、已被删除，或者链接不完整。</p>
        <Link className="text-link" href="/knowledge">
          返回知识库 →
        </Link>
      </section>
    </main>
  );
}

