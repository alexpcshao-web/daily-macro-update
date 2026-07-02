#!/bin/zsh
# 把 Daily Briefings 的更新推上 GitHub Pages。/briefing 產生完會自動呼叫。
set -u
REPO="/Users/shaopinquan/Documents/Daily Macro Update"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$REPO" || exit 1
git add "Daily Briefings"
if git diff --cached --quiet; then
  echo "沒有變更、不需發佈。"; exit 0
fi
MSG="briefing: 更新 $(date +%Y-%m-%d)"
git commit -m "$MSG" >/dev/null
git push origin main && echo "✅ 已推上 GitHub Pages（約 1 分鐘後更新）：https://alexpcshao-web.github.io/daily-macro-update/"
