"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  Category,
  KnowledgeApiError,
  KnowledgeBlockUpdateInput,
  updateKnowledgeBlock,
} from "@/lib/knowledge-api";

type KnowledgeEditFormProps = {
  blockId: string;
  categories: Category[];
  initial: {
    title: string;
    topic?: string | null;
    summary?: string | null;
    content: string;
    contentKind: "markdown" | "raw";
    language?: string | null;
    category_id?: string | null;
  };
};

type KnowledgeEditFormState = {
  title: string;
  language: string;
  topic: string;
  category_id: string;
  summary: string;
  content: string;
};

export function KnowledgeEditForm({
  blockId,
  categories,
  initial,
}: KnowledgeEditFormProps) {
  const router = useRouter();
  const storageKey = useMemo(() => `knowledge-edit-form:${blockId}`, [blockId]);
  const [formState, setFormState] = useState<KnowledgeEditFormState>({
    title: initial.title,
    language: initial.language ?? "zh-CN",
    topic: initial.topic ?? "",
    category_id: initial.category_id ?? "",
    summary: initial.summary ?? "",
    content: initial.content,
  });
  const [storageReady, setStorageReady] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const contentLabel =
    initial.contentKind === "markdown" ? "Markdown 内容" : "原始内容";

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const saved = window.sessionStorage.getItem(storageKey);
      if (!saved) {
        setStorageReady(true);
        return;
      }

      try {
        const parsed = JSON.parse(saved) as Partial<KnowledgeEditFormState>;
        setFormState((current) => ({
          ...current,
          title: parsed.title ?? current.title,
          language: parsed.language ?? current.language,
          topic: parsed.topic ?? current.topic,
          category_id: parsed.category_id ?? current.category_id,
          summary: parsed.summary ?? current.summary,
          content: parsed.content ?? current.content,
        }));
      } catch {
        window.sessionStorage.removeItem(storageKey);
      } finally {
        setStorageReady(true);
      }
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
  }, [storageKey]);

  useEffect(() => {
    if (!storageReady) return;
    window.sessionStorage.setItem(storageKey, JSON.stringify(formState));
  }, [formState, storageKey, storageReady]);

  function updateField(
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) {
    const { name, value } = event.target;
    setFormState((current) => ({ ...current, [name]: value }));
    setStatusMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setStatusMessage(null);

    const content = formState.content.trim();
    if (!content) {
      setError(`请输入${contentLabel}。`);
      return;
    }

    const categoryId = formState.category_id.trim();
    const payload: KnowledgeBlockUpdateInput = {
      title: formState.title.trim() || undefined,
      topic: formState.topic.trim() || null,
      summary: formState.summary.trim() || null,
      language: formState.language.trim() || null,
      category_id: categoryId || null,
      ...(initial.contentKind === "markdown"
        ? { markdown_content: content }
        : { raw_text: content }),
    };

    setSubmitting(true);
    try {
      const block = await updateKnowledgeBlock(blockId, payload);
      window.sessionStorage.removeItem(storageKey);
      setStatusMessage("新版本已保存，正在返回知识详情…");
      router.push(`/knowledge/${block.id}`);
    } catch (caught) {
      if (caught instanceof KnowledgeApiError) {
        setError(caught.message);
      } else {
        setError("保存失败，请确认 API 已启动。");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="knowledge-form" onSubmit={handleSubmit}>
      <div className="form-row">
        <label>
          标题
          <input
            maxLength={300}
            name="title"
            onChange={updateField}
            value={formState.title}
          />
        </label>
        <label>
          语言
          <select
            name="language"
            onChange={updateField}
            value={formState.language}
          >
            <option value="zh-CN">中文</option>
            <option value="en">English</option>
            <option value="">自动识别</option>
          </select>
        </label>
      </div>

      <div className="form-row">
        <label>
          主题或整理要求
          <input
            maxLength={500}
            name="topic"
            onChange={updateField}
            value={formState.topic}
          />
        </label>
        <label>
          主分类
          <select
            name="category_id"
            onChange={updateField}
            value={formState.category_id}
          >
            <option value="">未分类</option>
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
        <textarea
          name="summary"
          onChange={updateField}
          rows={4}
          value={formState.summary}
        />
      </label>

      <label>
        {contentLabel}
        <textarea
          name="content"
          onChange={updateField}
          required
          rows={18}
          value={formState.content}
        />
      </label>

      {error ? (
        <div className="form-error" role="alert">
          {error}
        </div>
      ) : null}
      {statusMessage ? (
        <div className="form-status" role="status">
          {statusMessage}
        </div>
      ) : null}

      <div className="form-actions">
        <p>保存后会创建新的用户编辑版本，并保留此前版本。</p>
        <button className="button" disabled={submitting} type="submit">
          {submitting ? "正在保存…" : "保存新版本"}
        </button>
      </div>
    </form>
  );
}
