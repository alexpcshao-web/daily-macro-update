# -*- coding: utf-8 -*-
"""讀取 data/*.json，渲染所有每日 briefing HTML + index.html。
新增一天：在 data/ 放一個 YYYYMMDD.json（結構見任一現有檔），再跑 python3 build.py。"""
import os, json, glob
from briefing_lib import render, build_index

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

def main():
    n = 0
    for fp in sorted(glob.glob(os.path.join(DATA, "*.json"))):
        with open(fp, encoding="utf-8") as f:
            day = json.load(f)
        out = os.path.join(HERE, f"{day['date']}_{day['wd']}_briefing.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(render(day))
        n += 1
    total = build_index(DATA, HERE)
    print(f"✅ 已渲染 {n} 份 briefing，index.html 共 {total} 天")

if __name__ == "__main__":
    main()
