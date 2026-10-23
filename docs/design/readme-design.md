# README 设计调研与维护

调研日期：2026-10-23。以下观察来自各项目当时的 README；链接内容后续可能更新。

## 参考项目

| 项目 | 观察到的设计 | Notebook 的取舍 |
| --- | --- | --- |
| [Memos](https://github.com/usememos/memos/blob/main/README.md) | 品牌标识、简短定位、深浅色产品截图，紧接安装入口；详细部署说明放在文档中。 | 一句话说明用途，提供主题适配，缩短首轮启动路径。 |
| [AppFlowy](https://github.com/AppFlowy-IO/AppFlowy/blob/main/README.md) | 居中的标题、徽章与导航，大幅产品截图展示使用场景，安装和贡献入口明确。 | 采用清晰首屏层次；展示素材应来自本项目，功能描述与代码保持一致。 |
| [AFFiNE](https://github.com/toeverything/AFFiNE/blob/canary/README.md) | 品牌主视觉和居中入口，用独立功能段落表达能力，再引导贡献。 | 统一视觉语言，将功能压缩成便于扫读的表格。 |
| [Dify](https://github.com/langgenius/dify/blob/main/README.md) | 顶部横幅与导航，快速开始靠前，复杂能力和高级配置逐层展开。 | 使用本地横幅，将模型参数、API 示例等细节移入专门文档。 |

GitHub 官方建议 README 回答项目用途、价值、上手方式和求助途径，并推荐使用相对链接关联仓库文件。参见 [About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)。

## 本仓库采用的结构

1. **品牌首屏**：横幅、一句话定位、四枚徽章和导航。
2. **价值与能力**：先解释处理流程，再列出已经实现的功能和范围。
3. **快速开始**：克隆、初始化、三个终端启动；桌面入口放在折叠区。
4. **深入了解**：架构图、目录、文档导航、规划、贡献和许可。

## 视觉规范

- 沿用应用的松绿色 `#176b4d` 与暖纸色 `#f3f0e8`；深色横幅使用独立配色。
- 横幅是产品流程插画，不充当界面截图。正文保留文字版流程，图片加载失败时也能理解。
- 使用原生 Markdown、少量 GitHub 支持的 HTML、SVG 与 Mermaid，不依赖自定义脚本或页面样式。
- 徽章仅显示许可、阶段和运行时版本。未建立 CI 或正式 Release 时，不展示虚构状态。
- 居中仅用于首屏；正文左对齐。控制表格列数，避免在窄屏放置并排大图。
- 文档图片保存在 `docs/assets/`，使用相对路径、明确替代文本，不复制参考项目的品牌素材。

## 维护检查

- 修改功能描述前核对路由和服务实现；区分已实现、演示适配器和规划。
- 新增截图时使用隔离的示例数据，注明截图内容，避免个人笔记、路径、密钥或真实账户资料。
- 更新版本或启动命令时同步修改 `.env.example`、开发指南及徽章。
- 检查 GitHub 深浅主题、窄屏、目录锚点、折叠区和仓库内相对链接。
