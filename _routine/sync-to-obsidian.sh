#!/bin/bash
# Kenyalang.AI · 同步最新 brief/周报 → Obsidian 财经仪表盘（~/Brain · iCloud · 手机可见）
# 2026-06-17 建 · ADR: ~/Brain/02_Decisions/2026-06-17-kenyalang-intel-system-redesign.md
# 由 run-fetcher-local.sh 末尾调用 · 也可单独跑：bash _routine/sync-to-obsidian.sh

REPO=~/Desktop/Kelvin-Projects/kenyalang-ai
VAULT=~/Brain/_财经数据

# 先拉最新（含远程 routine 写的 daily/weekly）
git -C "$REPO" pull origin main >/dev/null 2>&1 || true

mkdir -p "$VAULT/daily" "$VAULT/weekly"

# markdown 很小 · 全量镜像进 vault（iCloud 自动同步到手机）
cp "$REPO"/daily/*.md  "$VAULT/daily/"  2>/dev/null || true
cp "$REPO"/weekly/*.md "$VAULT/weekly/" 2>/dev/null || true

# 文件名是 YYYY-MM-DD · 按名排序取最新（cp 会改 mtime 故不用 -t）
latest_daily=$(ls "$VAULT"/daily/*.md  2>/dev/null | sort | tail -1)
latest_weekly=$(ls "$VAULT"/weekly/*.md 2>/dev/null | sort | tail -1)
echo "[obsidian-sync] daily=$(basename "${latest_daily:-none}") · weekly=$(basename "${latest_weekly:-none}")"
