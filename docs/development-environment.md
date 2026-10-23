# 开发环境与容器方案

## 1. 结论

本项目采用混合开发模式：

```text
本机
├── Next.js Web
├── FastAPI API
├── Python Worker
├── Git、编辑器和调试器
└── 项目源码

Docker Compose
├── PostgreSQL + pgvector
└── Redis
```

本机应用使用虚拟环境隔离依赖，基础设施使用容器隔离服务。应用容器化是后续方向，当前仓库尚未提供 Web、API 和 Worker 的生产镜像。

## 2. 三种隔离方式

### 2.1 语言虚拟环境

Python 的 `.venv` 只隔离 Python 解释器和第三方包，不包含操作系统、PostgreSQL 或 Redis。

本项目使用 `uv`：

- `.python-version` 锁定 Python 3.12。
- `pyproject.toml` 声明依赖范围。
- `uv.lock` 在依赖安装后锁定精确版本。
- `.venv` 只存在本机，不提交 Git。

Node.js 不使用 Python 式虚拟环境。项目通过 `.nvmrc` 锁定 Node.js 22，
使用 `fnm exec` 只在项目命令中切换版本，并通过 pnpm workspace 和锁文件隔离、固定依赖。
项目没有向 shell 启动文件写入自动切换配置，因此其他程序和项目仍使用原有系统 Node.js。

### 2.2 Docker 容器

容器打包应用进程及其运行依赖，但共享宿主机内核。它比虚拟机轻量，适合运行版本固定的 PostgreSQL、Redis 和部署后的应用。

容器不是数据备份。数据库数据保存在 Docker volume 中，仍需单独制定备份策略。

### 2.3 虚拟机

虚拟机包含完整客体操作系统，隔离更强但启动慢、资源开销大。本项目开发阶段不需要虚拟机。

未来执行用户或 AI 生成的不可信代码时，普通容器也不等于绝对安全边界。届时需要专门沙箱、受限系统调用、资源限制和网络策略。

## 3. 为什么选择混合开发

- Web 和 API 直接在本机运行，热更新和断点调试简单。
- PostgreSQL、pgvector 和 Redis 不需要安装到 macOS。
- 服务版本由 Compose 固定，环境容易复现。
- 源码挂载、容器网络和文件权限问题较少。
- 后续可复用相同服务配置构建完整容器化测试环境。

## 4. 版本策略

| 工具 | 项目版本策略 |
| --- | --- |
| Python | 3.12，使用 `.python-version` |
| Python 包 | `pyproject.toml` 声明范围，`uv.lock` 固定解析结果 |
| Node.js | 22 LTS，使用 `.nvmrc` 和 `fnm exec` |
| pnpm | 根 `package.json` 的 `packageManager` 字段 |
| PostgreSQL | Compose 镜像固定主版本和 pgvector 标签 |
| Redis | Compose 镜像固定主版本 |

不要依赖系统自带的 Python，也不要使用机器上任意版本的 Node.js。升级运行时或数据库主版本需要作为单独变更处理。

## 5. 首次安装

### 5.1 检查工具

```bash
brew install fnm
fnm --version
uv --version
docker --version
docker compose version
```

安装项目使用的 Node.js 22：

```bash
fnm install 22
fnm exec --using=22 -- node --version
```

无需修改 `~/.zshrc`，也无需将 Node.js 22 设置为系统默认版本。项目 Makefile 会
通过 `fnm exec --using=22` 调用已安装的 pnpm 10.12.1。

### 5.2 初始化项目

```bash
cp .env.example .env
make setup
make infra-up
make migrate
```

`make setup` 会创建 Python `.venv`、安装 Python 依赖并安装前端依赖。`make migrate`
使用 Alembic 将数据库升级到当前版本；拉取包含数据库变更的新代码后也需要执行该命令。

可用以下命令确认版本隔离：

```bash
make node-version
```

输出中的 `system Node` 是其他程序继续使用的版本，`project Node` 应为 Node.js 22。

### 5.3 启动应用

使用三个终端：

```bash
make api
make worker
make web
```

## 6. Compose 服务

服务定义位于 `infrastructure/compose.yml`：

- `postgres`：业务数据库、全文索引和 pgvector。
- `redis`：异步任务队列。

常用命令：

```bash
make infra-up
make infra-logs
make infra-down
```

`infra-up` 会等待 PostgreSQL 和 Redis 的健康检查通过后再返回，随后即可运行
`make migrate`，避免首次启动时数据库尚未就绪造成连接失败。

`infra-down` 不删除 volume。除非明确需要清空本地数据，否则不要执行带 `--volumes` 的关闭命令。

## 7. 配置和密钥

- `.env.example` 提交到 Git，描述所有可用配置。
- `.env` 保存本机配置和密钥，禁止提交。
- 浏览器可见变量必须使用 `NEXT_PUBLIC_` 前缀，且不能包含秘密。
- 模型 API Key 只由 API 或 Worker 读取。
- 生产环境从部署平台的密钥系统注入配置，不把 `.env` 打进镜像。

新增配置项时，必须同时更新：

1. `.env.example`
2. Python 或前端配置模型
3. 本文档中需要用户理解的部分

## 8. 网络与地址

本机应用访问 Compose 服务时使用：

```text
PostgreSQL: 127.0.0.1:5432
Redis:      127.0.0.1:6379
```

容器之间通信时应使用 Compose 服务名，例如 `postgres:5432`，不能使用 `127.0.0.1`。完整容器化部署时会提供单独的容器环境配置。

## 9. 数据与文件

- PostgreSQL 数据保存在命名 volume `postgres_data`。
- Redis 在开发环境启用持久化 volume，但不能作为事实数据源。
- 上传附件保存在仓库下的 `data/`，目录内容不提交 Git。
- 数据库是元数据和业务状态的事实来源，附件通过存储键引用。

## 10. 日常开发检查

```bash
make check
```

该命令运行：

- Ruff Python 静态检查
- Pytest
- ESLint
- Next.js 路由类型生成与 TypeScript 类型检查

提交依赖变更时需要同时提交 `uv.lock` 或 `pnpm-lock.yaml`。

`next-env.d.ts` 和 `*.tsbuildinfo` 由 Next.js / TypeScript 生成，已加入忽略规则。
全新克隆后运行类型检查会先执行 `next typegen`，无需预先启动开发服务器。
个人工具配置（如 `.claude/`）与依赖缓存只保留本地，项目级约定见 [AGENTS.md](../AGENTS.md)。

数据库模型发生变化时，不直接修改已经应用过的迁移，而是创建新迁移：

```bash
make migration message="add attachments"
make migrate
```

## 11. 开发与生产差异

开发环境：

- 应用在本机运行。
- 基础设施在容器中运行。
- 开启热更新和调试日志。

未来生产部署建议（尚未提供完整部署方案）：

- Web、API、Worker 分别构建不可变镜像。
- 数据库优先使用托管服务或独立持久化部署。
- 不开放 PostgreSQL 和 Redis 的公网端口。
- 由反向代理终止 TLS。
- 使用生产密钥管理、备份、监控和迁移流程。

## 12. 当前业务能力

当前已实现：

- Alembic 初始迁移和默认分类数据迁移。
- `categories`、`knowledge_blocks` 和 `knowledge_versions` 基础表。
- 创建、读取、编辑和软删除知识块 API。
- 分类列表和自定义分类创建 API。
- 知识列表、新建草稿、详情、编辑和分类管理 Web 页面。
- 编辑草稿时创建新版本并保留原始版本。
- 知识块主分类关联与默认分类。
- 附件元数据、本地受控存储与上传接口。
- Redis + ARQ 异步整理任务和持久化任务状态。
- 无模型密钥时可运行的本地整理适配器。
- MiniMax M3 Anthropic 兼容适配器、图片 base64 输入和强制工具调用。
- AI 生成 Markdown 版本和待确认状态展示。
- AI 结果编辑确认，确认后生成 `user_confirmed` 当前正式版本。
- 确认版本的 Markdown 分块和活动分块持久化。
- 确认版本的 embedding 生成和 `chunk_embeddings` 持久化，支持本地 deterministic provider 与 MiniMax `embo-01`。
- 基于活动分块的 `/search` API，PostgreSQL 全文检索、pgvector 向量召回和 RRF 融合排序。
- Web 搜索页面，支持输入关键词并跳转到命中的知识块详情。
- 本地 Web 地址白名单 CORS 配置。
- API 自动化测试以及前端 lint、类型检查和生产构建。
- 真实 PostgreSQL 与浏览器端到端联调，覆盖分类、编辑版本和软删除。

下一个里程碑是增加 PDF 内容提取，并建立检索评测集来校准召回规模、RRF 参数和相似度阈值。
