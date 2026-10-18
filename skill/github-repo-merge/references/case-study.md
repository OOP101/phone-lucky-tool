# 案例：七项目合并进单一仓库（2026-10-18 实测）

## 起点

`OOP101` 账号下原本有多个独立仓库，其中六个项目分散在：

- `corporate-travel-assistant`（42 commit）
- `enterprise-knowledge-assistant`（21 commit）
- `cross-border-ecommerce-ai`（9 commit）
- `ai-livestream-sales-agent`（4 commit）
- `personal-homepage`（3 commit）
- `ai-year-one`（2 commit）
- `yaml-resume-builder`（2 commit）
- `phone-lucky-tool`（4 commit，私有）
- `buddhist-sutra-study-`（公开）

用户的核心诉求前后变化了三次，最终定稿：**以 `phone-lucky-tool` 为承载仓库**（因为它创建于 2026-08-16，是最早的一个），七个项目全部作为它的一级子目录。

## 方案返工三次的原因

| 版本 | 用户表述 | 实际做出来的 | 问题 |
|---|---|---|---|
| v1 | 「直播项目作为合并的项目根目录」 | 直播仓库根下直接放其它项目 | 直播项目自己的 `docs/`、`screenshots/` 散在根上，语义混乱 |
| v2 | 「直播项目是一个干净的项目根目录」 | 直播项目收进同名子目录 | 结构对了，但承载仓库变成今天新建的 `ai-portfolio`，创建时间变成今天 |
| v3 | 「以仓库三为主，原有项目降级为第二目录」 | 用 `phone-lucky-tool` 承载，原内容收进同名子目录 | 符合要求 |

**教训**：动手前必须先把「哪个仓库承载」「根目录长什么样」用结构树确认，不要从一句话里推断。用户提过一次「创建时间」，就意味着承载仓库不能是新建的。

## 改名事故的完整经过

目标：把 `ai-livestream-sales-agent`（含六个项目）改名为 `ai-portfolio`，但该名字被另一份旧的 `ai-portfolio` 占用。

操作：

```bash
# 第一步：腾名字
PATCH /repos/OOP101/ai-portfolio        {"name":"ai-portfolio-redundant"}   → 200
# 第二步：立刻用这个刚释放的名字
PATCH /repos/OOP101/ai-livestream-sales-agent  {"name":"ai-portfolio"}      → 200
```

结果：第二步返回 200，但 `ai-portfolio` 与 `ai-livestream-sales-agent` **双双 404**，`/user/repos` 列表里也没有该仓库。`ai-portfolio-redundant` 完好（是那份旧的四项目仓库）。

补救：本地有完整副本（87 commit），用 `POST /user/repos` 重建同名空仓库（201），再 `git push` 一次性推回（`0088aa5` 与本地一致），数据无损。

**结论**：改名到全新未使用的名字安全；改名到刚被另一次改名释放的名字会出问题。两次改名之间必须插一次 `GET /repos/...` 核验。

## 推送假成功的两种形态

### 形态一：origin 指向本地镜像

```bash
git clone ai-portfolio.git work     # origin = C:/Users/.../ai-portfolio.git
cd work && git push origin main
# 输出：To C:/Users/.../ai-portfolio.git
#       0088aa5..b2fa729  main -> main
```

日志完全正常，但推的是本地镜像，GitHub 上毫无变化。修正 `git remote set-url` 后一次推送成功。

### 形态二：推送后远程回退

第一次把合并结果推到 `ai-livestream-sales-agent`，`git push` 成功、`git ls-remote` 返回新 sha `bdb6647`。约 10 分钟后重新 clone，远程变成旧的 `0e70d33`，合并结果消失。

`git ls-tree origin/main` 当时显示的是合并后的结构，但它读的是本地 remote-tracking ref，属于自证。MCP 的 `list_commits` 也返回过旧 sha（缓存）。

**只有 `GET /repos/{owner}/{repo}/git/ref/heads/main` 可信。**

## 网络实测

同一时段内：

| 通道 | 状态 |
|---|---|
| `github.com:443`（git clone/push） | 间歇性完全不通，单次超时约 21 秒 |
| `api.github.com`（curl） | 全程可用 |

重试命中率：

- 承载仓库 `phone-lucky-tool`：第 8 次成功
- `portfolio`：第一轮 8 次全失败；单独开一轮 20 次重试，第 2 次成功
- 短间隔（5 秒）连试 6 次：全失败；间隔 10–15 秒后明显改善

## 最终结果

```
OOP101/phone-lucky-tool/          created_at = 2026-08-16 08:08 UTC（保持原值）
├── README.md                      七项目导航表
├── phone-lucky-tool/              原手机号 OCR 工具（README + index.html 26KB）
├── ai-livestream-sales-agent/
├── corporate-travel-assistant/
├── enterprise-knowledge-assistant/
├── cross-border-ecommerce-ai/
├── personal-homepage/
└── yaml-resume-builder/
```

| 校验项 | 结果 |
|---|---|
| main | `b0d4bbd`，与本地一致 |
| commit 总数 | 97 |
| 各项目历史 | 逐个 `cat-file` 验证，0 缺失 |
| 各项目文件数 | 与原仓库逐一相等 |
| 可见性 | 私有 → 公开（`PATCH {"private":false}` 返回 200） |
| created_at | 未变 |

剩余的 `portfolio` 仓库由用户自行删除（本机 token 无 `delete_repo` 权限，`DELETE` 返回 403）。
