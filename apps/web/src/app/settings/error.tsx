"use client";

import Link from "next/link";

type SettingsErrorProps = {
  reset: () => void;
};

export default function SettingsError({ reset }: SettingsErrorProps) {
  return (
    <main className="page-shell">
      <section className="error-state">
        <p className="eyebrow">Unable to load</p>
        <h1>设置页面加载失败</h1>
        <p>设置页渲染时遇到错误，请重试；如果仍然失败，请确认 API 服务和运行时设置文件正常。</p>
        <button className="button" onClick={() => reset()} type="button">
          重试
        </button>
        <p>
          <Link className="text-link" href="/knowledge">
            返回知识库 →
          </Link>
        </p>
      </section>
    </main>
  );
}
