"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  deleteKnowledgeBlock,
  KnowledgeApiError,
} from "@/lib/knowledge-api";

export function DeleteKnowledgeButton({ blockId }: { blockId: string }) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    if (!window.confirm("确认删除这条知识吗？删除后默认列表中将不再显示。")) {
      return;
    }

    setDeleting(true);
    setError(null);
    try {
      await deleteKnowledgeBlock(blockId);
      router.push("/knowledge");
      router.refresh();
    } catch (caught) {
      setError(
        caught instanceof KnowledgeApiError ? caught.message : "删除失败，请稍后重试。",
      );
      setDeleting(false);
    }
  }

  return (
    <div className="delete-action">
      <button
        className="danger-button"
        disabled={deleting}
        onClick={handleDelete}
        type="button"
      >
        {deleting ? "正在删除…" : "删除知识"}
      </button>
      {error ? <span role="alert">{error}</span> : null}
    </div>
  );
}

