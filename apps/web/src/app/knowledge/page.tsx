import Link from "next/link";

import { KnowledgeBlockListView } from "@/components/knowledge-block-list-view";
import { listCategories, listKnowledgeBlocks } from "@/lib/knowledge-api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default async function KnowledgePage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string }>;
}) {
  const { category: selectedCategory } = await searchParams;
  let result;
  let categories;
  try {
    [result, categories] = await Promise.all([
      listKnowledgeBlocks(
        selectedCategory
          ? {
              category_id:
                selectedCategory === "uncategorized" ? null : selectedCategory,
              uncategorized: selectedCategory === "uncategorized",
            }
          : undefined,
      ),
      listCategories(),
    ]);
  } catch {
    return (
      <main className="page-shell">
        <section className="error-state">
          <p className="eyebrow">Service unavailable</p>
          <h1>暂时无法读取知识库</h1>
          <p>请确认 FastAPI 服务运行在 {API_URL}，然后刷新页面。</p>
        </section>
      </main>
    );
  }
  const selectedCategoryInfo =
    selectedCategory && selectedCategory !== "uncategorized"
      ? categories.find((category) => category.id === selectedCategory)
      : null;
  const pageTitle = selectedCategory
    ? selectedCategory === "uncategorized"
      ? "未分类"
      : (selectedCategoryInfo?.name ?? "未知分类")
    : "知识库";
  const pageDescription = selectedCategory
    ? `当前分类下共有 ${result.total} 个知识块。`
    : `当前共保存 ${result.total} 个知识块。可以直接查看最近保存，也可以按分类进入。`;

  if (!selectedCategory) {
    const categoryCards = categories.map((category) => ({
      id: category.id,
      name: category.name,
      description: category.description,
      color: category.color,
      count: result.items.filter((block) => block.category_id === category.id).length,
      href: `/knowledge?category=${category.id}`,
    }));
    const uncategorizedCount = result.items.filter(
      (block) => block.category_id === null,
    ).length;

    return (
      <main className="page-shell">
        <div className="page-heading">
          <div>
            <p className="eyebrow">Knowledge library</p>
            <h1>知识库</h1>
            <p className="page-description">{pageDescription}</p>
          </div>
          <div className="page-heading-actions">
            <Link className="secondary-button" href="/knowledge/pending">
              待整理入库
            </Link>
            <Link className="button" href="/knowledge/new">
              新增知识
            </Link>
          </div>
        </div>

        <section className="category-browser" aria-label="知识分类">
          {categoryCards.map((category) => (
            <Link className="category-entry" href={category.href} key={category.id}>
              <span
                className="category-entry-color"
                style={{ background: category.color ?? "var(--accent)" }}
              />
              <div>
                <h2>{category.name}</h2>
                <p>{category.description ?? "查看这个分类下的知识块。"}</p>
              </div>
              <strong>{category.count}</strong>
            </Link>
          ))}
          <Link className="category-entry" href="/knowledge?category=uncategorized">
            <span className="category-entry-color uncategorized-color" />
            <div>
              <h2>未分类</h2>
              <p>还没有设置主分类的知识块统一放在这里。</p>
            </div>
            <strong>{uncategorizedCount}</strong>
          </Link>
        </section>

        {result.items.length === 0 ? (
          <section className="empty-state home-empty-state">
            <span>01</span>
            <h2>还没有保存任何知识</h2>
            <p>点击“新增知识”保存第一条草稿，保存后会进入详情页继续 AI 整理。</p>
            <Link className="text-link" href="/knowledge/new">
              创建知识 →
            </Link>
          </section>
        ) : (
          <section className="home-recent-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Recent knowledge</p>
                <h2>最近保存</h2>
              </div>
              <span>最新 {result.items.length} 条</span>
            </div>
            <KnowledgeBlockListView blocks={result.items} title="最近保存" />
          </section>
        )}
      </main>
    );
  }

  return (
    <main className="page-shell">
      <Link className="back-link" href="/knowledge">
        ← 返回分类
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Knowledge category</p>
          <h1>{pageTitle}</h1>
          <p className="page-description">{pageDescription}</p>
        </div>
        <div className="page-heading-actions">
          <Link className="secondary-button" href="/knowledge/pending">
            待整理入库
          </Link>
          <Link className="button" href="/knowledge/new">
            新增知识
          </Link>
        </div>
      </div>

      {result.items.length === 0 ? (
        <section className="empty-state">
          <span>01</span>
          <h2>这个分类还没有知识块</h2>
          <p>可以新建知识，或在知识详情里把已有知识移动到这里。</p>
          <Link className="text-link" href="/knowledge/new">
            创建知识 →
          </Link>
        </section>
      ) : (
        <KnowledgeBlockListView blocks={result.items} title={pageTitle} />
      )}
    </main>
  );
}
