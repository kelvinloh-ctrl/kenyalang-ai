#!/bin/bash
# Kenyalang.AI · 全本地自动 brief 流水线（B 方案 · 无远程 secret）
# 跑在非 TCC 保护目录的克隆里（~/Library/Application Support/kenyalang-ai）
# launchd 每天 MYT 6:30am 触发（配 pmset 定时唤醒）
#
# 流程：git pull → fetcher.py 抓取 → headless claude 写 brief → 本地凭证 push
# 跟 Desktop 那份是同一个 GitHub repo · Kelvin 开电脑 git pull 就同步
#
# 装：
#   cp _routine/com.kelvinloh.kenyalang-auto.plist ~/Library/LaunchAgents/
#   launchctl load ~/Library/LaunchAgents/com.kelvinloh.kenyalang-auto.plist
# 测一次：launchctl start com.kelvinloh.kenyalang-auto

set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HOME/Library/Logs/kenyalang-auto.log"
mkdir -p "$HOME/Library/Logs"
cd "$REPO" || { echo "FATAL cd $REPO" >>"$LOG"; exit 1; }

log(){ echo "[$(TZ=Asia/Kuala_Lumpur date '+%Y-%m-%d %H:%M:%S')] $*" >>"$LOG"; }

log "============ auto-local kickoff @ $REPO ============"

# 0. 等网络就绪（开机/登录触发时 WiFi 可能还没起）
for n in 1 2 3 4 5 6; do
  curl -sf -o /dev/null --max-time 5 https://api.github.com && break
  log "等网络就绪… ($n/6)"; sleep 5
done

# 1. sync
git pull --quiet origin main >>"$LOG" 2>&1 || log "WARN git pull failed, 用本地状态继续"

# 1.5 当日守卫 —— 今天 brief 已出（6:30 跑过 / 别处 push 过）就不重复
DATE=$(TZ=Asia/Kuala_Lumpur date +%Y-%m-%d)
if [ -f "daily/${DATE}.md" ]; then
  log "今日 brief daily/${DATE}.md 已存在 · 跳过（防重复）"
  exit 0
fi

# 2. deps
/usr/bin/env python3 -c "import yaml, feedparser" 2>/dev/null || {
  log "installing pyyaml feedparser"
  /usr/bin/env python3 -m pip install pyyaml feedparser --quiet --user >>"$LOG" 2>&1
}

# 3. fetch
log "running fetcher.py"
/usr/bin/env python3 fetcher.py >>"$LOG" 2>&1 || { log "FATAL fetcher.py 失败"; exit 1; }

OUT="daily/${DATE}.md"

# 3.3 Semantic dedup · 对比历史语义相似度 · 标记 may_be_duplicate
log "running semantic-dedup.py"
/usr/bin/env python3 _routine/semantic-dedup.py >>"$LOG" 2>&1 || log "WARN semantic-dedup.py 跳过（无 API key 或异常 · 不影响 brief）"

# 3.5 Reflexion · 提取昨日自我批评
PREV_CRITIQUE=""
YESTERDAY=$(TZ=Asia/Kuala_Lumpur date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d 2>/dev/null)
PREV_BRIEF="daily/${YESTERDAY}.md"
if [ -f "$PREV_BRIEF" ]; then
  # 提取 ## 自我批评 后的第一段非空行
  PREV_CRITIQUE=$(awk '/^## 自我批评/{found=1; next} found && /^[^#]/ && NF{print; exit}' "$PREV_BRIEF")
  if [ -n "$PREV_CRITIQUE" ]; then
    log "Reflexion: 注入昨日批评 → \"${PREV_CRITIQUE:0:60}…\""
  fi
fi

# 4. headless claude 写 brief（candidates.json 内嵌进 prompt · 只要 stdout markdown · 无需工具）
log "writing brief via headless claude → $OUT"
PROMPT_TEMPLATE="$(cat _routine/v5.3-local-prompt.md)"
PROMPT="${PROMPT_TEMPLATE//\{\{PREV_CRITIQUE\}\}/$PREV_CRITIQUE}

下面是今天的 candidates.json 全文：

$(cat candidates.json)"

# perl alarm 当 timeout（macOS 无 timeout）· 上限 300s
BRIEF="$(perl -e 'alarm 300; exec @ARGV' /opt/homebrew/bin/claude -p "$PROMPT" --output-format text 2>>"$LOG")"
RC=$?

# 5. 合法性校验：必须含 brief 头（支持 YAML frontmatter 前缀），否则不写（防垃圾覆盖）
if [ $RC -ne 0 ] || ! printf '%s' "$BRIEF" | grep -q "^# Kenyalang Daily"; then
  log "FATAL claude 写 brief 失败 rc=$RC · 首行: $(printf '%s' "$BRIEF" | head -1)"
  exit 1
fi

printf '%s\n' "$BRIEF" > "$OUT"
log "brief written: $OUT ($(wc -l <"$OUT") 行)"

# 6. push（本地 keychain 凭证 · 无 PAT）· 连状态文件一起提交（持久化去重状态 + 保持工作区干净）
git add "$OUT" candidates.json fetch-log.json seen.json _routine/semantic-seen.json >>"$LOG" 2>&1
git -c user.email="kenyalang-auto@kelvinloh.my" -c user.name="Kenyalang Auto-Local" \
    commit -m "auto-local brief: ${DATE}" >>"$LOG" 2>&1 || { log "no changes to commit"; }
git push --quiet origin main >>"$LOG" 2>&1 || { log "ERR git push 失败"; exit 1; }

log "DONE · pushed $OUT to origin/main"
