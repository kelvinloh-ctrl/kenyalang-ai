#!/bin/bash
# Kenyalang.AI · B2 · Mac local fetcher runner
# 由 ~/Library/LaunchAgents/com.kelvinloh.kenyalang-fetcher.plist 触发
# 每天 MYT 6:30am 跑 · 抓完 push · 给 7am routine 用
#
# Setup:
#   chmod +x _routine/run-fetcher-local.sh
#   cp _routine/com.kelvinloh.kenyalang-fetcher.plist ~/Library/LaunchAgents/
#   launchctl load ~/Library/LaunchAgents/com.kelvinloh.kenyalang-fetcher.plist
#
# 测试一次：
#   launchctl start com.kelvinloh.kenyalang-fetcher
#   tail -f ~/Library/Logs/kenyalang-fetcher.log
#
# 取消：
#   launchctl unload ~/Library/LaunchAgents/com.kelvinloh.kenyalang-fetcher.plist

set -e

REPO=~/Desktop/Kelvin-Projects/kenyalang-ai
LOG=~/Library/Logs/kenyalang-fetcher.log

# ensure log dir
mkdir -p ~/Library/Logs

echo "============================================================" >> "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] B2 fetcher kickoff" >> "$LOG"

cd "$REPO" || { echo "FATAL: cd $REPO failed" >> "$LOG"; exit 1; }

# 1. sync repo (in case routine pushed something overnight)
git pull origin main >> "$LOG" 2>&1 || {
  echo "WARN: git pull failed, continuing with local state" >> "$LOG"
}

# 2. ensure pyyaml + feedparser
/usr/bin/env python3 -c "import yaml, feedparser" 2>/dev/null || {
  echo "[$(date '+%H:%M:%S')] installing pyyaml + feedparser" >> "$LOG"
  /usr/bin/env python3 -m pip install pyyaml feedparser --quiet --user >> "$LOG" 2>&1
}

# 3. run fetcher
echo "[$(date '+%H:%M:%S')] running fetcher.py" >> "$LOG"
/usr/bin/env python3 fetcher.py >> "$LOG" 2>&1

# 4. commit + push
git add candidates.json fetch-log.json seen.json >> "$LOG" 2>&1
git -c user.email="kelvin-mac-fetcher@kelvinloh.my" \
    -c user.name="Kelvin Mac Fetcher" \
    commit -m "B2-fetch: $(TZ=Asia/Kuala_Lumpur date +%Y-%m-%d) candidates" >> "$LOG" 2>&1 || {
  echo "[$(date '+%H:%M:%S')] no changes to commit (probably already today)" >> "$LOG"
}
git push origin main >> "$LOG" 2>&1 || {
  echo "ERR: git push failed" >> "$LOG"
  exit 1
}

# 5. 同步最新 brief/周报 → Obsidian 财经仪表盘（~/Brain · iCloud · 手机可见）
echo "[$(date '+%H:%M:%S')] syncing to Obsidian vault" >> "$LOG"
bash "$REPO/_routine/sync-to-obsidian.sh" >> "$LOG" 2>&1 || echo "WARN: obsidian sync failed" >> "$LOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] B2 fetcher DONE · pushed + synced to Obsidian" >> "$LOG"
