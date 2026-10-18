---
name: github-repo-merge
description: 将多个 GitHub 仓库合并进一个承载仓库，完整保留各项目的提交历史，并保持承载仓库原有的创建时间。适用于用户提出「合并仓库」「打包成一个仓库」「保留创建时间」「多项目并到一个总目录」「把某个项目降级成子目录」等需求的场景，包含镜像备份、merge -s ours + read-tree 前缀合入、历史完整性校验、独立 API 核验，以及改名失效、推送假成功、origin 指向本地路径等已知故障的规避方法。
agent_created: true
---

# GitHub 多仓库合并与重组

把一个或多个 GitHub 仓库合并进另一个仓库，同时满足三个硬约束：

1. 每个被合并项目的**提交历史完整保留**——不是复制文件覆盖过去，`git log` 仍能看到原开发过程
2. 承载合并的仓库**保留原有的 `created_at`**——不新建仓库，新建等于把创建时间换成今天
3. 根目录整齐：只放 README 与各项目的一级子目录，任何项目都不散落在根上

## 何时使用

- 用户有多个独立项目仓库，想合并成一个作品集 / 总目录仓库
- 用户明确要求「保留创建时间」「不要新建仓库取代」
- 需要把承载仓库里的原有内容降级为子目录，与其它项目平级
- 需要在不丢失 git 历史的前提下重组目录结构

## 第一步：动远程前先确认三件事

这三件事不确定就动手，必然返工。

1. **哪个仓库承载合并**——它决定最终的 `created_at`。用户一旦提到创建时间，就绝不能用新建仓库承载。
2. **可见性冲突**——承载仓库与被并入仓库的 `private` 状态若不同，合并后只能保留一个。必须先问最终要公开还是私有。
3. **根目录结构**——根目录只放 README 与各项目一级子目录；承载仓库原本散在根上的文件也要收进同名子目录。把结构树画给用户确认后再执行。

## 第二步：镜像备份（先备份，后动手）

```bash
git clone --mirror https://github.com/OWNER/REPO.git REPO.git
```

网络不稳时按「网络」一节的策略重试。**所有仓库备份完成并校验通过后，才允许改动远程。**

校验备份：

```bash
git -C REPO.git rev-list --all --count      # commit 数
git -C REPO.git rev-parse refs/heads/main   # HEAD
git -C REPO.git fsck --no-progress          # 对象完整性
```

## 第三步：合入项目（保留历史的关键）

在承载仓库的工作副本里，对每个要并入的项目执行：

```bash
git remote add <别名> <镜像路径或 URL>
git fetch <别名>
git merge -s ours --no-commit --allow-unrelated-histories <别名>/main
git read-tree --prefix=<目标目录>/ -u <别名>/main:<源目录>
git commit -m "feat: 合入 <项目>"
```

三个细节决定成败：

- `merge -s ours` 只建立父子关系、把对方历史引入，不改动工作树
- `read-tree --prefix` 只取对方的**子目录树**放到指定前缀下，因此不会与根 README 冲突
- 一次 merge 可配多次 `read-tree`，最后一次 commit 收口，适合把多个项目合成一个提交
- **不依赖 `git subtree`**：多数环境没有这个子命令（`git subtree --help` 返回非 0 即不可用），本流程不需要它

## 第四步：校验完整性

**不要用 `git log -- <path>` 判断历史是否丢失。** 它会因 TREESAME 折叠 merge 分支，只显示 1–4 条，看起来像历史没了，实际都在。

逐个 commit 检查对象是否存在：

```bash
for sha in $(git -C ../SOURCE.git rev-list --all); do
  git cat-file -e "$sha" 2>/dev/null || echo "缺失 $sha"
done
```

文件数逐一对比：

```bash
git -C ../SOURCE.git ls-tree -r --name-only main | wc -l
git ls-tree -r --name-only HEAD -- TARGET/ | wc -l
```

## 第五步：推送并独立核验

```bash
git remote set-url origin https://github.com/OWNER/REPO.git
git remote -v          # 必须先确认指向 GitHub
git push origin main
```

核验必须走独立信息源，不看命令返回码：

```bash
TOKEN=$(printf "protocol=https\nhost=github.com\n\n" \
  | git-credential-manager get | grep '^password=' | cut -d= -f2-)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/git/ref/heads/main"
```

## 必须避开的五个坑

### 1. 从本地镜像 clone 的工作副本，origin 指向本地路径

`git clone REPO.git work` 之后 `origin` 是 `C:/path/to/REPO.git`。此时 `git push` 会返回成功，日志还打印 `old..new main -> main`，但推送目标是本地镜像，GitHub 毫无变化——一个完全合规的假成功。

推送前必须执行 `git remote set-url origin https://github.com/OWNER/REPO.git` 并用 `git remote -v` 核对。

### 2. 改名到「刚被另一次改名释放的名字」会让仓库消失

先把 A 改名腾出名字、紧接着把 B 改成该名字：第二次 PATCH 返回 200，但仓库随即 404，两个名字都查不到，`/user/repos` 列表里也没有。

- 两次改名之间必须插一次独立核验（`GET /repos/...`）
- 改名到**全新未使用的名字**是安全的，旧名会自动 301 重定向

### 3. push 显示成功不等于成功

曾出现「push 返回成功、`git ls-remote` 也返回新 sha，但稍后远程回到旧 commit」。

`git ls-tree origin/main` 读的是本地 remote-tracking ref，属于自证，不能作为核验依据；MCP 类接口也有缓存。**唯一可信的是 `GET /repos/{owner}/{repo}/git/ref/heads/main`。**

### 4. 结构调整时漏 `git add`

`git mv` 挪动已跟踪文件会自动进暂存区，但随后用 `cp` / 重定向新建的文件**不会**。commit 前用 `git status` 确认，或显式 `git add` 新文件。

### 5. 私有与公开不能共存

仓库只有一个 `private` 字段，合并后统一生效。转公开：

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
  -d '{"private":false}' https://api.github.com/repos/OWNER/REPO
```

## 网络

`github.com:443`（git 协议）会整段时段不通，而 `api.github.com`（curl）通常仍可用。

- 重试策略：间隔 10–15 秒，上限 15–20 次；短间隔连试 6 次往往全失败
- git 协议不通时，改名、可见性、描述等元数据操作仍可通过 API 完成
- 大批量文件不要走 API（逐个 blob 传 400+ 文件不现实），等 git 协议恢复再推

## 收尾

- 清理本地镜像与工作副本（可达数十 MB）
- 让用户删除已被并入的旧仓库：本机 token 通常没有 `delete_repo` 权限，`DELETE /repos/...` 返回 403 `Must have admin rights to Repository`
- 更新承载仓库的 description，使其覆盖合并后的全部项目
- 用 `GET /user/repos?per_page=100` 列出最终仓库清单，核对数量与可见性

## 配套资源

- `scripts/merge-repos.sh` — 批量合入脚本，按本流程实现，可直接执行
- `references/case-study.md` — 一次真实合并的完整记录，含三版方案返工、改名事故与最终核验数据
