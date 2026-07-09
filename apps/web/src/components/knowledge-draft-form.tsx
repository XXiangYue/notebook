"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  Category,
  createKnowledgeDraft,
  KnowledgeApiError,
  KnowledgeDraftInput,
  organizeKnowledgeBlock,
  updateKnowledgeDraft,
} from "@/lib/knowledge-api";

type DraftFormProps = {
  categories: Category[];
  blockId?: string;
  initial?: KnowledgeDraftInput;
};

type DraftFormState = {
  title: string;
  language: string;
  topic: string;
  category_id: string;
  raw_text: string;
};

export function KnowledgeDraftForm({
  categories,
  blockId,
  initial,
}: DraftFormProps) {
  const router = useRouter();
  const storageKey = useMemo(
    () => `knowledge-draft-form:${blockId ?? "new"}`,
    [blockId],
  );
  const [formState, setFormState] = useState<DraftFormState>({
    title: initial?.title ?? "",
    language: initial?.language ?? "zh-CN",
    topic: initial?.topic ?? "",
    category_id: initial?.category_id ?? "",
    raw_text: initial?.raw_text ?? "",
  });
  const [storageReady, setStorageReady] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const isEditing = Boolean(blockId);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const saved = window.sessionStorage.getItem(storageKey);
      if (!saved) {
        setStorageReady(true);
        return;
      }

      try {
        const parsed = JSON.parse(saved) as Partial<DraftFormState>;
        setFormState((current) => ({
          ...current,
          ...parsed,
          title: parsed.title ?? current.title,
          language: parsed.language ?? current.language,
          topic: parsed.topic ?? current.topic,
          category_id: parsed.category_id ?? current.category_id,
          raw_text: parsed.raw_text ?? current.raw_text,
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

    const rawText = formState.raw_text;
    if (!rawText.trim()) {
      setError("请输入需要保存的原始内容。");
      return;
    }

    const categoryId = formState.category_id.trim();
    const payload: KnowledgeDraftInput = {
      title: formState.title.trim() || undefined,
      topic: formState.topic.trim() || undefined,
      raw_text: rawText,
      language: formState.language.trim() || undefined,
      category_id: categoryId || null,
    };

    setSubmitting(true);
    try {
      const block =
        isEditing && blockId
          ? await updateKnowledgeDraft(blockId, payload)
          : await createKnowledgeDraft(payload);
      window.sessionStorage.removeItem(storageKey);
      if (!isEditing) {
        setStatusMessage("草稿已保存，正在启动 AI 整理…");
        try {
          const job = await organizeKnowledgeBlock(block.id);
          router.push(`/knowledge/${block.id}?jobId=${job.id}`);
        } catch {
          router.push(`/knowledge/${block.id}?organizeError=1`);
        }
      } else {
        setStatusMessage("新版本已保存，正在打开详情页…");
        router.push(`/knowledge/${block.id}`);
      }
    } catch (caught) {
      if (caught instanceof KnowledgeApiError) {
        setError(caught.message);
      } else {
        setError("无法连接知识库服务，请确认 API 已启动。");
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
            placeholder="可选，未填写时使用主题"
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
            placeholder="例如：整理这组关于混合检索的笔记"
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
        原始内容
        <textarea
          autoFocus={!isEditing}
          name="raw_text"
          onChange={updateField}
          placeholder="粘贴文章片段、聊天记录、想法或其他暂时不想手工整理的内容……"
          required
          rows={16}
          value={formState.raw_text}
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
        <p>
          {isEditing
            ? "保存后会创建新版本，最初输入仍会保留。"
            : "保存后会自动启动 AI 整理，整理结果会在详情页确认入库。"}
        </p>
        <button className="button" disabled={submitting} type="submit">
          {submitting
            ? isEditing
              ? "正在保存…"
              : "正在保存并整理…"
            : isEditing
              ? "保存新版本"
              : "保存并 AI 整理"}
        </button>
      </div>
    </form>
  );
}
