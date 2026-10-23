# macOS 桌面应用

Notebook 的 macOS 应用位于 `apps/desktop`，使用 Electron 承载现有 Next.js 前端。

## 前置要求

- Docker Desktop 已启动。
- `uv`、`fnm`、`pnpm 10.12.1` 可在终端 PATH 中访问，Node.js 22 已安装。
- 已执行过 `make setup`，或至少安装过 Python/Node 依赖。

## 开发运行

```bash
fnm exec --using=22 -- pnpm dev:desktop
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
fnm exec --using=22 -- pnpm build:desktop
```

构建产物会生成到：

```text
apps/desktop/dist/mac*/Notebook.app
```

当前桌面应用是“本机项目启动器”形态：`.app` 会复用这个仓库里的 Python、Node 和 Docker
环境。要做成完全自包含、可分发给没有开发环境的用户的安装包，需要进一步把后端运行时、
前端构建产物和数据库方案一并内置或替换。

## 项目目录定位

从源码启动或在仓库的 `apps/desktop/dist/` 中运行构建产物时，启动器会向上查找同时包含
`pnpm-workspace.yaml` 和 `pyproject.toml` 的项目目录，不依赖开发者机器的固定路径。

如果将 `.app` 移到了仓库以外（例如 `/Applications`），从终端显式指定源码目录：

```bash
NOTEBOOK_PROJECT_ROOT="/absolute/path/to/notebook" /Applications/Notebook.app/Contents/MacOS/Notebook
```

环境变量应指向完成依赖安装的仓库根目录。这个设置只对本次启动生效。

## 图标构建

`build:icon` 根据 `scripts/generate_icon.py` 生成 PNG、iconset 与 ICNS。
`pnpm build:desktop` 会自动调用该步骤；生成目录 `apps/desktop/build/` 不纳入版本控制。
