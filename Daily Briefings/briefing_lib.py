# -*- coding: utf-8 -*-
"""產生游庭皓《早晨財經速解讀》每日 Briefing（風格沿用 Samples 分析報告）。
每天一個 HTML 檔。內容由逐字稿（/tmp/briefing_txt）人工整理摘要而成。"""
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang TC", "Microsoft JhengHei", "Noto Sans TC", sans-serif;
  background:#f7f8fa; color:#1a2330; line-height:1.65; }
.wrap { max-width:1100px; margin:0 auto; padding:28px 24px 80px; }
.nav { font-size:12.5px; color:#6c7a8c; margin-bottom:14px; }
.nav a { color:#1a6cb1; text-decoration:none; }
.hero { background:linear-gradient(135deg,#0f3a64 0%,#14528d 60%,#1a6cb1 100%);
  color:#fff; padding:32px 30px; border-radius:16px; box-shadow:0 6px 24px rgba(15,58,100,0.18); margin-bottom:28px; }
.hero .kclose { font-size:12px; letter-spacing:2px; opacity:.8; text-transform:uppercase; }
.hero h1 { margin:6px 0 8px; font-size:24px; letter-spacing:.3px; line-height:1.4; }
.hero .sub { opacity:.9; margin:0; font-size:13.5px; }
.hero .stats { display:flex; flex-wrap:wrap; gap:14px; margin-top:22px; }
.hero .stat { background:rgba(255,255,255,0.14); padding:10px 16px; border-radius:10px; min-width:120px; }
.hero .stat .n { font-size:20px; font-weight:700; display:block; }
.hero .stat .n.up { color:#7ff0c0; } .hero .stat .n.down { color:#ffb3b3; }
.hero .stat .l { font-size:11.5px; opacity:.85; }
section { margin-bottom:30px; }
h2.section-title { font-size:19px; padding:12px 16px; border-left:5px solid #1a6cb1; background:#fff;
  border-radius:0 10px 10px 0; box-shadow:0 2px 8px rgba(0,0,0,0.04); margin-bottom:16px; }
h2.section-title small { font-weight:normal; color:#6c7a8c; font-size:13px; margin-left:8px; }
.card { background:#fff; border-radius:12px; padding:18px 22px; box-shadow:0 2px 10px rgba(0,0,0,0.05); margin-bottom:14px; }
.card h3 { margin:0 0 10px; font-size:16px; color:#14528d; }
.card p { margin:8px 0; font-size:14.5px; }
.card .lead { font-size:13.5px; color:#4a5868; margin:2px 0 14px; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media (max-width:720px){ .grid2 { grid-template-columns:1fr; } .hero h1{font-size:20px;} }
.framework-flow { display:flex; flex-direction:column; gap:8px; background:#f8fafc; padding:18px; border-radius:12px; border:1px dashed #cdd5e0; }
.flow-step { background:#fff; padding:11px 15px; border-radius:8px; display:flex; align-items:flex-start; gap:14px; border-left:4px solid #1a6cb1; box-shadow:0 1px 3px rgba(0,0,0,0.04); }
.flow-step .num { width:28px; height:28px; min-width:28px; line-height:28px; text-align:center; background:#1a6cb1; color:#fff; border-radius:50%; font-weight:700; font-size:13px; }
.flow-step .body { flex:1; font-size:14px; }
.flow-step .body strong { color:#14528d; display:block; margin-bottom:2px; }
.flow-arrow { text-align:center; color:#9aa6b3; margin:-2px 0; font-size:16px; }
.chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.chip { background:#eef3f9; color:#14528d; padding:6px 12px; border-radius:16px; font-size:12.5px; display:inline-flex; align-items:center; gap:6px; }
.chip .num { background:#14528d; color:#fff; padding:2px 7px; border-radius:10px; font-size:11px; }
.numbers { width:100%; border-collapse:collapse; font-size:13.5px; }
.numbers th, .numbers td { padding:8px 10px; border-bottom:1px solid #eef1f6; text-align:right; }
.numbers th { background:#f4f6f9; color:#14528d; text-align:right; }
.numbers td.idx { text-align:left; font-weight:600; color:#1a2330; }
.numbers td.up { color:#19945e; } .numbers td.down { color:#c0392b; }
.bigquote { background:#14528d; color:#fff; padding:22px 26px; border-radius:12px; margin:14px 0; font-size:15.5px; line-height:1.85; font-style:italic; position:relative; }
.bigquote::before { content:'\\201C'; font-size:56px; position:absolute; top:2px; left:12px; opacity:.3; }
.bigquote .author { display:block; margin-top:10px; font-style:normal; font-size:12.5px; opacity:.85; }
.insight { background:linear-gradient(135deg,#fffdf5,#fff7e0); border-left:4px solid #e6a23c; padding:14px 18px; border-radius:0 10px 10px 0; margin:10px 0; font-size:14px; }
.insight strong { color:#b86a30; }
.stocktag { display:inline-block; background:#eef3f9; color:#14528d; padding:3px 9px; border-radius:6px; font-size:12.5px; margin:2px 4px 2px 0; }
.stocktag b { color:#0f3a64; }
.kicker { font-size:11px; color:#6c7a8c; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }
footer { text-align:center; color:#9aa6b3; font-size:12px; margin-top:40px; line-height:1.8; }
"""

FRAMEWORK_NOTE = ('每日論述固定 7 步：①美股盤後＋事件鋪陳 ②歷史類比／數據回測 ③政策傳導鏈拆解 '
                  '④個股／類股配對 ⑤段子比喻穿插 ⑥台股盤前數字 ⑦週期擇時＋標準收尾。'
                  '下面照他當天的實際順序整理。')


def render(day):
    stats_html = ""
    for n, l, cls in day["stats"]:
        stats_html += f'<div class="stat"><span class="n {cls}">{n}</span><span class="l">{l}</span></div>'

    tldr_html = ""
    for label, text in day["tldr"]:
        tldr_html += f'<p><strong>{label}</strong> {text}</p>'

    sections_html = ""
    for sec in day["sections"]:
        cards = ""
        for c in sec["cards"]:
            cards += f'<div class="card"><h3>{c[0]}</h3>{c[1]}</div>'
        wrap_open = '<div class="grid2">' if sec.get("grid") else ''
        wrap_close = '</div>' if sec.get("grid") else ''
        sections_html += (f'<section><h2 class="section-title">{sec["title"]}'
                          f'{" <small>"+sec["sub"]+"</small>" if sec.get("sub") else ""}</h2>'
                          f'{wrap_open}{cards}{wrap_close}</section>')

    chain_html = ""
    if day.get("chain"):
        steps = ""
        for i, (head, ex) in enumerate(day["chain"], 1):
            steps += (f'<div class="flow-step"><div class="num">{i}</div><div class="body">'
                      f'<strong>{head}</strong>{ex}</div></div>')
            if i < len(day["chain"]):
                steps += '<div class="flow-arrow">↓</div>'
        chain_html = (f'<section><h2 class="section-title">\U0001f517 今日傳導鏈 <small>他怎麼把新聞翻成因果鏈</small></h2>'
                      f'<div class="framework-flow">{steps}</div></section>')

    num_rows = ""
    for idx, val, chg, cls in day["market"]:
        num_rows += (f'<tr><td class="idx">{idx}</td><td class="{cls}">{val}</td>'
                     f'<td class="{cls}">{chg}</td></tr>')
    market_html = (f'<section><h2 class="section-title">\U0001f4ca 數據速覽 <small>當日收盤</small></h2>'
                   f'<div class="card"><table class="numbers"><tr><th style="text-align:left">指數／資產</th>'
                   f'<th>點位／價格</th><th>漲跌</th></tr>{num_rows}</table>'
                   f'{("<p class=lead style=margin-top:12px>"+day["market_note"]+"</p>") if day.get("market_note") else ""}'
                   f'</div></section>')

    stocks_html = ""
    if day.get("stocks"):
        tags = "".join(f'<span class="stocktag">{s}</span>' for s in day["stocks"])
        stocks_html = (f'<section><h2 class="section-title">\U0001f3f7️ 點到的個股／類股</h2>'
                       f'<div class="card"><div>{tags}</div></div></section>')

    quote_html = ""
    if day.get("quote"):
        q, who = day["quote"]
        quote_html = (f'<section><h2 class="section-title">\U0001f3ad 今日招牌段子 <small>段子是他放結論的位置</small></h2>'
                      f'<div class="bigquote">{q}<span class="author">{who}</span></div></section>')

    concept_html = ""
    if day.get("concepts"):
        chips = "".join(f'<span class="chip">{c}</span>' for c in day["concepts"])
        concept_html = (f'<section><h2 class="section-title">\U0001f511 今日招牌概念詞</h2>'
                        f'<div class="card"><div class="chips">{chips}</div></div></section>')

    takeaway_html = "".join(f'<div class="insight">{t}</div>' for t in day["takeaway"])

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{day['date_disp']}（{day['wd']}）游庭皓早晨財經速解讀 Briefing</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<div class="nav">游庭皓《早晨財經速解讀》每日 Briefing</div>
<div class="hero">
  <div class="kicker">早晨財經速解讀 · 開盤前 30 分鐘</div>
  <h1>{day['headline']}</h1>
  <p class="sub">{day['date_disp']}（{day['wd']}） · 台北時間 08:30 直播 · 影片標題：{day['title']}</p>
  <div class="stats">{stats_html}</div>
</div>

<section>
<h2 class="section-title">\U0001f4cc 一句話 Briefing</h2>
<div class="card">{tldr_html}</div>
</section>

{sections_html}
{chain_html}
{market_html}
{stocks_html}
{quote_html}
{concept_html}

<section>
<h2 class="section-title">\U0001f9ed 操作心法 / 今日收斂</h2>
{takeaway_html}
</section>

<footer>
本 Briefing 依當日直播逐字稿整理摘要，僅供個人閱讀參考，非投資建議。<br>
風格與框架沿用《早晨財經速解讀》兩年分析報告。標準收尾：「祝各位投資朋友看盤順利、操盤愉快。」
</footer>
</div>
</body>
</html>"""


# ====== 索引頁 ======
import json, glob, re

def _blurb(day):
    if day.get("chapters"):
        ts=[c["title"] for c in day["chapters"]]
        pick=[t for t in ts if t not in ("市場總覽","美股追蹤","總結")][:3] or ts[:3]
        return "、".join(pick)
    titles = []
    for sec in day.get("sections", []):
        t = re.sub(r'^[^\w一-鿿]+', '', sec["title"]).strip()
        t = t.split("—")[0].split("(")[0].strip()
        if t:
            titles.append(t)
    return "、".join(titles[:3]) if titles else day.get("title", "")

def build_index(data_dir, out_dir):
    days = []
    for fp in glob.glob(os.path.join(data_dir, "*.json")):
        with open(fp, encoding="utf-8") as f:
            days.append(json.load(f))
    days.sort(key=lambda d: d["date"], reverse=True)
    cards = ""
    for d in days:
        fn = f"{d['date']}_{d['wd']}_briefing.html"
        cards += (f'<a class="card" href="{fn}"><span class="d">{d["date_disp"]}</span>'
                  f'<span class="wd">{d["wd"]}</span><h3>{d["headline"]}</h3>'
                  f'<p>{_blurb(d)}</p></a>')
    rng = ""
    if days:
        rng = f'{days[-1]["date_disp"]} – {days[0]["date_disp"]}'
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>游庭皓《早晨財經速解讀》每日 Briefing</title>
<style>
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
html, body {{ margin:0; padding:0;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Microsoft JhengHei","Noto Sans TC",sans-serif;
  background:#f7f8fa; color:#1a2330; line-height:1.65; }}
.wrap {{ max-width:1000px; margin:0 auto; padding:28px 24px 80px; }}
.topbar {{ display:flex; justify-content:flex-end; gap:8px; flex-wrap:wrap; margin-bottom:10px; }}
.topbar a {{ display:inline-flex; align-items:center; gap:6px; background:#fff; color:#14528d;
  border:1px solid #cdd9e6; border-radius:20px; padding:7px 14px; font-size:13px; font-weight:700;
  text-decoration:none; box-shadow:0 2px 8px rgba(0,0,0,0.05); transition:transform .15s, box-shadow .15s; }}
.topbar a:hover {{ transform:translateY(-1px); box-shadow:0 4px 12px rgba(0,0,0,0.1); }}
.hero {{ background:linear-gradient(135deg,#0f3a64 0%,#14528d 60%,#1a6cb1 100%);
  color:#fff; padding:34px 30px; border-radius:16px; box-shadow:0 6px 24px rgba(15,58,100,0.18); margin-bottom:28px; }}
.hero h1 {{ margin:0 0 8px; font-size:25px; }}
.hero p {{ margin:0; opacity:.9; font-size:14px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
@media (max-width:680px){{ .grid{{ grid-template-columns:1fr; }} }}
a.card {{ display:block; text-decoration:none; color:inherit; background:#fff; border-radius:12px;
  padding:18px 20px; box-shadow:0 2px 10px rgba(0,0,0,0.05); border-left:5px solid #1a6cb1;
  transition:transform .15s, box-shadow .15s; }}
a.card:hover {{ transform:translateY(-2px); box-shadow:0 6px 18px rgba(0,0,0,0.1); }}
.card .d {{ font-family:monospace; color:#6c7a8c; font-size:13px; }}
.card .wd {{ background:#14528d; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; margin-left:6px; }}
.card h3 {{ margin:8px 0 6px; font-size:15.5px; color:#14528d; line-height:1.45; }}
.card p {{ margin:0; font-size:13px; color:#4a5868; }}
footer {{ text-align:center; color:#9aa6b3; font-size:12px; margin-top:36px; }}
</style>
</head>
<body>
<div class="wrap">
<div class="topbar"><a href="https://alex-macro-dashboard.netlify.app/" target="_blank" rel="noopener">📊 總經儀表板 Macro Dashboard ↗</a><a href="./radar/" target="_blank" rel="noopener">🛰️ 質化雷達 Qual Radar ↗</a></div>
<div class="hero">
  <h1>游庭皓《早晨財經速解讀》每日 Briefing</h1>
  <p>共 {len(days)} 個平日 · {rng} · 每日直播重點，閱讀就懂</p>
</div>
<div class="grid">{cards}</div>
<footer>依當日直播逐字稿整理摘要，僅供個人閱讀參考、非投資建議。</footer>
</div>
</body>
</html>"""
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return len(days)


# ============================================================
# 章節版（chapters format）— render_chapters + 四大指數圖像化
# day schema: date,date_disp,wd,title,headline,
#   summary:[[label,text],...], indices:[{name,value,chg,pct},...],
#   indices_note(optional), chapters:[{time,title,fact,market(optional),
#     take:{stance,label,html}}], endnote(optional)
# stance ∈ agree|disagree|partial|neutral|core
# ============================================================
CSS_CH = """
:root { color-scheme: light; }
* { box-sizing:border-box; }
html,body { margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Microsoft JhengHei","Noto Sans TC",sans-serif; background:#f7f8fa; color:#1a2330; line-height:1.7; }
.wrap { max-width:1080px; margin:0 auto; padding:28px 24px 80px; }
.nav { font-size:12.5px; color:#6c7a8c; margin-bottom:12px; }
.hero { background:linear-gradient(135deg,#0f3a64 0%,#14528d 60%,#1a6cb1 100%); color:#fff; padding:30px 30px; border-radius:16px; box-shadow:0 6px 24px rgba(15,58,100,0.18); margin-bottom:22px; }
.hero .kicker { font-size:11px; letter-spacing:2px; opacity:.8; text-transform:uppercase; }
.hero h1 { margin:6px 0 8px; font-size:23px; line-height:1.4; }
.hero .sub { opacity:.9; margin:0; font-size:13.5px; }
/* 四大指數圖 */
.indices { background:#fff; border-radius:12px; padding:18px 22px 20px; box-shadow:0 2px 10px rgba(0,0,0,0.05); margin-bottom:14px; }
.indices h2 { font-size:16px; margin:0 0 14px; color:#14528d; }
.idx-row { display:grid; grid-template-columns:130px 1fr 132px; align-items:center; gap:12px; margin:9px 0; }
.idx-name { font-weight:700; font-size:14px; }
.idx-name .v { display:block; font-family:monospace; font-size:12.5px; color:#6c7a8c; font-weight:500; margin-top:1px; }
.idx-track { position:relative; height:24px; background:#f2f5f9; border-radius:6px; }
.idx-mid { position:absolute; left:50%; top:-3px; bottom:-3px; width:1px; background:#c4cdd9; }
.idx-bar { position:absolute; top:3px; height:18px; border-radius:4px; }
.idx-bar.up { background:linear-gradient(90deg,#43b985,#21895a); left:50%; }
.idx-bar.down { background:linear-gradient(270deg,#e2716b,#c0392b); right:50%; }
.idx-bar.flat { background:#9aa6b3; left:calc(50% - 2px); width:4px !important; }
.idx-chg { font-size:12.5px; font-weight:700; white-space:nowrap; text-align:left; }
.idx-chg.up { color:#19794e; } .idx-chg.down { color:#b1342f; } .idx-chg.flat { color:#6c7a8c; }
.idx-note { font-size:12.5px; color:#6c7a8c; margin:12px 0 0; }
.summary { background:#fff; border-radius:12px; padding:20px 24px; box-shadow:0 2px 10px rgba(0,0,0,0.05); margin-bottom:14px; }
.summary h2 { font-size:18px; margin:0 0 12px; color:#14528d; }
.summary p { margin:10px 0; font-size:14.5px; }
.summary b { color:#0f3a64; }
.toc { background:#fff; border-radius:12px; padding:14px 18px; box-shadow:0 2px 10px rgba(0,0,0,0.05); margin-bottom:24px; font-size:13px; }
.toc b { color:#14528d; }
.toc a { color:#1a6cb1; text-decoration:none; }
.toc a:hover { text-decoration:underline; }
.chapter { background:#fff; border-radius:14px; box-shadow:0 2px 12px rgba(0,0,0,0.06); margin-bottom:18px; overflow:hidden; }
.chapter > .head { display:flex; align-items:center; gap:12px; padding:14px 20px; background:linear-gradient(90deg,#eef4fa,#fff); border-left:6px solid #1a6cb1; }
.chapter > .head .time { font-family:monospace; font-size:13px; color:#fff; background:#14528d; padding:3px 9px; border-radius:6px; }
.chapter > .head .num { font-size:13px; color:#9aa6b3; font-weight:700; }
.chapter > .head h3 { margin:0; font-size:17px; color:#14528d; }
.chapter .body { padding:6px 20px 18px; }
.layer { display:grid; grid-template-columns:128px 1fr; gap:14px; padding:13px 0; border-top:1px dashed #e6ebf2; }
.layer:first-child { border-top:none; }
.layer .tag { font-size:12.5px; font-weight:700; padding-top:2px; }
.layer .tag .ico { display:block; font-size:18px; margin-bottom:2px; }
.layer.fact .tag { color:#2a6aa6; }
.layer.market .tag { color:#b86a30; }
.layer.take .tag { color:#1f7a52; }
.layer .content { font-size:14.5px; }
.layer .content p { margin:0 0 8px; } .layer .content p:last-child { margin-bottom:0; }
.layer .content b { color:#0f3a64; }
.layer.take { background:#f5fbf8; border-radius:8px; margin:6px -10px 0; padding:13px 12px; border-top:none; }
.stance { display:inline-block; font-size:12px; font-weight:700; padding:2px 10px; border-radius:20px; margin-bottom:6px; }
.stance.agree { background:#e2f5ec; color:#19794e; border:1px solid #9ed9bb; }
.stance.disagree { background:#fde8e8; color:#b1342f; border:1px solid #f0a9a6; }
.stance.partial { background:#fdefd8; color:#a86a1c; border:1px solid #f0c585; }
.stance.neutral { background:#eef1f6; color:#51607a; border:1px solid #cfd7e3; }
.stance.core { background:#e7eefc; color:#2f51b0; border:1px solid #adc1f0; }
.bigquote { background:#14528d; color:#fff; padding:16px 22px; border-radius:10px; margin:8px 0 0; font-size:14.5px; font-style:italic; }
.endnote { background:linear-gradient(135deg,#fffdf5,#fff7e0); border-left:4px solid #e6a23c; padding:14px 18px; border-radius:0 10px 10px 0; margin:18px 0 0; font-size:14px; }
.endnote b { color:#b86a30; }
footer { text-align:center; color:#9aa6b3; font-size:12px; margin-top:36px; line-height:1.8; }
@media (max-width:680px){ .layer{ grid-template-columns:1fr; gap:4px; } .layer .tag .ico{ display:inline; margin-right:4px; } .idx-row{ grid-template-columns:84px 1fr 92px; gap:8px; } .idx-name{ font-size:13px; } }
"""

def _indices_block(indices, note=""):
    if not indices: return ""
    mx = max((abs(float(i.get("pct", 0))) for i in indices), default=1) or 1
    rows = ""
    for i in indices:
        pct = float(i.get("pct", 0))
        d = "up" if pct > 0 else ("down" if pct < 0 else "flat")
        bw = round(abs(pct) / mx * 44, 1)
        if d == "up":
            bar = f'<div class="idx-bar up" style="width:{bw}%"></div>'
        elif d == "down":
            bar = f'<div class="idx-bar down" style="width:{bw}%"></div>'
        else:
            bar = '<div class="idx-bar flat"></div>'
        rows += (f'<div class="idx-row"><div class="idx-name">{i["name"]}<span class="v">{i["value"]}</span></div>'
                 f'<div class="idx-track"><div class="idx-mid"></div>{bar}</div>'
                 f'<div class="idx-chg {d}">{i["chg"]}</div></div>')
    note_html = f'<p class="idx-note">{note}</p>' if note else ''
    return f'<div class="indices"><h2>📊 當日四大指數收盤</h2>{rows}{note_html}</div>'

def render_chapters(day):
    summ = "".join(f'<p><b>{lab}</b> {txt}</p>' for lab, txt in day.get("summary", []))
    summary_html = f'<div class="summary"><h2>📌 一句話 Briefing</h2>{summ}</div>' if summ else ''
    idx_html = _indices_block(day.get("indices", []), day.get("indices_note", ""))
    toc = " · ".join(f'<a href="#c{n}">{c["time"]} {c["title"]}</a>' for n, c in enumerate(day["chapters"], 1))
    toc_html = f'<div class="toc"><b>章節導覽：</b>{toc}</div>'
    chaps = ""
    for n, c in enumerate(day["chapters"], 1):
        layers = (f'<div class="layer fact"><div class="tag"><span class="ico">📊</span>市場資訊</div>'
                  f'<div class="content">{c["fact"]}</div></div>')
        if c.get("market"):
            mlabel = c.get("market_label", "市場觀點")
            layers += (f'<div class="layer market"><div class="tag"><span class="ico">💬</span>{mlabel}</div>'
                       f'<div class="content">{c["market"]}</div></div>')
        tk = c["take"]
        layers += (f'<div class="layer take"><div class="tag"><span class="ico">🧠</span>他的解讀</div>'
                   f'<div class="content"><span class="stance {tk["stance"]}">{tk["label"]}</span>{tk["html"]}</div></div>')
        chaps += (f'<div class="chapter" id="c{n}"><div class="head"><span class="time">{c["time"]}</span>'
                  f'<span class="num">{n:02d}</span><h3>{c["title"]}</h3></div><div class="body">{layers}</div></div>')
    endnote = f'<div class="endnote">💡 <b>讀法提示</b>：{day["endnote"]}</div>' if day.get("endnote") else ''
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{day['date_disp']}（{day['wd']}）游庭皓 早晨財經速解讀 Briefing</title>
<style>{CSS_CH}</style>
</head>
<body>
<div class="wrap">
<div class="nav">游庭皓《早晨財經速解讀》每日 Briefing</div>
<div class="hero">
  <div class="kicker">早晨財經速解讀 · 開盤前 30 分鐘</div>
  <h1>{day['headline']}</h1>
  <p class="sub">{day['date_disp']}（{day['wd']}） · 影片標題：{day['title']}</p>
</div>
{idx_html}
{summary_html}
{toc_html}
{chaps}
{endnote}
<footer>
本 Briefing 依當日直播逐字稿（含 YouTube 章節時間軸）整理摘要，僅供個人閱讀參考、非投資建議。<br>
標準收尾：「祝各位投資朋友看盤順利、操盤愉快。」
</footer>
</div>
</body>
</html>"""

# 分派：有 chapters 用新版型，否則沿用舊版（向後相容）
_render_legacy = render
def render(day):
    if day.get("format") == "chapters" or day.get("chapters"):
        return render_chapters(day)
    return _render_legacy(day)
