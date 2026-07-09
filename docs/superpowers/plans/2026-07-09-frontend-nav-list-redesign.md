# 前端导航精简与紧凑列表重构 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 顶部导航精简为 3 入口,知识库页改为状态 tab + 分类 chips + 紧凑列表,删除 `public/knowledge-list.js` 并把全部交互迁入 React。

**Architecture:** Next.js App Router(服务端页面 + 客户端交互组件)。列表交互收敛到新的 `KnowledgeListPanel` 客户端组件;AI 整理轮询收敛到 `OrganizeJobWatcher`;pending/deleted/categories 三个独立页面分别由知识库 tab 与设置页承接。设计文档:`docs/superpowers/specs/2026-07-09-frontend-nav-list-redesign-design.md`。

**Tech Stack:** Next.js (App Router) + TypeScript,纯 CSS(globals.css),API 客户端 `src/lib/knowledge-api.ts`(已有全部所需函数,本次不改)。

**验证方式:** 前端无组件测试基建(设计文档明确本次不新增)。每个任务以 `lint + typecheck` 为门禁,最后统一 `make check` + 浏览器手动全流程验证。命令(在仓库根目录执行):

```bash
fnm exec --using=22 -- pnpm --filter @notebook/web lint
fnm exec --using=22 -- pnpm --filter @notebook/web typecheck
```

**重要背景(执行者必读):**

1. 仓库当前**没有任何提交**,所有文件都是 untracked。Task 0 先做基线提交,后续任务才有干净 diff。
2. `apps/web/public/knowledge-list.js` 用捕获阶段监听器接管了草稿/确认表单提交、列表操作、Markdown 预览切换、整理任务轮询。React 组件里已有等价的表单提交实现(被它架空)。在 Task 6 删除该文件之前,页面行为由它驱动;删除后由 React 接管。任务顺序保证删除时所有 React 等价物已就位。
3. 用户日常通过 macOS 桌面 App(`apps/desktop`,Electron)访问,窗口加载的就是本 Web 前端,桌面端代码不改。

---

### Task 0: 基线提交

**Files:** 全仓库(受 `.gitignore` 约束)

- [ ] **Step 1: 确认敏感文件不会入库**

```bash
git check-ignore .env data/ai-organizer-settings.json && echo OK
```

Expected: 输出被忽略的路径和 `OK`。若 `.env` 未被忽略,**停止并报告**,不得提交。

- [ ] **Step 2: 确认缓存文件被忽略**

```bash
git status --porcelain | grep -E "(pytest_cache|ruff_cache|tsbuildinfo|node_modules|\.next)" || echo CLEAN
```

Expected: `CLEAN`。若有缓存文件出现,先把对应模式补进 `.gitignore` 再继续。

- [ ] **Step 3: 基线提交**

```bash
git add -A && git commit -m "chore: 项目基线提交(重构前快照)"
```

- [ ] **Step 4: 提交设计文档与本计划**(若 Step 3 已包含则跳过)

```bash
git log --oneline -1
```

Expected: 能看到基线提交。

---

### Task 1: 导航精简 + 首页重定向 + 分类管理并入设置

**Files:**
- Modify: `apps/web/src/components/app-header.tsx`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/settings/page.tsx`
- Delete: `apps/web/src/app/categories/page.tsx`
- Modify: `apps/web/src/app/globals.css`(移动端导航隐藏规则)

- [ ] **Step 1: 精简 AppHeader**

`apps/web/src/components/app-header.tsx` 整文件替换为:

```tsx
import Link from "next/link";

export function AppHeader() {
  return (
    <header className="app-header">
      <Link className="brand" href="/knowledge">
        <span className="brand-mark">N</span>
        <span>Notebook</span>
      </Link>
      <nav aria-label="主导航">
        <Link href="/knowledge">知识库</Link>
        <Link href="/search">搜索</Link>
        <Link href="/settings">设置</Link>
        <Link className="button button-small" href="/knowledge/new">
          新增知识
        </Link>
      </nav>
    </header>
  );
}
```

- [ ] **Step 2: 首页重定向**

`apps/web/src/app/page.tsx` 整文件替换为:

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/knowledge");
}
```

- [ ] **Step 3: 设置页并入分类管理**

`apps/web/src/app/settings/page.tsx` 整文件替换为:

```tsx
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
```

- [ ] **Step 4: 删除分类管理独立页面**

```bash
rm apps/web/src/app/categories/page.tsx
```

- [ ] **Step 5: 更新移动端导航 CSS**

在 `apps/web/src/app/globals.css` 的 `@media (max-width: 760px)` 块中,删除以下两条规则(入口变少后不再需要隐藏):

```css
  .app-header nav > a:first-child {
    display: none;
  }

  .app-header nav > a:nth-child(4),
  .app-header nav > a:nth-child(5),
  .app-header nav > a:nth-child(6) {
    display: none;
  }
```

- [ ] **Step 6: lint + typecheck**

```bash
fnm exec --using=22 -- pnpm --filter @notebook/web lint && fnm exec --using=22 -- pnpm --filter @notebook/web typecheck
```

Expected: 均通过。

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/components/app-header.tsx apps/web/src/app/page.tsx apps/web/src/app/settings/page.tsx apps/web/src/app/categories apps/web/src/app/globals.css
git commit -m "feat(web): 导航精简为三入口,首页直达知识库,分类管理并入设置"
```

---

### Task 2: Markdown 预览切换迁入 React

**Files:**
- Modify: `apps/web/src/components/knowledge-content-viewer.tsx`

- [ ] **Step 1: 改为客户端组件并用 state 切换**

`knowledge-content-viewer.tsx` 只改两处。文件顶部加 `"use client";` 并引入 `useState`;把末尾的 `KnowledgeContentViewer` 函数替换为(`MarkdownPreview`、`parseMarkdown` 等其余内容不动):

```tsx
"use client";

import { Fragment, useState, type ReactNode } from "react";
```

```tsx
export function KnowledgeContentViewer({
  content,
  markdownContent,
}: KnowledgeContentViewerProps) {
  const [showPreview, setShowPreview] = useState(false);
  const previewMarkdown = markdownContent?.trim() ?? "";
  const hasMarkdown = Boolean(previewMarkdown);

  return (
    <div className="content-viewer">
      {hasMarkdown ? (
        <div className="content-viewer-actions">
          <button
            aria-pressed={showPreview}
            className="secondary-button button-small"
            onClick={() => setShowPreview((current) => !current)}
            type="button"
          >
            {showPreview ? "查看文本" : "预览 Markdown"}
          </button>
        </div>
      ) : null}

      {hasMarkdown && showPreview ? (
        <div aria-label="Markdown 预览" className="markdown-rendered" role="region">
          <div className="content-viewer-mode-label">Markdown 预览</div>
          <MarkdownPreview markdown={previewMarkdown} />
        </div>
      ) : (
        <div className="raw-content">{content}</div>
      )}
    </div>
  );
}
```

注意:同时删除了 `data-content-viewer`、`data-markdown-preview-toggle`、`data-markdown-preview-panel`、`data-markdown-raw-panel` 属性和 `hidden` 逻辑(原生脚本的钩子)。此时原生脚本的 toggle 分支找不到 `[data-content-viewer]` 会静默返回,React onClick 正常工作,不冲突。

- [ ] **Step 2: lint + typecheck**

```bash
fnm exec --using=22 -- pnpm --filter @notebook/web lint && fnm exec --using=22 -- pnpm --filter @notebook/web typecheck
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/components/knowledge-content-viewer.tsx
git commit -m "feat(web): Markdown 预览切换迁入 React state"
```

---

### Task 3: OrganizeJobWatcher + 详情页 URL 参数简化

**Files:**
- Create: `apps/web/src/components/organize-job-watcher.tsx`
- Modify: `apps/web/src/app/knowledge/[id]/page.tsx`
- Modify: `apps/web/src/components/knowledge-draft-form.tsx`

- [ ] **Step 1: 创建 OrganizeJobWatcher**

`apps/web/src/components/organize-job-watcher.tsx` 新建:

```tsx
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
```

- [ ] **Step 2: 详情页去掉提示类 URL 参数,接入 watcher**

`apps/web/src/app/knowledge/[id]/page.tsx` 修改:

a. searchParams 类型收窄为只剩 `jobId`:

```tsx
  searchParams?: Promise<{ jobId?: string }>;
```

b. import 增加:

```tsx
import { OrganizeJobWatcher } from "@/components/organize-job-watcher";
```

c. 删除 `query.confirmed === "1"` 提示块(`{query.confirmed === "1" && block.status === "searchable" ? (...) : null}` 整段)。

d. 工作流面板:`<div className="workflow-panel" data-organize-job-id=... data-organize-watch=...>` 改为普通 `<div className="workflow-panel">`;删除其中 `query.draftSaved`、`query.organizeStarted`、`query.organizeDone` 三个提示块,替换为一行 watcher 渲染(放在 `workflow-copy` 之前):

```tsx
              {query.jobId && !isPendingConfirmation ? (
                <OrganizeJobWatcher jobId={query.jobId} />
              ) : null}
```

- [ ] **Step 3: 草稿表单跳转参数简化**

`apps/web/src/components/knowledge-draft-form.tsx` 中 `handleSubmit` 的跳转两处修改:

```tsx
          const job = await organizeKnowledgeBlock(block.id);
          router.push(`/knowledge/${block.id}?jobId=${job.id}`);
        } catch {
          router.push(`/knowledge/${block.id}`);
        }
```

同时从 `<form>` 元素上删除原生脚本钩子属性(保留 `className` 和 `onSubmit`):`data-block-id`、`data-knowledge-draft-form`、`data-knowledge-editing`、`data-storage-key`。

**说明:** 原生脚本对该表单的拦截完全基于 `data-knowledge-draft-form` 属性;删除属性后 React `onSubmit` 立即接管,无过渡问题。确认表单的同类属性在 Task 6 处理。

- [ ] **Step 4: lint + typecheck**

```bash
fnm exec --using=22 -- pnpm --filter @notebook/web lint && fnm exec --using=22 -- pnpm --filter @notebook/web typecheck
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/organize-job-watcher.tsx apps/web/src/app/knowledge/\[id\]/page.tsx apps/web/src/components/knowledge-draft-form.tsx
git commit -m "feat(web): AI 整理轮询迁入 OrganizeJobWatcher,详情页去掉提示类 URL 参数"
```

---

### Task 4: KnowledgeListPanel 紧凑列表组件

**Files:**
- Create: `apps/web/src/components/knowledge-list-panel.tsx`
- Modify: `apps/web/src/app/globals.css`(新增紧凑行样式)

- [ ] **Step 1: 创建 KnowledgeListPanel**

`apps/web/src/components/knowledge-list-panel.tsx` 新建。要点:`view="default"` 提供删除,`view="deleted"` 提供恢复/彻底清除;批量与单条共用 `runAction`;操作成功的行记入 `removedIds` 本地隐藏 + `router.refresh()` 同步服务端;危险操作 `window.confirm` 确认。

```tsx
"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { KnowledgeStatus } from "@/components/knowledge-status";
import {
  deleteKnowledgeBlock,
  KnowledgeApiError,
  purgeKnowledgeBlock,
  restoreKnowledgeBlock,
  type Category,
  type KnowledgeBlockSummary,
} from "@/lib/knowledge-api";

type PanelView = "default" | "deleted";

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "未知时间";
  }
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(
    new Date(value),
  );
}

export function KnowledgeListPanel({
  blocks,
  categories,
  view = "default",
}: {
  blocks: KnowledgeBlockSummary[];
  categories: Category[];
  view?: PanelView;
}) {
  const router = useRouter();
  const [bulkMode, setBulkMode] = useState(false);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [removedIds, setRemovedIds] = useState<ReadonlySet<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categoryById = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );
  const items = blocks.filter((block) => !removedIds.has(block.id));
  const selectedItems = items.filter((block) => selected.has(block.id));
  const allSelected = items.length > 0 && selectedItems.length === items.length;

  function toggleSelected(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function exitBulkMode() {
    setBulkMode(false);
    setSelected(new Set());
    setError(null);
  }

  function confirmLabel(targets: KnowledgeBlockSummary[]) {
    const names = targets.map((block) => block.title || "未命名知识");
    return names.length <= 3
      ? names.join("、")
      : `${names.slice(0, 3).join("、")} 等 ${names.length} 条`;
  }

  async function runAction(
    targets: KnowledgeBlockSummary[],
    action: (id: string) => Promise<void>,
    failureMessage: string,
  ) {
    setBusy(true);
    setError(null);
    const done: string[] = [];
    try {
      for (const block of targets) {
        await action(block.id);
        done.push(block.id);
      }
    } catch (caught) {
      setError(
        caught instanceof KnowledgeApiError ? caught.message : failureMessage,
      );
    } finally {
      if (done.length > 0) {
        setRemovedIds((current) => new Set([...current, ...done]));
        setSelected((current) => {
          const next = new Set(current);
          for (const id of done) {
            next.delete(id);
          }
          return next;
        });
        router.refresh();
      }
      setBusy(false);
    }
  }

  async function handleDelete(targets: KnowledgeBlockSummary[]) {
    if (targets.length === 0) return;
    if (
      !window.confirm(
        `确认删除 ${confirmLabel(targets)} 吗？删除后会移入“最近删除”。`,
      )
    ) {
      return;
    }
    await runAction(targets, deleteKnowledgeBlock, "删除失败，请稍后重试。");
  }

  async function handleRestore(targets: KnowledgeBlockSummary[]) {
    if (targets.length === 0) return;
    await runAction(targets, restoreKnowledgeBlock, "恢复失败，请稍后重试。");
  }

  async function handlePurge(targets: KnowledgeBlockSummary[]) {
    if (targets.length === 0) return;
    if (
      !window.confirm(
        `确认彻底清除 ${confirmLabel(targets)} 吗？这个操作不能撤销。`,
      )
    ) {
      return;
    }
    await runAction(targets, purgeKnowledgeBlock, "彻底清除失败，请稍后重试。");
  }

  return (
    <section className="knowledge-list-panel" aria-label="知识块列表">
      <div className="knowledge-list-toolbar">
        {bulkMode ? (
          <>
            <div className="knowledge-list-bulk-actions">
              <button
                className="secondary-button secondary-button-small"
                disabled={busy || items.length === 0}
                onClick={() =>
                  setSelected(
                    allSelected
                      ? new Set()
                      : new Set(items.map((block) => block.id)),
                  )
                }
                type="button"
              >
                {allSelected ? "取消全选" : "全选"}
              </button>
              <span>
                {selectedItems.length > 0
                  ? `已选择 ${selectedItems.length} 条`
                  : "未选择知识"}
              </span>
            </div>
            <div className="knowledge-list-bulk-actions">
              {view === "default" ? (
                <button
                  className="danger-button danger-button-small"
                  disabled={busy || selectedItems.length === 0}
                  onClick={() => handleDelete(selectedItems)}
                  type="button"
                >
                  删除已选
                </button>
              ) : (
                <>
                  <button
                    className="secondary-button secondary-button-small"
                    disabled={busy || selectedItems.length === 0}
                    onClick={() => handleRestore(selectedItems)}
                    type="button"
                  >
                    恢复已选
                  </button>
                  <button
                    className="danger-button danger-button-small"
                    disabled={busy || selectedItems.length === 0}
                    onClick={() => handlePurge(selectedItems)}
                    type="button"
                  >
                    彻底清除
                  </button>
                </>
              )}
              <button
                className="secondary-button secondary-button-small"
                disabled={busy}
                onClick={exitBulkMode}
                type="button"
              >
                完成
              </button>
            </div>
          </>
        ) : (
          <>
            <span className="knowledge-list-count">{items.length} 条知识</span>
            <button
              className="secondary-button secondary-button-small"
              disabled={items.length === 0}
              onClick={() => setBulkMode(true)}
              type="button"
            >
              批量选择
            </button>
          </>
        )}
      </div>

      {error ? (
        <p className="list-error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="knowledge-list">
        {items.map((block) => {
          const category = block.category_id
            ? categoryById.get(block.category_id)
            : undefined;
          const body = (
            <>
              <div className="knowledge-row-line">
                <h2>{block.title}</h2>
                <span className="knowledge-row-meta">
                  <KnowledgeStatus
                    status={view === "deleted" ? "deleted" : block.status}
                  />
                  {category ? (
                    <span className="knowledge-row-category">
                      <i
                        style={{ background: category.color ?? "var(--accent)" }}
                      />
                      {category.name}
                    </span>
                  ) : null}
                  <span>
                    {view === "deleted"
                      ? `删除于 ${formatDate(block.deleted_at)}`
                      : formatDate(block.updated_at)}
                  </span>
                </span>
              </div>
              <p className="knowledge-row-summary">
                {block.summary ?? "尚未经过 AI 整理，当前仅保存原始资料。"}
              </p>
            </>
          );

          return (
            <article
              className="knowledge-row"
              data-selected={selected.has(block.id)}
              key={block.id}
            >
              {bulkMode ? (
                <label
                  className="knowledge-select-control"
                  aria-label={`选择 ${block.title}`}
                >
                  <input
                    checked={selected.has(block.id)}
                    onChange={() => toggleSelected(block.id)}
                    type="checkbox"
                  />
                </label>
              ) : null}
              {view === "deleted" ? (
                <div className="knowledge-row-main">{body}</div>
              ) : (
                <Link
                  className="knowledge-row-main"
                  href={`/knowledge/${block.id}`}
                >
                  {body}
                </Link>
              )}
              {!bulkMode ? (
                <div className="knowledge-row-actions">
                  {view === "default" ? (
                    <button
                      className="danger-icon-button"
                      disabled={busy}
                      onClick={() => handleDelete([block])}
                      type="button"
                    >
                      删除
                    </button>
                  ) : (
                    <>
                      <button
                        className="secondary-button secondary-button-small"
                        disabled={busy}
                        onClick={() => handleRestore([block])}
                        type="button"
                      >
                        恢复
                      </button>
                      <button
                        className="danger-icon-button"
                        disabled={busy}
                        onClick={() => handlePurge([block])}
                        type="button"
                      >
                        清除
                      </button>
                    </>
                  )}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: 新增紧凑行 CSS**

`apps/web/src/app/globals.css` 中,在 `.knowledge-list { border-top... }` 规则之后新增:

```css
.knowledge-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 4px;
  border-bottom: 1px solid var(--border);
}

.knowledge-row[data-selected="true"] {
  background: rgba(220, 235, 227, 0.4);
}

.knowledge-row-main {
  display: block;
  flex: 1;
  min-width: 0;
}

.knowledge-row-line {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
}

.knowledge-row-line h2 {
  overflow: hidden;
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-row-meta {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 12px;
}

.knowledge-row-category {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.knowledge-row-category i,
.category-chip i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.knowledge-row-summary {
  overflow: hidden;
  margin: 3px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-row-actions {
  display: inline-flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 120ms ease;
}

.knowledge-row:hover .knowledge-row-actions,
.knowledge-row:focus-within .knowledge-row-actions {
  opacity: 1;
}

@media (hover: none) {
  .knowledge-row-actions {
    opacity: 1;
  }
}
```

并在 `@media (max-width: 760px)` 块内追加:

```css
  .knowledge-row-line {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
```

- [ ] **Step 3: lint + typecheck**

```bash
fnm exec --using=22 -- pnpm --filter @notebook/web lint && fnm exec --using=22 -- pnpm --filter @notebook/web typecheck
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/components/knowledge-list-panel.tsx apps/web/src/app/globals.css
git commit -m "feat(web): 新增 KnowledgeListPanel 紧凑列表客户端组件"
```

---

### Task 5: 知识库页重构(状态 tab + 分类 chips + 紧凑列表)

**Files:**
- Modify: `apps/web/src/app/knowledge/page.tsx`(整文件重写)
- Delete: `apps/web/src/app/knowledge/pending/page.tsx`
- Delete: `apps/web/src/app/knowledge/deleted/page.tsx`
- Delete: `apps/web/src/components/knowledge-block-list-view.tsx`
- Delete: `apps/web/src/components/deleted-knowledge-list-view.tsx`
- Modify: `apps/web/src/app/globals.css`(新增 tab/chips/紧凑页头样式,删除废弃样式)
- Modify: `apps/web/src/app/knowledge/[id]/page.tsx` 与 `apps/web/src/app/knowledge/pending` 的互链清理(详情页无 pending 链接,无需改;检查即可)

- [ ] **Step 1: 重写知识库页**

`apps/web/src/app/knowledge/page.tsx` 整文件替换为:

```tsx
import Link from "next/link";

import { KnowledgeListPanel } from "@/components/knowledge-list-panel";
import {
  listCategories,
  listDeletedKnowledgeBlocks,
  listKnowledgeBlocks,
  type Category,
  type KnowledgeBlockList,
  type KnowledgeBlockStatus,
} from "@/lib/knowledge-api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const PENDING_STATUSES: KnowledgeBlockStatus[] = [
  "draft",
  "organizing",
  "pending_confirmation",
];

type View = "all" | "pending" | "deleted";

const VIEW_EMPTY_COPY: Record<View, { title: string; description: string }> = {
  all: {
    title: "还没有保存任何知识",
    description: "点击“新增知识”保存第一条草稿，保存后会自动进入 AI 整理。",
  },
  pending: {
    title: "没有待处理的知识",
    description: "草稿、AI 整理中和待确认入库的知识会集中显示在这里。",
  },
  deleted: {
    title: "最近删除为空",
    description: "删除后的知识块会先出现在这里，可以恢复或彻底清除。",
  },
};

function viewFromParam(value: string | undefined): View {
  return value === "pending" || value === "deleted" ? value : "all";
}

function hrefFor(view: View, category?: string) {
  const params = new URLSearchParams();
  if (view !== "all") {
    params.set("view", view);
  }
  if (category) {
    params.set("category", category);
  }
  const query = params.toString();
  return query ? `/knowledge?${query}` : "/knowledge";
}

export default async function KnowledgePage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string; category?: string }>;
}) {
  const params = await searchParams;
  const view = viewFromParam(params.view);
  const selectedCategory = view === "deleted" ? undefined : params.category;
  const statuses = view === "pending" ? PENDING_STATUSES : undefined;

  let categories: Category[];
  let result: KnowledgeBlockList;
  let chipSource: KnowledgeBlockList | null;
  let pendingTotal: number;
  try {
    [categories, result] = await Promise.all([
      listCategories(),
      view === "deleted"
        ? listDeletedKnowledgeBlocks()
        : listKnowledgeBlocks({
            ...(selectedCategory
              ? {
                  category_id:
                    selectedCategory === "uncategorized" ? null : selectedCategory,
                  uncategorized: selectedCategory === "uncategorized",
                }
              : {}),
            statuses,
          }),
    ]);
    chipSource =
      view === "deleted"
        ? null
        : selectedCategory
          ? await listKnowledgeBlocks({ statuses })
          : result;
    pendingTotal =
      view === "pending" && !selectedCategory
        ? result.total
        : (await listKnowledgeBlocks({ statuses: PENDING_STATUSES })).total;
  } catch {
    return (
      <main className="page-shell">
        <section className="error-state">
          <p className="eyebrow">Service unavailable</p>
          <h1>暂时无法读取知识库</h1>
          <p>请确认 FastAPI 服务运行在 {API_URL}，然后刷新页面。</p>
        </section>
      </main>
    );
  }

  const emptyCopy = VIEW_EMPTY_COPY[view];
  const countFor = (categoryId: string | null) =>
    chipSource
      ? chipSource.items.filter((block) => block.category_id === categoryId).length
      : 0;

  return (
    <main className="page-shell">
      <div className="list-heading">
        <div>
          <h1>知识库</h1>
          <span className="list-heading-count">共 {result.total} 条</span>
        </div>
        <Link className="button button-small" href="/knowledge/new">
          新增知识
        </Link>
      </div>

      <nav className="view-tabs" aria-label="列表视图">
        <Link
          className="view-tab"
          data-active={view === "all"}
          href={hrefFor("all", selectedCategory)}
        >
          全部
        </Link>
        <Link
          className="view-tab"
          data-active={view === "pending"}
          href={hrefFor("pending", selectedCategory)}
        >
          待处理 ({pendingTotal})
        </Link>
        <Link
          className="view-tab"
          data-active={view === "deleted"}
          href={hrefFor("deleted")}
        >
          最近删除
        </Link>
      </nav>

      {view !== "deleted" ? (
        <nav className="category-chips" aria-label="分类筛选">
          <Link
            className="category-chip"
            data-active={!selectedCategory}
            href={hrefFor(view)}
          >
            全部分类
          </Link>
          {categories.map((category) => (
            <Link
              className="category-chip"
              data-active={selectedCategory === category.id}
              href={hrefFor(view, category.id)}
              key={category.id}
            >
              <i style={{ background: category.color ?? "var(--accent)" }} />
              {category.name} ({countFor(category.id)})
            </Link>
          ))}
          <Link
            className="category-chip"
            data-active={selectedCategory === "uncategorized"}
            href={hrefFor(view, "uncategorized")}
          >
            未分类 ({countFor(null)})
          </Link>
        </nav>
      ) : null}

      {result.items.length === 0 ? (
        <section className="empty-state">
          <h2>{emptyCopy.title}</h2>
          <p>{emptyCopy.description}</p>
          {view !== "deleted" ? (
            <Link className="text-link" href="/knowledge/new">
              创建知识 →
            </Link>
          ) : null}
        </section>
      ) : (
        <KnowledgeListPanel
          blocks={result.items}
          categories={categories}
          view={view === "deleted" ? "deleted" : "default"}
        />
      )}
    </main>
  );
}
```

- [ ] **Step 2: 删除被 tab 取代的页面与旧列表组件**

```bash
rm apps/web/src/app/knowledge/pending/page.tsx apps/web/src/app/knowledge/deleted/page.tsx
rm apps/web/src/components/knowledge-block-list-view.tsx apps/web/src/components/deleted-knowledge-list-view.tsx
rmdir apps/web/src/app/knowledge/pending apps/web/src/app/knowledge/deleted
```

- [ ] **Step 3: 清理详情页残留的 pending 入口(如有)**

检查 `apps/web/src/app/knowledge/[id]/page.tsx` 和其余文件对已删路由的引用:

```bash
grep -rn "knowledge/pending\|knowledge/deleted\|href=\"/categories\"" apps/web/src --include="*.tsx"
```

Expected: 无输出。若有输出,把链接替换为 `/knowledge?view=pending`、`/knowledge?view=deleted`、`/settings`。

- [ ] **Step 4: 新增页头/tab/chips CSS,删除废弃样式**

`apps/web/src/app/globals.css`:

新增(放在 `.knowledge-row` 规则之前):

```css
.list-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.list-heading h1 {
  display: inline;
  margin: 0;
  font-size: 32px;
  letter-spacing: -0.02em;
}

.list-heading-count {
  margin-left: 12px;
  color: var(--muted);
  font-size: 14px;
}

.view-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--border);
}

.view-tab {
  padding: 10px 14px;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  font-size: 14px;
  font-weight: 700;
}

.view-tab[data-active="true"] {
  border-bottom-color: var(--accent);
  color: var(--accent-dark);
}

.category-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}

.category-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 30px;
  padding: 4px 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.category-chip[data-active="true"] {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent-dark);
}
```

删除以下不再被引用的规则块(整块删除):
- `.knowledge-list-panel[data-bulk-mode="false"] [data-bulk-controls]`、`.knowledge-list-panel[data-bulk-mode="true"] [data-bulk-enter]...` 两条 data-bulk-mode 规则
- `.category-browser`、`.category-entry`、`.category-entry:hover`、`.category-entry-color`、`.uncategorized-color`、`.category-entry h2`、`.category-entry p`、`.category-entry strong`
- `.home-recent-section, .home-empty-state`
- `.pending-summary-grid`、`.pending-summary-card`、`.pending-summary-card:hover`、`.pending-summary-card span`、`.pending-summary-card strong`、`.pending-buckets`、`.pending-bucket`、`.pending-section-heading`、`.pending-section-heading p:not(.eyebrow)`、`.pending-empty`、`.pending-empty h3`、`.pending-empty p`
- `.knowledge-list-item`(及其全部派生:`[data-bulk-mode="true"] .knowledge-list-item`、`:hover`、`[data-selected="true"]`、`h2`、`p`)、`.knowledge-list-main`、`a.knowledge-list-main`、`.knowledge-list-meta`(保留——详情页仍在用)、`.list-arrow`
- `@media (max-width: 760px)` 内引用上述已删类的行(`.grid, .category-browser, .pending-summary-grid...` 列表里去掉已删的类名;`.knowledge-list-item` 相关规则整块删)
- 首页 hero 相关:`.grid`、`.card`、`.card strong`、`.card p`、`.hero-actions`、`.lede`(首页已重定向,搜索/详情等页未用这些类;删除前 grep 确认)

```bash
grep -rn "hero-actions\|className=\"lede\"\|className=\"grid\"\|className=\"card\"" apps/web/src --include="*.tsx"
```

Expected: 无输出后再删。

- [ ] **Step 5: lint + typecheck**

```bash
fnm exec --using=22 -- pnpm --filter @notebook/web lint && fnm exec --using=22 -- pnpm --filter @notebook/web typecheck
```

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/app/knowledge apps/web/src/components apps/web/src/app/globals.css
git commit -m "feat(web): 知识库页改为状态 tab + 分类 chips + 紧凑列表"
```

---

### Task 6: 删除原生脚本与 layout 注入

**Files:**
- Delete: `apps/web/public/knowledge-list.js`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/components/confirm-ai-result-form.tsx`(去掉钩子属性)

- [ ] **Step 1: 确认原生脚本钩子已无消费者**

```bash
grep -rn "data-knowledge-draft-form\|data-confirm-ai-form\|data-knowledge-item\|data-markdown-preview-toggle\|data-organize-watch\|data-bulk-enter" apps/web/src --include="*.tsx"
```

Expected: 只剩 `confirm-ai-result-form.tsx` 的 `data-confirm-ai-form`(下一步删)。若还有其他输出,先回头处理。

- [ ] **Step 2: 确认表单去掉钩子属性**

`apps/web/src/components/confirm-ai-result-form.tsx` 中 `<form>` 元素删除 `data-block-id={blockId}` 和 `data-confirm-ai-form` 两个属性(React `onSubmit` 从此真正接管提交,`router.refresh()` 局部更新)。

- [ ] **Step 3: 删除脚本与 layout 注入**

```bash
rm apps/web/public/knowledge-list.js
```

`apps/web/src/app/layout.tsx` 整文件替换为:

```tsx
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppHeader } from "@/components/app-header";

import "./globals.css";

export const metadata: Metadata = {
  title: "Notebook",
  description: "个人 AI 知识库",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <AppHeader />
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 4: lint + typecheck**

```bash
fnm exec --using=22 -- pnpm --filter @notebook/web lint && fnm exec --using=22 -- pnpm --filter @notebook/web typecheck
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/public apps/web/src/app/layout.tsx apps/web/src/components/confirm-ai-result-form.tsx
git commit -m "refactor(web): 删除 public/knowledge-list.js,交互全部由 React 组件接管"
```

---

### Task 7: 全量检查与手动验证

**Files:** 无新改动(验证 + 修复)

- [ ] **Step 1: 全量检查**

```bash
make check
```

Expected: ruff、pytest、eslint、tsc 全部通过(后端未改,pytest 应保持原状)。

- [ ] **Step 2: 浏览器手动全流程验证**

开发服务已运行(或 `make api`、`make worker`、`make web`)。按顺序验证并记录结果:

1. 访问 `/` → 重定向到 `/knowledge`;顶部导航只有 知识库/搜索/设置/新增知识。
2. `/knowledge`:页头紧凑;三个 tab;分类 chips 可点且过滤生效;1120×900 视口下可见 ≥10 行(验收标准 2)。
3. 新增知识 → 保存后跳详情页且 URL 只带 `jobId` → 整理进度文案逐秒更新 → 完成后自动出现确认表单(无整页刷新)。
4. 确认入库 → 页面局部更新为已确认状态。
5. 详情页 Markdown「预览 Markdown」按钮切换正常。
6. 列表删除单条 → 行消失无整页跳转;`?view=deleted` 中恢复 → 行消失;再删一条后彻底清除 → 行消失。
7. 批量选择 → 全选 → 删除已选/恢复已选 正常。
8. `?view=pending`:草稿/整理中/待确认集中显示,徽章区分。
9. `/settings`:AI 设置正常 + 分类管理可创建/编辑/删除分类。
10. 移动宽度(375px)下导航与列表不溢出。

- [ ] **Step 3: 桌面 App 验证**

重启 macOS Notebook.app(每次启动重新构建 Next.js),确认窗口内为新 UI。

- [ ] **Step 4: 修复发现的问题并提交**

发现问题按 systematic-debugging 处理;修复后:

```bash
git add -A && git commit -m "fix(web): 手动验证发现的问题修复"
```

(无问题则跳过。)

---

## Self-Review 记录

- **Spec 覆盖:** 导航精简(Task 1)、首页重定向(Task 1)、分类并入设置(Task 1)、状态 tab + chips + 紧凑列表(Task 4/5)、pending/deleted/categories 页面删除(Task 1/5)、knowledge-list.js 删除与四类交互迁移(Task 2/3/4/6)、验收标准逐条对应(Task 5 行高 CSS + Task 7 验证)。无缺口。
- **占位符扫描:** 无 TBD/TODO;所有代码步骤含完整代码。
- **类型一致性:** `KnowledgeListPanel` props(`blocks/categories/view`)与 Task 5 调用一致;`OrganizeJobWatcher` props(`jobId`)与 Task 3 详情页调用一致;`hrefFor`/`viewFromParam` 仅在 Task 5 内部使用。
