# AI 应用作品集

五个 AI 应用项目，各自独立可运行。每个项目的提交历史都完整保留，可单独检出使用。

## 项目索引

| 目录 | 项目 | 技术栈 | 说明 |
|---|---|---|---|
| [`ai-livestream-sales-agent/`](./ai-livestream-sales-agent) | 直播带货 AI 话术助手 | LangGraph + FastAPI + Vue 3 + ChromaDB | 实时弹幕 → 意图识别 → RAG 检索 → 话术与策略推送 |
| [`corporate-travel-assistant/`](./corporate-travel-assistant) | 企业级差旅助手 | LangGraph + FastAPI + React | 多智能体行程规划 / 预订 / 实时监控 |
| [`enterprise-knowledge-assistant/`](./enterprise-knowledge-assistant) | 企业知识库问答 | RAG + 向量检索 + 重排序 | DOCX/PDF 批量入库、多轮对话记忆、JWT 权限 |
| [`cross-border-ecommerce-ai/`](./cross-border-ecommerce-ai) | 跨境电商智能平台 | FastAPI + Vue 3 + RAG | 智能客服 / 营销文案 / 实时翻译 |
| [`personal-homepage/`](./personal-homepage) | 个人主页 | 单文件 HTML | 主页 / 术语小词典 / 技术详解 |

## 说明

- 每个目录是一个独立项目，启动方式、环境变量与依赖见其目录内的 README。
- 各项目历史保留在原分支中，`git log --follow <路径>` 可追溯完整开发过程。
