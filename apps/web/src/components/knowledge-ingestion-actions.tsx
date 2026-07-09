"use client";

import { ChangeEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  getIngestionJob,
  KnowledgeApiError,
  organizeKnowledgeBlock,
  uploadAttachment,
} from "@/lib/knowledge-api";

export function KnowledgeIngestionActions({
  blockId,
  canIngest,
  organizing,
}: {
  blockId: string;
  canIngest: boolean;
  organizing: boolean;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setMessage("正在上传附件…");
    try {
      await uploadAttachment(blockId, file);
      setMessage("附件已保存。");
      router.refresh();
    } catch (error) {
      setMessage(
        error instanceof KnowledgeApiError ? error.message : "附件上传失败。",
      );
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function handleOrganize() {
    setBusy(true);
    setMessage("整理任务已提交…");
    try {
      const job = await organizeKnowledgeBlock(blockId);
      for (let attempt = 0; attempt < 60; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        const latest = await getIngestionJob(job.id);
        if (latest.status === "succeeded") {
          setMessage("AI 整理完成，结果等待确认。");
          router.refresh();
          return;
        }
        if (latest.status === "failed") {
          throw new KnowledgeApiError(
            latest.error_message ?? "AI 整理任务失败。",
          );
        }
      }
      setMessage("任务仍在运行，可稍后刷新页面查看。");
    } catch (error) {
      setMessage(
        error instanceof KnowledgeApiError ? error.message : "无法启动整理任务。",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ingestion-actions">
      <input
        accept=".png,.jpg,.jpeg,.webp,.txt,.md,.pdf"
        hidden
        onChange={handleFile}
        ref={inputRef}
        type="file"
      />
      <button
        className="secondary-button"
        disabled={busy || organizing || !canIngest}
        onClick={() => inputRef.current?.click()}
        type="button"
      >
        上传附件
      </button>
      <button
        className="button"
        disabled={busy || organizing || !canIngest}
        onClick={handleOrganize}
        type="button"
      >
        {organizing ? "正在整理…" : "AI 整理"}
      </button>
      {message ? <span role="status">{message}</span> : null}
    </div>
  );
}
