"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import {
  Category,
  confirmKnowledgeBlock,
  KnowledgeApiError,
} from "@/lib/knowledge-api";

type ConfirmAiResultFormProps = {
  blockId: string;
  categories: Category[];
  initialTitle: string;
  initialSummary: string;
  initialMarkdown: string;
  initialCategoryId: string | null;
};

export function ConfirmAiResultForm({
  blockId,
  categories,
  initialTitle,
  initialSummary,
  initialMarkdown,
  initialCategoryId,
}: ConfirmAiResultFormProps) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") ?? "").trim();
    const markdown = String(form.get("markdown_content") ?? "").trim();
    const summary = String(form.get("summary") ?? "").trim();
    const categoryId = String(form.get("category_id") ?? "").trim();

    if (!title || !markdown) {
      setError("标题和 Markdown 正文不能为空。");
      return;
    }

    setSubmitting(true);
    try {
      await confirmKnowledgeBlock(blockId, {
        title,
        summary: summary || null,
        markdown_content: markdown,
        category_id: categoryId || null,
      });
      router.refresh();
    } catch (caught) {
      if (caught instanceof KnowledgeApiError) {
        setError(caught.message);
      } else {
        setError("确认失败，请稍后重试。");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      className="confirm-form"
      data-block-id={blockId}
      data-confirm-ai-form
      onSubmit={handleSubmit}
    >
      <div className="form-row">
        <label>
          标题
          <input defaultValue={initialTitle} maxLength={300} name="title" />
        </label>
        <label>
          主分类
          <select defaultValue={initialCategoryId ?? ""} name="category_id">
            <option value="">未选择</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label>
        摘要
        <textarea defaultValue={initialSummary} name="summary" rows={4} />
      </label>

      <label>
        Markdown 正文
        <textarea
          defaultValue={initialMarkdown}
          name="markdown_content"
          required
          rows={18}
        />
      </label>

      {error ? (
        <div className="form-error" role="alert">
          {error}
        </div>
      ) : null}

      <div className="form-actions">
        <p>确认后会生成正式版本，并立即作为知识库检索的分块和索引输入。</p>
        <button className="button" disabled={submitting} type="submit">
          {submitting ? "正在入库…" : "确认并入库"}
        </button>
      </div>
    </form>
  );
}
