# macOS 桌面应用

Notebook 的 macOS 应用位于 `apps/desktop`，使用 Electron 承载现有 Next.js 前端。

## 前置要求

- Docker Desktop 已启动。
- `uv`、`pnpm` 可在终端 PATH 中访问。
- 已执行过 `make setup`，或至少安装过 Python/Node 依赖。

## 开发运行

```bash
pnpm dev:desktop
```

应用启动时会自动执行：

1. 如果没有 `.env`，从 `.env.example` 创建。
2. 启动 `infrastructure/compose.yml` 中的 PostgreSQL 和 Redis。
3. 执行数据库迁移。
4. 启动 FastAPI 和 worker。
5. 构建 Next.js 前端并用 `next start` 启动生产模式 Web 服务。
6. 在 macOS 窗口中打开可用的本地 Web 端口，默认是 `http://127.0.0.1:3000`。

关闭 Notebook 窗口或退出应用时，应用会终止本次启动的 API、worker、Next.js
进程树，并停止对应的 Docker Compose 服务，避免后台服务继续占用端口。

## 生成 `.app`

```bash
pnpm build:desktop
```

构建产物会生成到：

```text
apps/desktop/dist/mac*/Notebook.app
```

当前桌面应用是“本机项目启动器”形态：`.app` 会复用这个仓库里的 Python、Node 和 Docker
环境。要做成完全自包含、可分发给没有开发环境的用户的安装包，需要进一步把后端运行时、
前端构建产物和数据库方案一并内置或替换。
