# 项目合集

七个项目，各自独立可运行。每个项目的提交历史完整保留，可单独检出使用。

## 项目索引

| 项目 | 目录 | 技术栈 | 说明 |
|---|---|---|---|
| 直播带货话术助手 | [`livestream/`](./livestream) | LangGraph + FastAPI + Vue 3 + ChromaDB | 实时弹幕 → 意图识别 → RAG 检索 → 话术与策略推送 |
| 企业级差旅助手 | [`travel/`](./travel) | LangGraph + FastAPI + React | 多智能体行程规划 / 预订 / 实时监控 |
| 企业知识库问答 | [`knowledge/`](./knowledge) | RAG + 向量检索 + 重排序 | DOCX/PDF 批量入库、多轮对话记忆、JWT 权限 |
| 跨境电商智能平台 | [`ecommerce/`](./ecommerce) | FastAPI + Vue 3 + RAG | 智能客服 / 营销文案 / 实时翻译 |
| 个人主页 | [`homepage/`](./homepage) | 单文件 HTML | 主页 / 术语小词典 / 技术详解 |
| 简历构建管线 | [`resume/`](./resume) | Python + Jinja2 + Headless Chrome | YAML 单一数据源 → HTML → PDF，带结构与页数校验 |
| 手机号识别工具 | [`phone-ocr/`](./phone-ocr) | 单文件 HTML + Tesseract.js | 截图批量 OCR 提取手机号，号段校验 + 运营商标注 + 多站查询 |

## 说明

- 每个目录是一个独立项目，启动方式、环境变量与依赖见其目录内的 README。
- 各项目历史保留在提交历史中，`git log --follow <路径>` 可追溯完整开发过程。

## 其他目录

| 目录 | 内容 |
|---|---|
| [`skill/`](./skill) | 可复用的工作流技能。当前包含 `github-repo-merge`：把多个仓库合并进一个承载仓库、保留各自提交历史与承载仓库创建时间的完整方法论 |
