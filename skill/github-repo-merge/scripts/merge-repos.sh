#!/usr/bin/env bash
# merge-repos.sh — 把多个仓库以一级子目录形式合入一个承载仓库，保留各自完整提交历史
#
# 设计约束：
#   1. 不新建仓库，承载仓库的 created_at 不变
#   2. 每个源仓库作为承载仓库根下的一个一级子目录，与其它的平级
#   3. 源仓库的完整 commit 历史随 merge 父节点带过来
#
# 用法：
#   ./merge-repos.sh <承载仓库URL> <工作目录> <源仓库名>[:<目标目录名>] [...]
#
# 示例：
#   ./merge-repos.sh https://github.com/OOP101/phone-lucky-tool.git ./work \
#       ai-livestream-sales-agent corporate-travel-assistant yaml-resume-builder:resume
#
# 执行完成后脚本只做本地 commit，推送与核验仍需手动完成：
#   cd <工作目录> && git remote set-url origin <承载仓库URL> && git push origin main
#
# 依赖：git、bash。不需要 git-subtree。

set -euo pipefail

if [ $# -lt 3 ]; then
  sed -n '2,20p' "$0"
  exit 1
fi

CARRIER_URL="$1"; shift
WORK_DIR="$1"; shift
OWNER_REPO=$(echo "$CARRIER_URL" | sed -E 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?#\1#')

if [ -d "$WORK_DIR" ]; then
  echo "工作目录已存在：$WORK_DIR" >&2
  echo "请换一个不存在的路径，或先手动删除" >&2
  exit 1
fi

echo "==> 克隆承载仓库 $OWNER_REPO"
git clone "$CARRIER_URL" "$WORK_DIR"
cd "$WORK_DIR"

MIRROR_ROOT="$(cd "$(dirname "$WORK_DIR")" && pwd)/_mirrors"
mkdir -p "$MIRROR_ROOT"

declare -a ADDED=()

for spec in "$@"; do
  SRC="${spec%%:*}"
  if [ "$SRC" = "$spec" ]; then
    TARGET="$SRC"
  else
    TARGET="${spec##*:}"
  fi

  echo ""
  echo "==> 拉取源仓库 $SRC"

  # 网络不稳时重试：间隔 10 秒，最多 20 次
  ok=0
  for i in $(seq 1 20); do
    if git clone --mirror "https://github.com/${OWNER_REPO%%/*}/$SRC.git" "$MIRROR_ROOT/$SRC.git" 2>/dev/null; then
      echo "    第 $i 次成功"
      ok=1
      break
    fi
    rm -rf "$MIRROR_ROOT/$SRC.git"
    echo "    第 $i 次失败，10 秒后重试"
    sleep 10
  done

  if [ "$ok" -eq 0 ]; then
    echo "    ❌ $SRC 拉取失败，中止（已合入的内容保留在工作目录里，可手工继续）" >&2
    exit 2
  fi

  git remote add "$SRC" "$MIRROR_ROOT/$SRC.git" 2>/dev/null || true
  git fetch -q "$SRC"

  SRC_COMMITS=$(git -C "$MIRROR_ROOT/$SRC.git" rev-list --all --count)
  SRC_FILES=$(git -C "$MIRROR_ROOT/$SRC.git" ls-tree -r --name-only main | wc -l)
  echo "    $SRC_COMMITS 个 commit，$SRC_FILES 个文件"

  # 只建立历史父子关系，不改工作树
  git merge -s ours --no-commit --allow-unrelated-histories "$SRC/main" >/dev/null 2>&1 || true
  # 把源仓库的整棵树放进目标子目录
  git read-tree --prefix="$TARGET/" -u "$SRC/main"
  git commit -q -m "feat: 合入 $SRC → $TARGET/（保留完整提交历史）"
  ADDED+=("$SRC:$TARGET:$SRC_COMMITS:$SRC_FILES")
done

echo ""
echo "==> 校验历史完整性"
FAIL=0
for entry in "${ADDED[@]}"; do
  IFS=':' read -r SRC TARGET _ _ <<< "$entry"
  missing=0
  for sha in $(git -C "$MIRROR_ROOT/$SRC.git" rev-list --all); do
    git cat-file -e "$sha" 2>/dev/null || missing=$((missing + 1))
  done
  now_count=$(git ls-tree -r --name-only HEAD -- "$TARGET/" | wc -l)
  if [ "$missing" -eq 0 ]; then
    echo "    ✅ $SRC  历史 0 缺失，目录内 $now_count 个文件"
  else
    echo "    ❌ $SRC  缺失 $missing 个 commit"
    FAIL=1
  fi
done

echo ""
echo "==> 当前根目录"
git ls-tree --name-only HEAD
echo ""
echo "commit 总数: $(git rev-list --all --count)"
echo "本地 HEAD:  $(git rev-parse HEAD)"

if [ "$FAIL" -ne 0 ]; then
  echo ""
  echo "存在校验失败项，请勿推送" >&2
  exit 3
fi

echo ""
echo "下一步（脚本不自动推送）："
echo "  cd $WORK_DIR"
echo "  git remote set-url origin $CARRIER_URL"
echo "  git remote -v            # 确认指向 GitHub，而不是本地镜像"
echo "  git push origin main"
echo ""
echo "推送后必须用独立信息源核验："
echo "  curl -s -H \"Authorization: Bearer \$TOKEN\" \\"
echo "    https://api.github.com/repos/$OWNER_REPO/git/ref/heads/main"
