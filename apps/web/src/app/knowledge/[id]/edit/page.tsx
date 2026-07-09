import Link from "next/link";
import { notFound } from "next/navigation";

import { KnowledgeEditForm } from "@/components/knowledge-edit-form";
import {
  getKnowledgeBlock,
  KnowledgeApiError,
  listCategories,
} from "@/lib/knowledge-api";

export default async function EditKnowledgePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

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
  const current =
    block.versions.find((version) => version.id === block.current_version_id) ??
    block.versions.at(-1);

  return (
    <main className="page-shell narrow-shell">
      <Link className="back-link" href={`/knowledge/${block.id}`}>
        ← 返回知识详情
      </Link>
      <div className="page-heading compact-heading">
        <div>
          <p className="eyebrow">Edit draft</p>
          <h1>编辑知识块</h1>
          <p className="page-description">
            保存后新增一个编辑版本，不覆盖此前内容。
          </p>
        </div>
      </div>
      <KnowledgeEditForm
        blockId={block.id}
        categories={categories}
        initial={{
          title: block.title,
          topic: current?.topic_instruction ?? undefined,
          summary: block.summary,
          content: current?.markdown_content ?? current?.raw_text ?? "",
          contentKind: current?.markdown_content ? "markdown" : "raw",
          language: block.language ?? undefined,
          category_id: block.category_id,
        }}
      />
    </main>
  );
}
