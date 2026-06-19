#!/bin/bash
# 本機執行 wrapper — 由 launchd 在每個平日 09:10 觸發
# 載入 .env（GEMINI_API_KEY）與 cookies，啟動 venv 跑 daily_briefing.py
set -euo pipefail

REPO="/Users/shaopinquan/Documents/Daily Macro Update"
cd "$REPO"

mkdir -p logs

# deno / git 需要在 PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# 載入本機機密（GEMINI_API_KEY）
if [ -f "$REPO/.env" ]; then
  set -a
  source "$REPO/.env"
  set +a
fi

# YouTube cookies（繞過 bot 偵測；本機住宅 IP 不會被字幕端點封鎖）
export YOUTUBE_COOKIES_FILE="$REPO/www.youtube.com_cookies.txt"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 開始執行 ====="
"$REPO/.venv/bin/python" "$REPO/scripts/daily_briefing.py"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') 完成 ====="
