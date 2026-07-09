"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import {
  Category,
  KnowledgeApiError,
  updateKnowledgeBlock,
} from "@/lib/knowledge-api";

type KnowledgeCategoryFormProps = {
  blockId: string;
  categories: Category[];
  initialCategoryId: string | null;
};

export function KnowledgeCategoryForm({
  blockId,
  categories,
  initialCategoryId,
}: KnowledgeCategoryFormProps) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const form = new FormData(event.currentTarget);
    const categoryId = String(form.get("category_id") ?? "").trim();

    setSubmitting(true);
    try {
      await updateKnowledgeBlock(blockId, {
        category_id: categoryId || null,
      });
      router.refresh();
    } catch (caught) {
      if (caught instanceof KnowledgeApiError) {
        setError(caught.message);
      } else {
        setError("分类保存失败，请稍后重试。");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="inline-category-form" onSubmit={handleSubmit}>
      <label>
        重新设定分类
        <select defaultValue={initialCategoryId ?? ""} name="category_id">
          <option value="">未分类</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
      </label>
      <button className="secondary-button button-small" disabled={submitting} type="submit">
        {submitting ? "保存中…" : "保存分类"}
      </button>
      {error ? (
        <span className="inline-form-error" role="alert">
          {error}
        </span>
      ) : null}
    </form>
  );
}
