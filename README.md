# yaml-resume-builder

**YAML 驱动的中文简历构建管线：一份内容数据源，多版本简历一键生成。**
An YAML-driven resume build pipeline: single data source → Jinja2 HTML → Edge/Chrome headless PDF, with structure & page-count validation.

## 这是什么

改简历最痛的不是写内容，而是「改一处要同步 N 个版本、排版全靠手动调」。本项目把简历当成工程来做：

```
resume_data.yaml（唯一要改的文件）
    │
    ├── scripts/gen_from_data.py   渲染 Jinja2 模板 → output/*.html
    │
    └── scripts/build_all.py       一键构建：生成 + 结构校验 + 浏览器无头导出 PDF
                                        │
                                        └── output/*.pdf（自动校验页数）
```

## 特性

- **单一数据源**：所有版本共用一份 YAML，改一处全量同步，永不漏改
- **多版本 / 多方向**：`variants` 定义不同求职方向（如 AI 应用开发 / 测试开发）的内容差异，`profiles` 决定每个版本用哪个方向、哪个模板、哪些工作经历块
- **零重依赖导 PDF**：不用 LaTeX / wkhtmltopdf，本机有 Edge 或 Chrome 即可无头导出，中文排版天然友好
- **构建即校验**：div 配平、证件照数量、章节数、PDF 页数自动检查，排版炸了第一时间知道
- **结构化强调**：YAML 里写 `<span class="hl">关键指标</span>`，渲染时自动标红
- **可选附录合并**：`export_appendix.py` 把一页技术附录 PDF 合并进主简历（自动同步求职意向口径）

## 快速开始

```bash
# 1. 依赖：Python 3.8+，以及 Edge 或 Chrome（任一，走无头导出）
pip install pyyaml jinja2

# 2. 改内容：编辑 resume_data.yaml（仓库自带虚构示例「张三」）
# 3. 构建：
```

- Windows：双击 `build.bat`
- macOS / Linux：`python scripts/build_all.py`

产物在 `output/`。构建输出会列出每个文件的 div 配平 / 照片 / 章节数 / PDF 页数。

## 数据结构（resume_data.yaml）

| 字段 | 作用 |
|---|---|
| `person` | 姓名、联系方式、证件照（留空用内置占位图，也可填本地路径） |
| `education` | 教育背景 |
| `project_order` + `projects` | 项目经历；每个项目下按 variant 提供不同侧重的写法 |
| `work_blocks` | 工作经历块；profile 通过 `work` 列表挑选/组合 |
| `variants` | 各求职方向的技能 / 个人概述 / 求职意向 |
| `profiles` | 输出配置：路径、模板、variant、工作块组合、doc_title |

改模板：`resume_templates/layout_*.html.j2`（页面壳）与 `_body.html.j2`（正文骨架）。改完跑构建即可，**不要手改 `output/` 里的产物**。

## 附录合并（可选）

准备一页 `appendix/技术附录.html`，然后：

```bash
python scripts/export_appendix.py --appx appendix/技术附录.html --main output/张三_AI应用开发工程师.pdf
```

产出 `*_含项目附录.pdf`（需要 `pip install pymupdf`）。

## Windows 编码注意事项（踩坑经验）

- 含**中文**的 `.bat` 必须保存为 **GBK(ANSI) 编码 + CRLF 换行**，否则 cmd 按字节位置解析脚本时会出现时好时坏的乱码/报错（LF 换行 + goto 循环 + 多字节字符是重灾区）
- 本仓库的 `build.bat` 刻意**全 ASCII**，任何代码页下都稳定；中文提示由 Python 以 UTF-8 输出（脚本内已设 `PYTHONIOENCODING=utf-8`）

## 路线图

- [ ] 更多模板（单页紧凑版 / 中英双语版）
- [ ] 构建产物截图示例
- [ ] GitHub Actions 自动构建示例
- [ ] 腾讯/字节式长版定制模板（含导出 Markdown、页面编辑模式）

## License

[MIT](LICENSE) © OOP101
