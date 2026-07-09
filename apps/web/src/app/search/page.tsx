import Link from "next/link";

import { searchKnowledge } from "@/lib/knowledge-api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type SearchPageProps = {
  searchParams: Promise<{
    q?: string;
  }>;
};

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const query = (params.q ?? "").trim();
  let result = null;
  let error = false;

  if (query) {
    try {
      result = await searchKnowledge({ query });
    } catch {
      error = true;
    }
  }

  return (
    <main className="page-shell">
      <div className="page-heading compact-heading">
        <div>
          <p className="eyebrow">Full-text search</p>
          <h1>搜索知识库</h1>
          <p className="page-description">
            当前基于已确认知识块的活动分块做 PostgreSQL 全文检索、pgvector 向量召回和 RRF 融合排序。
          </p>
        </div>
      </div>

      <form className="search-form" action="/search">
        <label htmlFor="q">输入问题、关键词或短语</label>
        <div>
          <input
            id="q"
            name="q"
            type="search"
            defaultValue={query}
            placeholder="例如：标题路径、向量索引、混合检索"
          />
          <button className="button" type="submit">
            搜索
          </button>
        </div>
      </form>

      {!query ? (
        <section className="empty-state search-empty">
          <span>FTS</span>
          <h2>输入关键词开始检索</h2>
          <p>只有状态为 searchable 的知识块会出现在搜索结果中。</p>
        </section>
      ) : error ? (
        <section className="error-state search-empty">
          <p className="eyebrow">Service unavailable</p>
          <h1>暂时无法搜索</h1>
          <p>请确认 FastAPI 服务运行在 {API_URL}，然后重试。</p>
        </section>
      ) : result && result.items.length > 0 ? (
        <section className="search-results" aria-label="搜索结果">
          <p className="search-summary">
            找到 {result.total} 个相关分块，按命中分数排序。
          </p>
          {result.items.map((item) => (
            <Link
              className="search-card"
              href={`/knowledge/${item.knowledge_block_id}`}
              key={item.knowledge_chunk_id}
            >
              <div>
                <p className="heading-path">
                  {item.heading_path.length > 0
                    ? item.heading_path.join(" / ")
                    : "无标题路径"}
                </p>
                <h2>{item.title}</h2>
                <p className="search-snippet">{item.snippet}</p>
                {item.summary ? <p className="muted-copy">{item.summary}</p> : null}
              </div>
              <span className="search-score">{item.score.toFixed(2)}</span>
            </Link>
          ))}
        </section>
      ) : (
        <section className="empty-state search-empty">
          <span>0</span>
          <h2>没有找到匹配内容</h2>
          <p>可以换一个更短的关键词，或先确认知识块让它进入 searchable 状态。</p>
        </section>
      )}
    </main>
  );
}
