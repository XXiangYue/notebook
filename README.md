# Notebook

面向个人用户的 AI 知识采集、整理、检索与问答工具。

当前仓库处于 MVP 基础设施阶段，采用混合开发模式：

- Next.js、FastAPI 和 Worker 在本机运行，获得更直接的热更新和调试体验。
- PostgreSQL + pgvector 与 Redis 通过 Docker Compose 运行。
- 生产环境再将应用进程容器化。

## 快速开始

前置要求：

- `fnm` Node.js 版本管理器
- Python 3.12（`uv` 会按 `.python-version` 管理）
- `uv`
- Docker Desktop
- pnpm 10.12.1

项目通过 `.nvmrc` 固定 Node.js 22。Makefile 使用 `fnm exec` 运行前端命令，
不会修改系统 Node.js，也不会影响其他项目。

```bash
cp .env.example .env
make setup
make infra-up
make migrate
```

检查隔离后的 Node.js 版本：

```bash
make node-version
```

输出会分别显示系统 Node 和项目 Node；前端命令以项目 Node 22 为准。

分别启动三个开发进程：

```bash
make api
make worker
make web
```

访问：

- Web：http://127.0.0.1:3000
- 知识列表：http://127.0.0.1:3000/knowledge
- 新增知识：http://127.0.0.1:3000/knowledge/new
- 分类管理：http://127.0.0.1:3000/categories
- 全文搜索：http://127.0.0.1:3000/search
- 设置：http://127.0.0.1:3000/settings
- API 文档：http://127.0.0.1:8000/docs
- API 存活检查：http://127.0.0.1:8000/health/live
- API 就绪检查：http://127.0.0.1:8000/health/ready

创建并读取知识草稿：

```bash
curl -X POST http://127.0.0.1:8000/knowledge-blocks \
  -H 'Content-Type: application/json' \
  -d '{"topic":"RAG 检索","raw_text":"混合检索结合关键词与向量召回。"}'

curl http://127.0.0.1:8000/knowledge-blocks
```

搜索已确认知识：

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"混合检索","limit":20}'
```

浏览器当前支持：

- 查看知识块列表。
- 输入标题、主题、语言、主分类和原始内容并保存草稿。
- 查看知识块详情、当前版本、内容哈希和版本数量。
- 编辑草稿并创建新版本，首次提交的内容不会被覆盖。
- 软删除知识块，删除后默认列表不再显示。
- 查看系统分类并创建自定义分类。
- 上传图片、文本、Markdown 或 PDF 附件到受控本地存储。
- 在设置页切换 AI 整理 provider，并配置 MiniMax 或 DeepSeek 模型参数。
- 提交异步 AI 整理任务并查看任务状态和待确认 Markdown。
- 编辑 AI 整理结果，确认后生成 `user_confirmed` 正式版本。
- 基于确认后的 Markdown 生成活动分块，作为检索和向量索引输入。
- 基于活动分块的 PostgreSQL 全文检索、pgvector 向量召回、RRF 融合排序 API 和搜索页面。

当前下一步：

- 增加 PDF 正文提取；图片已通过 MiniMax M3 多模态输入处理。
- 增加检索评测集，校准召回规模、RRF 参数和相似度阈值。

## AI 整理 Provider

AI 整理支持 `local`、`minimax` 和 `deepseek` 三种适配器。开发环境默认使用本地适配器。
可以在 Web 设置页切换 provider 并保存到 `data/ai-organizer-settings.json`；也可以在 `.env`
中预置默认值。

接入 MiniMax Token Plan 时，设置：

```dotenv
ORGANIZER_PROVIDER=minimax
MINIMAX_API_KEY=<Token Plan 订阅 Key>
MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic
MINIMAX_MODEL=MiniMax-M3
MINIMAX_MAX_TOKENS=8192
```

接入 DeepSeek V4 Flash 时，设置：

```dotenv
ORGANIZER_PROVIDER=deepseek
DEEPSEEK_API_KEY=<DeepSeek API Key>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_MAX_TOKENS=8192
DEEPSEEK_THINKING_ENABLED=false
```

密钥只放在已被 Git 忽略的 `.env`，不得写入 `.env.example` 或提交到仓库。
运行时设置文件位于已忽略的 `data/` 下，也不要提交到仓库。

MiniMax 适配器使用 Anthropic 兼容接口和强制工具调用：

- 图片以 base64 内容块发送，支持 PNG、JPEG、GIF 和 WEBP。
- txt、Markdown 附件作为文本加入上下文。
- PDF 暂时只提供文件名并返回警告，后续增加本地正文提取。
- 模型结果通过 JSON Schema 校验后才保存为 `ai_generated` 版本。

DeepSeek 适配器使用 OpenAI 兼容 `/chat/completions` 接口和 JSON 输出：

- txt、Markdown 附件作为文本加入上下文。
- 图片和 PDF 暂时只提供文件名并返回警告。
- 默认关闭 thinking 模式，避免整理任务产生额外推理输出。

官方资料：

- [MiniMax 模型概览](https://platform.minimaxi.com/docs/guides/models-intro)
- [Token Plan 快速接入](https://platform.minimaxi.com/docs/token-plan/quickstart)
- [Anthropic 兼容接口](https://platform.minimaxi.com/docs/api-reference/text-anthropic-api)
- [DeepSeek API 文档](https://api-docs.deepseek.com/)
- [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion)

详细说明见 [开发环境文档](docs/development-environment.md)。

## 检索 MVP

当前 `/search` 使用混合召回：

- 关键词召回：PostgreSQL `to_tsvector` + `websearch_to_tsquery`，并用 `ILIKE` 兜底中文短语。
- 向量召回：`chunk_embeddings.embedding_vector` 使用 pgvector `vector(1536)` 和 cosine distance。
- 融合排序：关键词排名和向量排名通过 RRF 合并。

Embedding 支持 `local` 和 `minimax` 两种 provider。`local-hash-embedding-v1` 用于离线测试；
接入 MiniMax 时设置：

```dotenv
EMBEDDING_PROVIDER=minimax
EMBEDDING_MODEL=embo-01
EMBEDDING_DIMENSIONS=1536
EMBEDDING_BASE_URL=https://api.minimaxi.com/v1
```

API Key 优先读取 `EMBEDDING_API_KEY`，未设置时复用 `MINIMAX_API_KEY`。历史或旧模型产生的
embedding 是派生数据，迁移维度或更换模型后可清空并由搜索路径自动重建。

## 参与贡献

欢迎提交 Issue 和 Pull Request。开发规范、目录结构与检查命令见 [贡献指南](AGENTS.md)。
提交代码前请运行 `make check`；界面变更请附上截图和验证说明。

## 开源许可

本项目使用 [MIT License](LICENSE)。
