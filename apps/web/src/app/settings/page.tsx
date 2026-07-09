import Link from "next/link";

import { AIOrganizerSettingsForm } from "@/components/ai-organizer-settings-form";
import { CategoryManager } from "@/components/category-manager";
import {
  KnowledgeApiError,
  getAIOrganizerSettings,
  listCategories,
  type AIOrganizerSettings,
  type Category,
} from "@/lib/knowledge-api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default async function SettingsPage() {
  let settings: AIOrganizerSettings;
  let categories: Category[];
  let errorMessage = `请确认 FastAPI 服务运行在 ${API_URL}，然后刷新页面。`;

  try {
    [settings, categories] = await Promise.all([
      getAIOrganizerSettings(),
      listCategories(),
    ]);
  } catch (caught) {
    if (caught instanceof KnowledgeApiError) {
      errorMessage = `设置接口返回：${caught.message}`;
    }

    return (
      <main className="page-shell">
        <section className="error-state">
          <p className="eyebrow">Service unavailable</p>
          <h1>暂时无法读取设置</h1>
          <p>{errorMessage}</p>
          <Link className="text-link" href="/knowledge">
            返回知识库 →
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <div className="page-heading compact-heading">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>设置</h1>
          <p className="page-description">
            配置 AI 整理使用的 provider、模型和接口地址。保存后新的后台整理任务会立即读取最新配置。
          </p>
        </div>
      </div>
      <AIOrganizerSettingsForm settings={settings} />

      <section className="content-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Categories</p>
            <h2>分类管理</h2>
          </div>
          <span>主分类用于稳定导航，系统分类保持少量。</span>
        </div>
        <CategoryManager categories={categories} />
      </section>
    </main>
  );
}
