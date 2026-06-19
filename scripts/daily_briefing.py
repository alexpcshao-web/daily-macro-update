#!/usr/bin/env python3
"""
每日簡報生成器
抓取游庭皓最新直播字幕 → Gemini 分析 → 輸出 HTML → git push
"""

import os
import re
import subprocess
import json
import glob
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from google import genai
from google.genai import types

# ── 常數 ──────────────────────────────────────────────────────────────────────
CHANNEL_URL = "https://www.youtube.com/@yutinghaofinance/streams"
REPO_ROOT = Path(__file__).parent.parent
OUTPUT_HTML = REPO_ROOT / "daily_briefing.html"
GEMINI_MODEL = "gemini-2.0-flash"
TW_TZ = timezone(timedelta(hours=8))
SUB_LANGS = "zh-TW,zh-Hant,zh-Hans,zh,en"


# ── 1. 抓字幕 ─────────────────────────────────────────────────────────────────
def fetch_subtitle(tmpdir: str) -> tuple[str, str]:
    """用 yt-dlp 下載最新有字幕的一集，回傳 (raw_vtt, video_title)。

    在住宅 IP（本機）上 yt-dlp 可直接下載 YouTube 字幕；雲端 IP 會被封鎖，
    所以本系統設計為在本機 launchd 排程執行。
    """
    cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE")

    # 逐集嘗試最新 5 集，找到第一個有字幕的
    for idx in range(1, 6):
        cmd = [
            "yt-dlp",
            "--playlist-items", str(idx),
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", SUB_LANGS,
            "--skip-download",
            "--ignore-no-formats-error",
            "--output", f"{tmpdir}/ep_%(id)s.%(ext)s",
            "--print", "title",
            "--no-simulate",  # --print 預設會啟用 simulate，導致不寫字幕檔
            "--no-warnings",
        ]
        if cookies_file and os.path.exists(cookies_file):
            cmd += ["--cookies", cookies_file]
        cmd.append(CHANNEL_URL)

        # 確保 deno（JS runtime，yt-dlp 解析 YouTube 必需）在 PATH 中
        env = os.environ.copy()
        for p in ("/opt/homebrew/bin", "/usr/local/bin"):
            if p not in env.get("PATH", ""):
                env["PATH"] = p + os.pathsep + env.get("PATH", "")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
        title = result.stdout.strip().splitlines()[0] if result.stdout.strip() else "未知標題"

        sub_files = sorted(glob.glob(f"{tmpdir}/ep_*.vtt"))
        if sub_files:
            print(f"✅ 字幕取得：{title}")
            return Path(sub_files[0]).read_text(encoding="utf-8"), title

        print(f"第 {idx} 集無字幕，嘗試下一集...")

    raise FileNotFoundError("最新 5 集均無可用字幕")


# ── 2. 清理 VTT ───────────────────────────────────────────────────────────────
def clean_vtt(raw: str) -> str:
    """去除時間軸、HTML 標籤、重複行，回傳純文字"""
    lines = []
    seen = set()
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        # 時間軸行：00:00:00.000 --> 00:00:02.000
        if re.match(r"^\d{2}:\d{2}:\d{2}", line):
            continue
        if line.isdigit():
            continue
        # 去除 HTML/<c> 標籤與時間內嵌標記
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return "\n".join(lines)


# ── 3. Gemini 分析 ─────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """你是一位專業的金融分析師，請根據以下游庭皓直播字幕，產生一份結構化的每日財經深度簡報。

【分析框架】游庭皓的分析順序：先看流動性（資金環境、聯準會、利率）→ 再看實體經濟（基本面數據）→ 再看情緒估值（市場情緒、籌碼面）。

【核心要求】每一個觀點都必須有完整因果鏈：「因為 A（觸發因素）→ 透過 B 機制（傳導路徑）→ 導致 C 結果（預期影響）」，並標明時間維度（短期 1-4 週 / 中期 1-3 月 / 長期 3月+）。

【字幕內容】
{transcript}

---

請嚴格以下列 JSON 格式回應（不要加 markdown code block，直接輸出 JSON）：

{{
  "date": "今日日期 YYYY-MM-DD",
  "hero": {{
    "title": "今日主題（15字以內）",
    "summary": "一句話總結（30字以內）",
    "cycle_phase": "當前市場周期階段（如：升息尾聲、衰退預期、復甦初期）",
    "causal_chain_count": 整數
  }},
  "market_overview": {{
    "liquidity": "流動性環境描述（100字）",
    "real_economy": "實體經濟狀況（100字）",
    "sentiment": "市場情緒與估值（100字）"
  }},
  "causal_chains": [
    {{
      "trigger": "觸發因素",
      "mechanism": "傳導機制",
      "result": "預期結果",
      "time_lag": "時間延遲（如：2-4週）",
      "confidence": "高/中/低",
      "time_horizon": "短期/中期/長期"
    }}
  ],
  "key_indicators": [
    {{
      "name": "指標名稱",
      "reading": "當前讀數或狀態",
      "signal": "看多/看空/中性",
      "interpretation": "解讀（50字以內）"
    }}
  ],
  "sector_views": [
    {{
      "sector": "板塊或個股",
      "view": "看法",
      "reason": "因果邏輯（50字以內）",
      "timeframe": "時間框架"
    }}
  ],
  "trade_signals": {{
    "buy_conditions": ["條件1", "條件2"],
    "reduce_conditions": ["條件1", "條件2"],
    "watch_list": ["觀察項目1", "觀察項目2"]
  }},
  "contrarian_view": {{
    "main_view": "游庭皓的獨特/反向觀點（100字）",
    "risk_scenario": "最大風險情境（50字）"
  }},
  "catalysts": [
    {{
      "event": "催化劑事件",
      "date": "預計日期或時間範圍",
      "impact": "潛在影響",
      "direction": "正面/負面/雙向"
    }}
  ],
  "quote_of_day": "今日金句（直接引用游庭皓的原話，30字以內）"
}}
"""


def call_gemini(transcript: str) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY 環境變數未設定")

    client = genai.Client(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(transcript=transcript[:30000])
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    raw = response.text.strip()

    # 清除可能的 markdown code fence
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


# ── 4. 生成 HTML ──────────────────────────────────────────────────────────────
def signal_badge(signal: str) -> str:
    colors = {"看多": "#22c55e", "看空": "#ef4444", "中性": "#f59e0b"}
    color = colors.get(signal, "#94a3b8")
    return f'<span class="badge" style="background:{color}">{signal}</span>'


def confidence_badge(conf: str) -> str:
    colors = {"高": "#22c55e", "中": "#f59e0b", "低": "#ef4444"}
    color = colors.get(conf, "#94a3b8")
    return f'<span class="badge" style="background:{color}">{conf}信心</span>'


def direction_badge(direction: str) -> str:
    colors = {"正面": "#22c55e", "負面": "#ef4444", "雙向": "#a855f7"}
    color = colors.get(direction, "#94a3b8")
    return f'<span class="badge" style="background:{color}">{direction}</span>'


def build_html(data: dict, video_title: str) -> str:
    hero = data.get("hero", {})
    overview = data.get("market_overview", {})
    chains = data.get("causal_chains", [])
    indicators = data.get("key_indicators", [])
    sectors = data.get("sector_views", [])
    signals = data.get("trade_signals", {})
    contrarian = data.get("contrarian_view", {})
    catalysts = data.get("catalysts", [])
    quote = data.get("quote_of_day", "")
    report_date = data.get("date", datetime.now(TW_TZ).strftime("%Y-%m-%d"))

    # ── 因果鏈 HTML ──────────────────────────────────────────────────────────
    chains_html = ""
    for i, c in enumerate(chains, 1):
        chains_html += f"""
        <div class="chain-card">
          <div class="chain-header">
            <span class="chain-num">#{i}</span>
            {confidence_badge(c.get('confidence',''))}
            <span class="chain-time">{c.get('time_horizon','')} · {c.get('time_lag','')}</span>
          </div>
          <div class="chain-flow">
            <div class="chain-node trigger">
              <div class="node-label">觸發因素</div>
              <div class="node-content">{c.get('trigger','')}</div>
            </div>
            <div class="chain-arrow">→</div>
            <div class="chain-node mechanism">
              <div class="node-label">傳導機制</div>
              <div class="node-content">{c.get('mechanism','')}</div>
            </div>
            <div class="chain-arrow">→</div>
            <div class="chain-node result">
              <div class="node-label">預期結果</div>
              <div class="node-content">{c.get('result','')}</div>
            </div>
          </div>
        </div>"""

    # ── 指標 HTML ─────────────────────────────────────────────────────────────
    indicators_html = ""
    for ind in indicators:
        indicators_html += f"""
        <div class="indicator-card">
          <div class="indicator-header">
            <span class="indicator-name">{ind.get('name','')}</span>
            {signal_badge(ind.get('signal',''))}
          </div>
          <div class="indicator-reading">{ind.get('reading','')}</div>
          <div class="indicator-interp">{ind.get('interpretation','')}</div>
        </div>"""

    # ── 板塊 HTML ─────────────────────────────────────────────────────────────
    sectors_html = ""
    for s in sectors:
        sectors_html += f"""
        <div class="sector-card">
          <div class="sector-name">{s.get('sector','')}</div>
          <div class="sector-view">{s.get('view','')}</div>
          <div class="sector-reason">{s.get('reason','')}</div>
          <div class="sector-tf">⏱ {s.get('timeframe','')}</div>
        </div>"""

    # ── 操作訊號 HTML ──────────────────────────────────────────────────────────
    def list_items(items):
        return "".join(f"<li>{x}</li>" for x in items)

    # ── 催化劑 HTML ───────────────────────────────────────────────────────────
    catalysts_html = ""
    for cat in catalysts:
        catalysts_html += f"""
        <div class="catalyst-card">
          <div class="catalyst-header">
            {direction_badge(cat.get('direction',''))}
            <span class="catalyst-date">{cat.get('date','')}</span>
          </div>
          <div class="catalyst-event">{cat.get('event','')}</div>
          <div class="catalyst-impact">{cat.get('impact','')}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>每日財經簡報 {report_date}</title>
  <style>
    :root {{
      --bg: #0a1628;
      --card: #ffffff;
      --primary: #0f3a64;
      --accent: #1a6cb1;
      --accent2: #2d9cdb;
      --text: #1e293b;
      --muted: #64748b;
      --border: #e2e8f0;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, 'Segoe UI', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}

    /* Hero */
    .hero {{
      background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 60%, var(--accent2) 100%);
      color: white;
      padding: 48px 24px 56px;
      text-align: center;
    }}
    .hero-date {{ font-size: 0.85rem; opacity: 0.7; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 12px; }}
    .hero-title {{ font-size: clamp(1.8rem, 4vw, 2.8rem); font-weight: 800; margin-bottom: 12px; }}
    .hero-summary {{ font-size: 1.1rem; opacity: 0.9; max-width: 600px; margin: 0 auto 24px; }}
    .hero-meta {{ display: flex; justify-content: center; gap: 24px; flex-wrap: wrap; }}
    .hero-chip {{
      background: rgba(255,255,255,0.15);
      border: 1px solid rgba(255,255,255,0.3);
      border-radius: 999px;
      padding: 6px 16px;
      font-size: 0.85rem;
    }}
    .video-source {{
      margin-top: 16px;
      font-size: 0.8rem;
      opacity: 0.6;
    }}

    /* Layout */
    .container {{ max-width: 1100px; margin: 0 auto; padding: 32px 16px; }}
    .section {{ margin-bottom: 40px; }}
    .section-title {{
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--accent2);
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-bottom: 20px;
      padding-bottom: 8px;
      border-bottom: 2px solid var(--accent);
    }}

    /* Cards */
    .card {{
      background: var(--card);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }}
    .grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
    .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}

    /* Badge */
    .badge {{
      display: inline-block;
      color: white;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 999px;
    }}

    /* Market Overview */
    .overview-card .ov-label {{
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 6px;
    }}
    .overview-card p {{ font-size: 0.92rem; line-height: 1.6; color: var(--text); }}

    /* Causal Chain */
    .chain-card {{
      background: var(--card);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }}
    .chain-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }}
    .chain-num {{ font-weight: 800; color: var(--accent); font-size: 1.1rem; }}
    .chain-time {{ font-size: 0.8rem; color: var(--muted); margin-left: auto; }}
    .chain-flow {{
      display: grid;
      grid-template-columns: 1fr auto 1fr auto 1fr;
      align-items: center;
      gap: 8px;
    }}
    @media (max-width: 600px) {{
      .chain-flow {{ grid-template-columns: 1fr; }}
      .chain-arrow {{ text-align: center; transform: rotate(90deg); }}
    }}
    .chain-node {{
      border-radius: 8px;
      padding: 12px;
      font-size: 0.88rem;
    }}
    .chain-node.trigger {{ background: #fef3c7; border-left: 3px solid #f59e0b; }}
    .chain-node.mechanism {{ background: #dbeafe; border-left: 3px solid #3b82f6; }}
    .chain-node.result {{ background: #dcfce7; border-left: 3px solid #22c55e; }}
    .node-label {{ font-size: 0.7rem; font-weight: 700; opacity: 0.6; text-transform: uppercase; margin-bottom: 4px; }}
    .chain-arrow {{ text-align: center; font-size: 1.4rem; color: var(--muted); }}

    /* Indicators */
    .indicator-card {{
      background: var(--card);
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }}
    .indicator-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    .indicator-name {{ font-weight: 700; font-size: 0.95rem; }}
    .indicator-reading {{ font-size: 1.1rem; font-weight: 600; color: var(--accent); margin-bottom: 6px; }}
    .indicator-interp {{ font-size: 0.82rem; color: var(--muted); line-height: 1.5; }}

    /* Sectors */
    .sector-card {{
      background: var(--card);
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
      border-top: 3px solid var(--accent);
    }}
    .sector-name {{ font-weight: 700; font-size: 1rem; margin-bottom: 6px; color: var(--primary); }}
    .sector-view {{ font-size: 0.9rem; font-weight: 600; margin-bottom: 6px; }}
    .sector-reason {{ font-size: 0.82rem; color: var(--muted); margin-bottom: 8px; line-height: 1.5; }}
    .sector-tf {{ font-size: 0.78rem; color: var(--accent2); }}

    /* Trade Signals */
    .signals-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
    .signal-box {{ background: var(--card); border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.25); }}
    .signal-box h4 {{ font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }}
    .signal-box.buy h4 {{ color: #22c55e; }}
    .signal-box.sell h4 {{ color: #ef4444; }}
    .signal-box.watch h4 {{ color: #f59e0b; }}
    .signal-box ul {{ list-style: none; }}
    .signal-box li {{ font-size: 0.85rem; padding: 6px 0; border-bottom: 1px solid var(--border); line-height: 1.5; }}
    .signal-box li:last-child {{ border-bottom: none; }}

    /* Contrarian */
    .contrarian-card {{ background: linear-gradient(135deg, #1e1b4b, #312e81); color: white; border-radius: 12px; padding: 24px; }}
    .contrarian-card h4 {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; opacity: 0.7; margin-bottom: 12px; }}
    .contrarian-card p {{ line-height: 1.7; font-size: 0.95rem; }}
    .risk-box {{ margin-top: 16px; background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 12px; }}
    .risk-box .risk-label {{ font-size: 0.75rem; font-weight: 700; color: #fca5a5; margin-bottom: 6px; }}

    /* Catalysts */
    .catalyst-card {{
      background: var(--card);
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }}
    .catalyst-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
    .catalyst-date {{ font-size: 0.8rem; color: var(--muted); margin-left: auto; }}
    .catalyst-event {{ font-weight: 600; font-size: 0.9rem; margin-bottom: 6px; }}
    .catalyst-impact {{ font-size: 0.82rem; color: var(--muted); line-height: 1.5; }}

    /* Quote */
    .quote-card {{
      background: linear-gradient(135deg, var(--primary), var(--accent));
      color: white;
      border-radius: 16px;
      padding: 32px;
      text-align: center;
    }}
    .quote-mark {{ font-size: 3rem; opacity: 0.3; line-height: 1; margin-bottom: -8px; }}
    .quote-text {{ font-size: 1.3rem; font-weight: 600; line-height: 1.6; }}
    .quote-author {{ margin-top: 16px; font-size: 0.85rem; opacity: 0.7; }}

    /* Footer */
    footer {{ text-align: center; padding: 24px; color: rgba(255,255,255,0.3); font-size: 0.8rem; }}
  </style>
</head>
<body>

<!-- Hero -->
<div class="hero">
  <div class="hero-date">{report_date}</div>
  <div class="hero-title">{hero.get('title','每日財經簡報')}</div>
  <div class="hero-summary">{hero.get('summary','')}</div>
  <div class="hero-meta">
    <span class="hero-chip">📊 周期：{hero.get('cycle_phase','')}</span>
    <span class="hero-chip">🔗 因果鏈：{hero.get('causal_chain_count', len(chains))} 條</span>
  </div>
  <div class="video-source">來源：{video_title}</div>
</div>

<div class="container">

  <!-- 市場環境概覽 -->
  <div class="section">
    <div class="section-title">市場環境概覽</div>
    <div class="grid-3">
      <div class="card overview-card">
        <div class="ov-label">💧 流動性環境</div>
        <p>{overview.get('liquidity','')}</p>
      </div>
      <div class="card overview-card">
        <div class="ov-label">🏭 實體經濟</div>
        <p>{overview.get('real_economy','')}</p>
      </div>
      <div class="card overview-card">
        <div class="ov-label">🧠 情緒與估值</div>
        <p>{overview.get('sentiment','')}</p>
      </div>
    </div>
  </div>

  <!-- 因果邏輯鏈 -->
  <div class="section">
    <div class="section-title">因果邏輯鏈</div>
    {chains_html}
  </div>

  <!-- 關鍵指標 -->
  <div class="section">
    <div class="section-title">關鍵指標解讀</div>
    <div class="grid-3">
      {indicators_html}
    </div>
  </div>

  <!-- 板塊與個股觀點 -->
  <div class="section">
    <div class="section-title">板塊與個股觀點</div>
    <div class="grid-3">
      {sectors_html}
    </div>
  </div>

  <!-- 操作訊號 -->
  <div class="section">
    <div class="section-title">操作訊號</div>
    <div class="signals-grid">
      <div class="signal-box buy">
        <h4>✅ 買進條件</h4>
        <ul>{list_items(signals.get('buy_conditions',[]))}</ul>
      </div>
      <div class="signal-box sell">
        <h4>🔴 減倉條件</h4>
        <ul>{list_items(signals.get('reduce_conditions',[]))}</ul>
      </div>
      <div class="signal-box watch">
        <h4">👁 持續觀察</h4>
        <ul>{list_items(signals.get('watch_list',[]))}</ul>
      </div>
    </div>
  </div>

  <!-- 反向思考 -->
  <div class="section">
    <div class="section-title">反向思考</div>
    <div class="contrarian-card">
      <h4>游庭皓的獨特觀點</h4>
      <p>{contrarian.get('main_view','')}</p>
      <div class="risk-box">
        <div class="risk-label">⚠️ 最大風險情境</div>
        <div>{contrarian.get('risk_scenario','')}</div>
      </div>
    </div>
  </div>

  <!-- 近期催化劑 -->
  <div class="section">
    <div class="section-title">近期催化劑</div>
    <div class="grid-2">
      {catalysts_html}
    </div>
  </div>

  <!-- 今日金句 -->
  <div class="section">
    <div class="section-title">今日金句</div>
    <div class="quote-card">
      <div class="quote-mark">"</div>
      <div class="quote-text">{quote}</div>
      <div class="quote-author">— 游庭皓</div>
    </div>
  </div>

</div>

<footer>
  每日財經簡報 · 由 Gemini AI 分析 · {datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M")} 台北時間
</footer>
</body>
</html>"""


# ── 5. Git commit & push ──────────────────────────────────────────────────────
def git_push(paths: list[str], msg: str):
    os.chdir(REPO_ROOT)
    subprocess.run(["git", "add", *paths], check=True)
    # 沒有變更時 commit 會失敗，先檢查
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode
    if diff == 0:
        print("（無變更，略過 commit）")
        return
    subprocess.run(["git", "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)


# ── 資料檔路徑 ─────────────────────────────────────────────────────────────────
DATA_DIR = REPO_ROOT / "data"
TRANSCRIPT_FILE = DATA_DIR / "latest_transcript.txt"
META_FILE = DATA_DIR / "latest_meta.json"


# ── 模式 1：抓字幕（本機住宅 IP 執行，不需 Gemini key）────────────────────────
def run_fetch():
    print("📡 抓取字幕中...")
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_vtt, video_title = fetch_subtitle(tmpdir)
    transcript = clean_vtt(raw_vtt)
    print(f"📝 清理後字幕 {len(transcript)} 字：{video_title}")

    DATA_DIR.mkdir(exist_ok=True)
    TRANSCRIPT_FILE.write_text(transcript, encoding="utf-8")
    date_str = datetime.now(TW_TZ).strftime("%Y-%m-%d")
    META_FILE.write_text(json.dumps(
        {"title": video_title, "date": date_str}, ensure_ascii=False, indent=2
    ), encoding="utf-8")

    print("📤 推送字幕，交由 GitHub Actions 分析...")
    git_push([str(TRANSCRIPT_FILE), str(META_FILE)], f"📝 更新字幕 {date_str}")
    print("🎉 字幕已推送！")


# ── 模式 2：Gemini 分析 + 產 HTML（GitHub Actions 執行，key 為 Secret）────────
def run_analyze():
    if not TRANSCRIPT_FILE.exists():
        raise FileNotFoundError(f"找不到字幕檔 {TRANSCRIPT_FILE}")
    transcript = TRANSCRIPT_FILE.read_text(encoding="utf-8")
    meta = json.loads(META_FILE.read_text(encoding="utf-8")) if META_FILE.exists() else {}
    video_title = meta.get("title", "未知標題")
    print(f"📄 讀取字幕 {len(transcript)} 字：{video_title}")

    print("🤖 呼叫 Gemini 分析...")
    data = call_gemini(transcript)

    print("🎨 生成 HTML...")
    html = build_html(data, video_title)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"✅ 已輸出 {OUTPUT_HTML}")

    date_str = data.get("date", meta.get("date", datetime.now(TW_TZ).strftime("%Y-%m-%d")))
    print("📤 Git push...")
    git_push([str(OUTPUT_HTML)], f"📊 每日簡報 {date_str}")
    print("🎉 完成！")


# ── 模式 3：本機一條龍（需本機有 GEMINI_API_KEY）──────────────────────────────
def run_all():
    print("📡 抓取字幕中...")
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_vtt, video_title = fetch_subtitle(tmpdir)
    transcript = clean_vtt(raw_vtt)
    print(f"📝 清理後字幕 {len(transcript)} 字：{video_title}")

    print("🤖 呼叫 Gemini 分析...")
    data = call_gemini(transcript)

    print("🎨 生成 HTML...")
    html = build_html(data, video_title)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"✅ 已輸出 {OUTPUT_HTML}")

    date_str = data.get("date", datetime.now(TW_TZ).strftime("%Y-%m-%d"))
    git_push([str(OUTPUT_HTML)], f"📊 每日簡報 {date_str}")
    print("🎉 完成！")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="每日財經簡報生成器")
    parser.add_argument("mode", nargs="?", default="all",
                        choices=["fetch", "analyze", "all"],
                        help="fetch=本機抓字幕 / analyze=雲端跑Gemini / all=本機一條龍")
    args = parser.parse_args()
    {"fetch": run_fetch, "analyze": run_analyze, "all": run_all}[args.mode]()
