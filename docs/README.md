# Notebook 文档

[返回项目首页](../README.md)

## 使用与开发

| 文档 | 内容 |
| --- | --- |
| [开发环境](development-environment.md) | 工具版本、首次安装、启动命令、存储与日常检查 |
| [AI 与检索配置](configuration.md) | 本地模式、MiniMax、DeepSeek、embedding 与附件支持范围 |
| [macOS 桌面版](macos-desktop.md) | Electron 启动、打包及源码目录定位 |
| [贡献指南](../AGENTS.md) | 代码风格、测试、提交与 Pull Request 约定 |

## 设计资料

这些文档记录设计目标，不等同于已经交付的功能。当前可用能力见[项目首页](../README.md#核心能力)。

| 文档 | 内容 |
| --- | --- |
| [产品需求](product-requirements.md) | 产品场景、目标及规划 |
| [MVP 架构](mvp-architecture.md) | 服务分工、检索与问答方向 |
| [知识数据模型](knowledge-model.md) | 知识块、版本与索引的设计 |
| [前端导航设计](design/frontend-navigation.md) | 导航与紧凑列表重构意图及当前进度 |
| [README 设计调研](design/readme-design.md) | 参考项目、视觉原则与本仓库的落地方案 |

## 仓库内容约定

- 提交源码、迁移、测试、锁文件、可复用配置和维护中的项目文档。
- `.claude/` 等个人工具配置仅保留本地；通用开发约定集中在根目录 `AGENTS.md`。
- `.next/`、`next-env.d.ts`、`*.tsbuildinfo` 与桌面图标构建目录由命令生成，不提交。
- 旧工具执行清单位于本地忽略目录 `docs/superpowers/`；可维护的设计结论保存在 `docs/design/`。
- `assets/` 仅保存文档使用的视觉素材。图片使用仓库内相对路径，并提供替代文本。
