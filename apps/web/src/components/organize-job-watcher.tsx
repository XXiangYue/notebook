"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getIngestionJob } from "@/lib/knowledge-api";

const MAX_ATTEMPTS = 180;

export function OrganizeJobWatcher({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [message, setMessage] = useState(
    "AI 整理任务已启动，完成后会自动显示确认表单。",
  );
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    let attempts = 0;

    async function poll() {
      attempts += 1;
      try {
        const job = await getIngestionJob(jobId);
        if (cancelled) return;
        if (job.status === "succeeded") {
          setMessage("AI 整理已完成，正在载入确认表单…");
          router.refresh();
          return;
        }
        if (job.status === "failed") {
          setFailed(true);
          setMessage(job.error_message ?? "AI 整理任务失败，可以重新点击 AI 整理。");
          router.refresh();
          return;
        }
        setMessage(`AI 整理正在运行，已等待 ${attempts} 秒。完成后会自动显示确认表单。`);
      } catch {
        if (cancelled) return;
        setMessage("暂时无法读取 AI 整理进度，仍会继续重试。");
      }
      if (attempts < MAX_ATTEMPTS) {
        timer = window.setTimeout(poll, 1000);
      } else {
        setMessage("AI 整理仍在运行。可以稍后刷新页面查看结果。");
      }
    }

    timer = window.setTimeout(poll, 1000);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [jobId, router]);

  return (
    <div className={failed ? "form-error" : "form-status"} role={failed ? "alert" : "status"}>
      {message}
    </div>
  );
}
