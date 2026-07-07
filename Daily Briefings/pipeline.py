# -*- coding: utf-8 -*-
"""抓取游庭皓最新直播字幕、清理成純文字，並列出「還沒做 briefing」的日期。
用法：python3 pipeline.py [要回看幾集，預設 8]
輸出：transcripts_clean/YYYYMMDD.txt（純文字），並印出 pending 日期清單。
這一步是純機械流程；真正的摘要由 AI（/briefing 指令）閱讀 transcripts_clean 後產生。"""
import os, re, sys, subprocess, glob, json

HERE = os.path.dirname(os.path.abspath(__file__))
SUB_DIR = os.path.expanduser("~/Documents/youtube-transcripts")
COOKIES = os.path.join(SUB_DIR, "www.youtube.com_cookies.txt")
CLEAN_DIR = os.path.join(HERE, "transcripts_clean")
DATA_DIR = os.path.join(HERE, "data")
CHANNEL = "https://www.youtube.com/@yutinghaofinance/streams"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8

os.makedirs(CLEAN_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def fetch():
    cmd = ["yt-dlp", "--skip-download", "--write-subs", "--write-auto-subs",
           "--sub-langs", "zh-Hant,zh-TW,zh,en",
           "--output", "%(upload_date)s_%(title)s.%(ext)s",
           "--playlist-end", str(N), CHANNEL]
    if os.path.exists(COOKIES):
        cmd[1:1] = ["--cookies", COOKIES]
    print(f"▶ 抓取最新 {N} 集字幕…")
    r = subprocess.run(cmd, cwd=SUB_DIR)
    if r.returncode != 0:
        print("⚠ yt-dlp 回傳非 0（可能被 rate-limit，等 1 小時再試，或字幕已是最新）")


def clean_vtt(fp):
    content = open(fp, encoding="utf-8").read()
    seen, res = set(), []
    for line in content.split("\n"):
        line = line.strip()
        if not line: continue
        if line.startswith(("WEBVTT", "Kind:", "Language:")): continue
        if re.match(r"[\d:\.]+\s*-->\s*[\d:\.]+", line): continue
        if re.match(r"^\d+$", line): continue
        line = re.sub(r"<[^>]+>", "", line)
        if line not in seen:
            seen.add(line); res.append(line)
    return " ".join(res)


def fetch_chapters():
    """用 metadata（不下載）抓最近 N 集的章節時間軸，回傳 {date: [(start,end,title),...]}。"""
    cmd = ["yt-dlp", "--skip-download", "--playlist-end", str(N),
           "--print", "%(upload_date)s\t%(chapters)j", CHANNEL]
    if os.path.exists(COOKIES):
        cmd[1:1] = ["--cookies", COOKIES]
    out = {}
    try:
        r = subprocess.run(cmd, cwd=SUB_DIR, capture_output=True, text=True, timeout=300)
        for line in r.stdout.splitlines():
            if "\t" not in line: continue
            date, ch = line.split("\t", 1)
            ch = ch.strip()
            if not ch.startswith("["): continue
            try:
                chaps = json.loads(ch)
            except Exception:
                continue
            out[date] = [(c.get("start_time", 0), c.get("end_time", 0), c.get("title", "")) for c in chaps]
    except Exception as e:
        print(f"⚠ 抓章節失敗（將退回整段逐字稿）：{e}")
    return out


def _ts(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def segment_vtt(fp, chapters):
    """依章節時間把 vtt 切成各段，回傳含章節標頭的純文字。"""
    cues = []
    cur = None
    for line in open(fp, encoding="utf-8").read().split("\n"):
        m = re.match(r"(\d+:\d+:\d+\.\d+)\s*-->", line.strip())
        if m:
            cur = _ts(m.group(1))
        elif line.strip() and cur is not None and not line.startswith(("WEBVTT", "Kind:", "Language:")):
            txt = re.sub(r"<[^>]+>", "", line.strip())
            if txt: cues.append((cur, txt))
    seen = set()
    buckets = {i: [] for i in range(len(chapters))}
    for t, txt in cues:
        if txt in seen: continue
        seen.add(txt)
        for i, (st, en, name) in enumerate(chapters):
            if st <= t < (en or 10**9):
                buckets[i].append(txt); break
    parts = []
    for i, (st, en, name) in enumerate(chapters):
        mm = int(st // 60); ss = int(st % 60)
        parts.append(f"===== [{mm:02d}:{ss:02d}] {name} =====\n" + " ".join(buckets[i]))
    return "\n\n".join(parts)


def main():
    fetch()
    done = {os.path.basename(p)[:8] for p in glob.glob(os.path.join(DATA_DIR, "*.json"))}
    # 只看最近抓回來的這個視窗，避免把整個歷史片庫都當成 pending
    lookback = max(N, 12)
    recent = sorted(glob.glob(os.path.join(SUB_DIR, "*.zh-TW.vtt")))[-lookback:]
    pending = []
    for fp in recent:
        d = os.path.basename(fp)[:8]
        title = os.path.basename(fp).replace(".zh-TW.vtt", "")
        outp = os.path.join(CLEAN_DIR, d + ".txt")
        if not os.path.exists(outp):
            open(outp, "w", encoding="utf-8").write(title + "\n\n" + clean_vtt(fp))
        if d not in done:
            pending.append((d, title))
    pending.sort()
    # 對 pending 日期抓章節並切段（章節版 briefing 的素材）
    if pending:
        chap_map = fetch_chapters()
        vtt_by_date = {os.path.basename(p)[:8]: p for p in recent}
        for d, _t in pending:
            if d in chap_map and d in vtt_by_date:
                seg = segment_vtt(vtt_by_date[d], chap_map[d])
                title = os.path.basename(vtt_by_date[d]).replace(".zh-TW.vtt", "")
                open(os.path.join(CLEAN_DIR, d + "_segmented.txt"), "w", encoding="utf-8").write(title + "\n\n" + seg)
                json.dump([{"time": f"{int(s//60):02d}:{int(s%60):02d}", "title": nm}
                           for s, e, nm in chap_map[d]],
                          open(os.path.join(CLEAN_DIR, d + ".chapters.json"), "w"), ensure_ascii=False, indent=1)
    print("\n=== 還沒做 briefing 的日期（pending）===")
    if not pending:
        print("（無，全部都已產出）")
    for d, t in pending[-15:]:
        seg = os.path.join("transcripts_clean", d + "_segmented.txt")
        tag = "（含章節切段）" if os.path.exists(os.path.join(HERE, seg)) else "（無章節，用整段）"
        print(f"  {d}  {seg if os.path.exists(os.path.join(HERE, seg)) else os.path.join('transcripts_clean', d+'.txt')}  {tag}  |  {t[9:55]}")
    pend = [p[0] for p in pending]
    json.dump({"pending": pend}, open(os.path.join(CLEAN_DIR, "_pending.json"), "w"))
    print(json.dumps({"pending": pend}, ensure_ascii=False))


if __name__ == "__main__":
    main()
