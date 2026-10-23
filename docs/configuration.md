# AI 整理与检索配置

[返回文档导航](README.md) · [返回项目首页](../README.md)

配置项以 [`.env.example`](../.env.example) 和 [Settings](../apps/api/app/config.py) 为准。
下面的模型名是本项目当前默认配置；可按你的供应商账户权限调整。

## 离线体验

默认的 `ORGANIZER_PROVIDER=local` 使用本地模板整理，`EMBEDDING_PROVIDER=local`
使用确定性哈希向量，不调用外部模型。它们用于开发与验证流程，不代表大模型整理或真实语义检索质量。

切换到 MiniMax 或 DeepSeek 后，待整理文本及适配器支持的附件内容会发送到所选服务；
使用远程 embedding 时，待索引文本和搜索查询也会发送到相应服务。
运行时在设置页保存的整理配置优先于 `.env` 默认值。

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

详细说明见 [开发环境文档](development-environment.md)。

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
