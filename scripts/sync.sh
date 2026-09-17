#!/usr/bin/env bash
# sync.sh — 將 .pi/skills/meal-planner/ 同步到 .omp/ 與 .opencode/
# 用法：cd <repo-root> && bash .pi/skills/meal-planner/scripts/sync.sh
# 只同步 SKILL.md、references/、scripts/；state/ 各 runtime 獨立維護，不同步。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
SRC="$ROOT/.pi/skills/meal-planner"

for TARGET in ".omp/skills/meal-planner" ".opencode/skills/meal-planner"; do
    DEST="$ROOT/$TARGET"
    mkdir -p "$DEST"
    # 同步 SKILL.md
    cp -f "$SRC/SKILL.md" "$DEST/SKILL.md"
    # 同步 references/（整目錄）
    rm -rf "$DEST/references"
    cp -r "$SRC/references" "$DEST/references"
    # 同步 scripts/（整目錄，含本檔；cache/ 各 runtime 獨立，同步後移除）
    rm -rf "$DEST/scripts"
    cp -r "$SRC/scripts" "$DEST/scripts"
    rm -rf "$DEST/scripts/cache"
    # 不同步 state/、cache/（各 runtime 獨立）
    echo "synced: $TARGET"
done

# md5 驗證
echo "--- md5 check ---"
for TARGET in ".pi/skills/meal-planner" ".omp/skills/meal-planner" ".opencode/skills/meal-planner"; do
    MD5=$(cat "$ROOT/$TARGET/SKILL.md" | md5sum | awk '{print $1}')
    echo "$TARGET SKILL.md md5: $MD5"
done
