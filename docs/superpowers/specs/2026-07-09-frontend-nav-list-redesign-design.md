# 前端导航精简与紧凑列表重构设计

日期:2026-07-09
状态:待用户确认

## 背景

Notebook 前端(`apps/web`)进入日常使用阶段。用户反馈两个核心问题:

1. **列表信息密度太低**:知识库列表每行约 130px(28px 标题 + 大间距),一屏只能看三四条;分类大卡片区还把列表挤到页面底部。
2. **导航与信息架构乱**:顶部导航有 7 个入口(知识库/待整理入库/搜索/分类管理/最近删除/设置/新增知识),首页 `/` 还是一个宣传页,日常使用需要多余的跳转和记忆。

另有一个直接影响本次改动的技术债:`apps/web/public/knowledge-list.js` 用捕获阶段
监听器接管了列表操作、草稿/确认表单提交、Markdown 预览切换和整理任务轮询。其中
表单提交在 `knowledge-draft-form.tsx`、`confirm-ai-result-form.tsx` 中已有等价 React
实现但被原生脚本架空,形成"两套逻辑改一处漏一处"的隐患;列表操作完成后依赖整页
跳转或 `location.replace` 刷新。重新设计列表 DOM 时这些 `data-*` 钩子必然失效,
因此交互迁移与显示重构一并完成(方案 B,已获用户确认)。

访问方式:用户日常通过 macOS 桌面 App(`apps/desktop`,Electron 壳)图标启动,
窗口内加载的就是本 Web 前端,故本次改动无需触碰桌面端代码;桌面 App 每次启动
会重新执行 Next.js 构建,改动在下次启动后自动生效。

## 目标

- 顶部导航精简为:知识库 · 搜索 · 设置 + [新增知识] 按钮。
- `/` 重定向到 `/knowledge`,删除宣传首页。
- 知识库页改为「状态 tab + 分类 chips + 紧凑列表」,一屏可见 10 条以上。
- 删除 `public/knowledge-list.js`,全部交互迁入 React 组件;列表操作局部更新,
  不再整页跳转刷新。

## 非目标

- 不改后端 API、不动搜索页功能(仅导航入口变化)。
- 不改详情页内容组织、状态文案、Markdown 默认显示模式(默认仍为纯文本 + 手动预览)。
- 不做桌面端启动提速或打包改动。
- 不做旧路由兼容跳转(仓库尚未首次提交,无历史链接负担)。

## 设计

### 1. 导航与路由

- `AppHeader` 精简为:品牌(链接 `/knowledge`)+ 知识库 / 搜索 / 设置 + [新增知识]。
- `src/app/page.tsx` 改为 `redirect("/knowledge")`(next/navigation)。
- 删除路由与页面:`/knowledge/pending`、`/knowledge/deleted`、`/categories`。
- 设置页(`/settings`)新增「分类管理」区块,复用现有 `category-manager.tsx`。
- 移动端断点(760px)下导航保持全部 4 个入口可见(现在入口少了,不再需要隐藏)。

### 2. 知识库页(`/knowledge`)

- **页头**:标题降为约 32px,去掉 eyebrow 装饰行与 72px 大标题;数量统计内联;
  右侧仅保留 [新增知识]。
- **状态 tab**:`全部 · 待处理 (n) · 最近删除`,URL 参数 `?view=pending|deleted`,
  服务端过滤:
  - 全部:默认列表(现有行为,不含已删除)。
  - 待处理:`status in (draft, organizing, pending_confirmation)`,平铺按更新时间
    倒序,以状态徽章区分,不再分三段;徽章文案沿用 `knowledge-status.tsx` 中文映射。
  - 最近删除:现 `/knowledge/deleted` 数据源,行内提供「恢复」「彻底清除」。
- **分类 chips**:一行小筛选块替代分类大卡片:`全部 · <各分类>(数量) · 未分类`,
  带分类色点,点击设置 `?category=`,与状态 tab 可组合。分类数量沿用现有前端
  计算方式(基于当前返回的 items 统计)。
- **紧凑列表行**(目标行高约 60px):
  - 第一行:标题(约 17px,加粗,单行截断)+ 右侧内联元信息(状态徽章、分类色点
    + 名称、更新日期)。
  - 第二行:摘要单行截断(muted);无摘要时显示原提示文案。
  - 悬停显示行内操作(删除,或 deleted 视图下的恢复/清除);整行(除操作区)可点
    进入详情。
  - 批量模式:工具栏「批量选择」进入,行首复选框 + 全选 + 按视图显示
    删除已选/恢复已选/彻底清除,危险操作保留 `window.confirm` 二次确认。

### 3. 交互迁移(删除 `public/knowledge-list.js`)

| 原生逻辑 | 去向 |
|---|---|
| 列表批量/单条 删除·恢复·清除、计数 | 新客户端组件 `KnowledgeListPanel`(合并 `knowledge-block-list-view.tsx` 与 `deleted-knowledge-list-view.tsx`,按 `view` 决定可用操作);React state 管理选择集,操作成功后从本地 state 移除行并 `router.refresh()` |
| 草稿表单提交拦截 + sessionStorage 恢复 | 删除;`knowledge-draft-form.tsx` 已有等价实现(含 sessionStorage),恢复其生效 |
| 确认入库表单提交拦截 | 删除;`confirm-ai-result-form.tsx` 已有等价实现,其 `router.refresh()` 后详情页按新状态渲染,不再依赖 `?confirmed=1` |
| Markdown 预览切换 | `knowledge-content-viewer.tsx` 改为客户端组件,用 useState 切换 |
| 整理任务轮询(`watchOrganizeJob`,整页 reload) | 新客户端组件 `OrganizeJobWatcher`:接收 `jobId`,1s 间隔轮询(上限 180 次),期间显示进度文案,成功/失败后 `router.refresh()`;挂在详情页工作流面板内 |
| `window.NOTEBOOK_API_URL` 注入 | 随脚本一并从 `layout.tsx` 移除 |

URL 参数接力(`draftSaved`/`organizeStarted`/`organizeDone`/`organizeError`/`confirmed`)
简化:新建草稿后仍跳转详情页并带 `jobId` 供 `OrganizeJobWatcher` 使用;纯提示类参数
随迁移移除,提示改由组件状态渲染。

### 4. 错误处理

- 沿用现有分层:API 调用失败在面板/表单内显示 `form-error`/`list-error` 文案;
  服务不可用时页面级 error-state 不变。
- 批量操作沿用现有逐条请求语义:失败即中止并显示错误,已成功的行保持已移除状态,
  `router.refresh()` 兜底同步服务端真实状态。

### 5. 测试与验证

- `make check` 全绿(ruff、pytest、eslint、tsc)。后端无改动,pytest 应保持原状。
- 预览浏览器手动全流程验证:新增草稿 → AI 整理轮询 → 确认入库 → 列表(全部/待
  处理/最近删除 tab、分类 chips 过滤)→ 删除 → 恢复 → 彻底清除;桌面 App 重启后
  确认新 UI 生效。
- 前端目前无组件测试基建,本次不新增测试框架;以上述手动验证 + 类型检查兜底。

## 验收标准

1. 顶部导航仅 3 入口 + 新增按钮;`/` 直达知识库;pending/deleted/categories 独立
   页面已删除,功能分别由知识库 tab 与设置页承接。
2. 知识库默认视图在 1120px 宽、900px 高视口下可见至少 10 条知识行。
3. `apps/web/public/knowledge-list.js` 已删除,`layout.tsx` 无脚本注入;删除/恢复/
   清除/确认入库均无整页跳转。
4. `make check` 通过。
