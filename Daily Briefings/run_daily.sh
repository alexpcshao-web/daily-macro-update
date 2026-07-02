#!/bin/zsh
# 每個平日由 launchd 觸發。流程：
#   1) 抓最新字幕 + 清理（不需登入）
#   2) 找出最新一個還沒做的日期
#   3a) 若有 token（~/.claude/briefing_token）→ 用 claude 無頭模式自動產生（全自動）
#   3b) 若沒有 token → 跳出 macOS 通知，提醒你開 Claude Code 跑 /briefing（半自動）
#
# 手動測試：DRYRUN=1 ./run_daily.sh   （只跑機械流程，不呼叫 claude）
# 全自動需要：claude setup-token → 把 token 存到 ~/.claude/briefing_token（chmod 600）
set -u
DIR="/Users/shaopinquan/Documents/Daily Macro Update/Daily Briefings"
export PATH="/Users/shaopinquan/.local/bin:/opt/anaconda3/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
TOKEN_FILE="$HOME/.claude/briefing_token"
cd "$DIR" || exit 1
mkdir -p logs
LOG="$DIR/logs/run_$(date +%Y%m%d_%H%M).log"
exec >> "$LOG" 2>&1
echo "=== $(date) 開始 ==="

notify() { osascript -e "display notification \"$2\" with title \"$1\" sound name \"Glass\"" 2>/dev/null; }

# 1) 抓字幕 + 清理 + 算出 pending
python3 pipeline.py 8

# 2) 只看「最新一集」是否還沒做（避免被舊的回補缺口卡住）
NEWEST=$(python3 -c "
import os, glob, json
sub = os.path.expanduser('~/Documents/youtube-transcripts')
vtts = sorted(glob.glob(os.path.join(sub, '*.zh-TW.vtt')))
latest = os.path.basename(vtts[-1])[:8] if vtts else ''
done = os.path.exists(os.path.join('data', latest + '.json')) if latest else True
print('' if (not latest or done) else latest)
")
if [ -z "$NEWEST" ]; then
  echo "最新一集已產生（或無新集），結束。"
  echo "=== $(date) 結束 ==="
  exit 0
fi
TXT="transcripts_clean/$NEWEST.txt"
echo "要產生：$NEWEST （$TXT）"

# 3) 有 token → 全自動；沒有 → 通知半自動
if [ ! -s "$TOKEN_FILE" ] && [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  echo "找不到 $TOKEN_FILE，改用半自動：發通知提醒手動跑 /briefing。"
  notify "今日 Briefing 字幕已備好" "請開 Claude Code 輸入 /briefing 產生 $NEWEST 的內容"
  echo "=== $(date) 結束 ==="
  exit 0
fi
[ -s "$TOKEN_FILE" ] && export CLAUDE_CODE_OAUTH_TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"

SEG="transcripts_clean/${NEWEST}_segmented.txt"
[ -s "$SEG" ] || SEG="$TXT"
read -r -d '' PROMPT <<EOF
你要產生游庭皓《早晨財經速解讀》$NEWEST 這天的每日 briefing（章節版）。
工作目錄就是現在所在的 Daily Briefings 資料夾。步驟：
1. 完整讀 $SEG （若是 *_segmented.txt，內含 ===== [MM:SS] 章節名 ===== 標頭，照章節分段）。
2. 比照 data/20260624.json 的章節 schema（"format":"chapters"）產生 data/$NEWEST.json：頂層 format/date/date_disp/wd/title/headline；indices（道瓊/標普/納指/費半/台股，每筆 name,value,chg,pct 數字跌為負）；indices_note；summary（一句話 Briefing 3 點）；chapters（照章節順序，每段 fact＝📊市場資訊、market＋market_label＝💬市場觀點(選填)、take{stance∈agree|disagree|partial|neutral|core, label 徽章文字, html}＝🧠他的解讀）；endnote 選填。
3. 寫作靈魂：講清楚他對每個資訊/觀點是同意/反對/部分同意，以及「為什麼」(他的反駁或支持邏輯)。招牌段子放進該段 take 的 html(可用 <div class="bigquote">)。忠於逐字稿、用他的框架。date 用 $NEWEST、date_disp 與 wd 依日期填。
4. 執行 python3 build.py 重新渲染。
5. 只回一句完成訊息。
EOF

if [ "${DRYRUN:-0}" = "1" ]; then
  echo "[DRYRUN] 將以全自動模式呼叫 claude -p（略過實際呼叫）"
else
  echo "$PROMPT" | claude -p \
    --permission-mode bypassPermissions \
    --max-budget-usd 1.50 \
    --output-format text
  if [ -f "data/$NEWEST.json" ]; then
    ./publish.sh
    notify "今日 Briefing 已上線" "$NEWEST 完成 → https://alexpcshao-web.github.io/daily-macro-update/"
  else
    notify "Briefing 自動產生失敗" "$NEWEST 未產生，請手動跑 /briefing 或檢查 token"
  fi
fi

echo "=== $(date) 結束 ==="
