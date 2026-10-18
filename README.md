# 项目合集

七个项目，各自独立可运行。每个项目的提交历史完整保留，可单独检出使用。

## 项目索引

| 目录 | 项目 | 技术栈 | 说明 |
|---|---|---|---|
| [`ai-livestream-sales-agent/`](./ai-livestream-sales-agent) | 直播带货 AI 话术助手 | LangGraph + FastAPI + Vue 3 + ChromaDB | 实时弹幕 → 意图识别 → RAG 检索 → 话术与策略推送 |
| [`corporate-travel-assistant/`](./corporate-travel-assistant) | 企业级差旅助手 | LangGraph + FastAPI + React | 多智能体行程规划 / 预订 / 实时监控 |
| [`enterprise-knowledge-assistant/`](./enterprise-knowledge-assistant) | 企业知识库问答 | RAG + 向量检索 + 重排序 | DOCX/PDF 批量入库、多轮对话记忆、JWT 权限 |
| [`cross-border-ecommerce-ai/`](./cross-border-ecommerce-ai) | 跨境电商智能平台 | FastAPI + Vue 3 + RAG | 智能客服 / 营销文案 / 实时翻译 |
| [`personal-homepage/`](./personal-homepage) | 个人主页 | 单文件 HTML | 主页 / 术语小词典 / 技术详解 |
| [`yaml-resume-builder/`](./yaml-resume-builder) | 简历构建管线 | Python + Jinja2 + Headless Chrome | YAML 单一数据源 → HTML → PDF，带结构与页数校验 |
| [`phone-lucky-tool/`](./phone-lucky-tool) | 手机号识别与吉凶查询 | 单文件 HTML + Tesseract.js | 截图批量 OCR 提取手机号，号段校验 + 运营商标注 + 多站查询 |

## 说明

- 每个目录是一个独立项目，启动方式、环境变量与依赖见其目录内的 README。
- 各项目历史保留在提交历史中，`git log --follow <路径>` 可追溯完整开发过程。

## 其他目录

| 目录 | 内容 |
|---|---|
| [`skill/`](./skill) | 可复用的工作流技能。当前包含 `github-repo-merge`：把多个仓库合并进一个承载仓库、保留各自提交历史与承载仓库创建时间的完整方法论 |
