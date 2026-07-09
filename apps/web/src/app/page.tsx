import Link from "next/link";

const milestones = [
  {
    title: "采集",
    description: "保存原始文本和附件，再交给 AI 整理，任何模型失败都不会丢失输入。",
  },
  {
    title: "检索",
    description: "结合关键词、向量和结构化过滤，返回可定位的知识片段。",
  },
  {
    title: "回答",
    description: "只依据检索证据生成答案，并为关键结论提供可追溯引用。",
  },
];

export default function Home() {
  return (
    <main>
      <div className="eyebrow">Notebook MVP</div>
      <h1>把碎片知识变成可以重新找到的资料。</h1>
      <p className="lede">
        保存还没来得及整理的资料，保留原文与版本，再逐步接入 AI
        整理、混合检索和可追溯问答。
      </p>
      <div className="hero-actions">
        <Link className="button" href="/knowledge/new">
          保存第一块知识
        </Link>
        <Link className="text-link" href="/knowledge">
          查看知识库 →
        </Link>
      </div>
      <section className="grid" aria-label="核心能力">
        {milestones.map((milestone) => (
          <article className="card" key={milestone.title}>
            <strong>{milestone.title}</strong>
            <p>{milestone.description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
