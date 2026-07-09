"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import {
  Category,
  createCategory,
  deleteCategory,
  KnowledgeApiError,
  updateCategory,
} from "@/lib/knowledge-api";

export function CategoryManager({ categories }: { categories: Category[] }) {
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [busyCategoryId, setBusyCategoryId] = useState<string | null>(null);
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<{
    categoryId: string;
    message: string;
  } | null>(null);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreateError(null);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("name") ?? "").trim();
    if (!name) {
      setCreateError("请输入分类名称。");
      return;
    }

    setCreating(true);
    try {
      await createCategory({
        name,
        description: String(form.get("description") ?? "").trim() || null,
        color: String(form.get("color") ?? "").trim() || null,
      });
      formElement.reset();
      router.refresh();
    } catch (caught) {
      setCreateError(
        caught instanceof KnowledgeApiError ? caught.message : "创建分类失败。",
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdate(
    category: Category,
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    setActionError(null);
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    if (!name) {
      setActionError({ categoryId: category.id, message: "请输入分类名称。" });
      return;
    }

    setBusyCategoryId(category.id);
    try {
      await updateCategory(category.id, {
        name,
        description: String(form.get("description") ?? "").trim() || null,
        color: String(form.get("color") ?? "").trim() || null,
      });
      setEditingCategoryId(null);
      router.refresh();
    } catch (caught) {
      setActionError({
        categoryId: category.id,
        message:
          caught instanceof KnowledgeApiError ? caught.message : "更新分类失败。",
      });
    } finally {
      setBusyCategoryId(null);
    }
  }

  async function handleDelete(category: Category) {
    setActionError(null);
    const confirmed = window.confirm(
      `确认删除“${category.name}”吗？已有知识会移动到未分类。`,
    );
    if (!confirmed) {
      return;
    }

    setBusyCategoryId(category.id);
    try {
      await deleteCategory(category.id);
      if (editingCategoryId === category.id) {
        setEditingCategoryId(null);
      }
      router.refresh();
    } catch (caught) {
      setActionError({
        categoryId: category.id,
        message:
          caught instanceof KnowledgeApiError ? caught.message : "删除分类失败。",
      });
    } finally {
      setBusyCategoryId(null);
    }
  }

  return (
    <div className="category-layout">
      <section className="category-list" aria-label="分类列表">
        {categories.map((category) => (
          <article
            className="category-card"
            key={category.id}
          >
            <span
              className="category-color"
              style={{ backgroundColor: category.color ?? "#8A938D" }}
            />
            {editingCategoryId === category.id ? (
              <form
                className="category-edit-form"
                onSubmit={(event) => handleUpdate(category, event)}
              >
                <label>
                  名称
                  <input
                    defaultValue={category.name}
                    maxLength={100}
                    name="name"
                    required
                  />
                </label>
                <label>
                  描述
                  <textarea
                    defaultValue={category.description ?? ""}
                    name="description"
                    rows={3}
                  />
                </label>
                <label>
                  颜色
                  <input
                    defaultValue={category.color ?? "#176B4D"}
                    name="color"
                    type="color"
                  />
                </label>
                {actionError?.categoryId === category.id ? (
                  <div className="inline-form-error" role="alert">
                    {actionError.message}
                  </div>
                ) : null}
                <div className="category-actions">
                  <button
                    className="button button-small"
                    disabled={busyCategoryId === category.id}
                    type="submit"
                  >
                    {busyCategoryId === category.id ? "保存中…" : "保存"}
                  </button>
                  <button
                    className="secondary-button secondary-button-small"
                    disabled={busyCategoryId === category.id}
                    onClick={() => {
                      setEditingCategoryId(null);
                      setActionError(null);
                    }}
                    type="button"
                  >
                    取消
                  </button>
                </div>
              </form>
            ) : (
              <>
                <div className="category-card-main">
                  <h2>{category.name}</h2>
                  <p>{category.description ?? "没有描述"}</p>
                  {actionError?.categoryId === category.id ? (
                    <div className="inline-form-error" role="alert">
                      {actionError.message}
                    </div>
                  ) : null}
                </div>
                <div className="category-card-side">
                  <span className="category-kind">
                    {category.is_system ? "系统分类" : "自定义"}
                  </span>
                  <Link
                    className="text-link category-view-link"
                    href={`/knowledge?category=${category.id}`}
                  >
                    查看知识
                  </Link>
                  {!category.is_system ? (
                    <div className="category-actions">
                      <button
                        className="secondary-button secondary-button-small"
                        disabled={busyCategoryId === category.id}
                        onClick={() => {
                          setEditingCategoryId(category.id);
                          setActionError(null);
                        }}
                        type="button"
                      >
                        编辑
                      </button>
                      <button
                        className="danger-button danger-button-small"
                        disabled={busyCategoryId === category.id}
                        onClick={() => handleDelete(category)}
                        type="button"
                      >
                        {busyCategoryId === category.id ? "删除中…" : "删除"}
                      </button>
                    </div>
                  ) : null}
                </div>
              </>
            )}
          </article>
        ))}
      </section>

      <form className="category-form" onSubmit={handleCreate}>
        <p className="eyebrow">New category</p>
        <h2>创建分类</h2>
        <label>
          名称
          <input maxLength={100} name="name" required />
        </label>
        <label>
          描述
          <textarea name="description" rows={4} />
        </label>
        <label>
          颜色
          <input defaultValue="#176B4D" name="color" type="color" />
        </label>
        {createError ? (
          <div className="form-error" role="alert">
            {createError}
          </div>
        ) : null}
        <button className="button" disabled={creating} type="submit">
          {creating ? "正在创建…" : "创建分类"}
        </button>
      </form>
    </div>
  );
}
