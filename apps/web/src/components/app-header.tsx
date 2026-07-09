import Link from "next/link";

export function AppHeader() {
  return (
    <header className="app-header">
      <Link className="brand" href="/knowledge">
        <span className="brand-mark">N</span>
        <span>Notebook</span>
      </Link>
      <nav aria-label="主导航">
        <Link href="/knowledge">知识库</Link>
        <Link href="/search">搜索</Link>
        <Link href="/settings">设置</Link>
        <Link className="button button-small" href="/knowledge/new">
          新增知识
        </Link>
      </nav>
    </header>
  );
}
