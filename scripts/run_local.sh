#!/bin/bash
# 本機執行 wrapper — 由 launchd 在每個平日 09:10 觸發
# 載入 .env（GEMINI_API_KEY）與 cookies，啟動 venv 跑 daily_briefing.py
set -euo pipefail

REPO="/Users/shaopinquan/Documents/Daily Macro Update"
cd "$REPO"

mkdir -p logs

# deno / git 需要在 PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# YouTube cookies（繞過 bot 偵測；本機住宅 IP 不會被字幕端點封鎖）
export YOUTUBE_COOKIES_FILE="$REPO/www.youtube.com_cookies.txt"

# 只在本機抓字幕並 push；Gemini 分析交給 GitHub Actions（金鑰為雲端 Secret）
echo "===== $(date '+%Y-%m-%d %H:%M:%S') 開始抓字幕 ====="
"$REPO/.venv/bin/python" "$REPO/scripts/daily_briefing.py" fetch
echo "===== $(date '+%Y-%m-%d %H:%M:%S') 完成 ====="
