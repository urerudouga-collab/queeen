"""SNSでシェアしたときに出る画像（OGP画像 1200x630）を作るスクリプト。

使い方:  python3 scripts/make_ogp.py        … まだ画像がない記事だけ作る
         python3 scripts/make_ogp.py --all  … 全部作り直す
（Node.js と Playwright が必要。作った画像は static/ogp/ に保存されます）
"""
from __future__ import annotations

import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "ogp"
STATIC = (ROOT / "static").as_uri()

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500'
         '&family=Shippori+Mincho:wght@600;700&display=block" rel="stylesheet">')

CSS = """
*{margin:0;box-sizing:border-box}
body{width:1200px;height:630px;overflow:hidden;font-family:'Shippori Mincho',serif;color:#fff;
 background:radial-gradient(120% 140% at 15% 0%,#ff4fa0 0%,#ff0078 38%,#c8005f 72%,#7a003a 100%);position:relative}
.pat{position:absolute;inset:-60px;opacity:.09;background:url(STATIC/tiara2.svg) 0 0/170px 92px repeat;transform:rotate(-8deg)}
.rib{position:absolute;opacity:.22}
.r1{right:-120px;top:-150px;width:620px;transform:rotate(14deg)}
.r2{left:-150px;bottom:-230px;width:520px;transform:rotate(-18deg) scaleX(-1);opacity:.14}
.frame{position:absolute;inset:28px;border:1.5px solid rgba(255,255,255,.55)}
.in{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 110px}
.tiara{width:150px;filter:drop-shadow(0 3px 8px rgba(90,0,40,.35))}
.brand{font-family:'Cormorant Garamond',serif;font-weight:500;letter-spacing:.2em;line-height:1}
.mag{font-family:'Cormorant Garamond',serif;font-style:italic;letter-spacing:.12em}
.cat{font-family:'Cormorant Garamond',serif;font-weight:600;letter-spacing:.35em;font-size:26px;margin:22px 0 18px;
 padding:6px 22px;border:1px solid rgba(255,255,255,.8);border-radius:40px}
.title{font-weight:700;font-size:var(--fs);line-height:1.5;letter-spacing:.04em;text-wrap:balance;text-shadow:0 2px 14px rgba(90,0,40,.35)}
.foot{position:absolute;bottom:54px;left:0;right:0;text-align:center;font-family:'Cormorant Garamond',serif;letter-spacing:.3em;font-size:24px}
.foot img{width:40px;vertical-align:-6px;margin-right:12px}
""".replace("STATIC", STATIC)


def page(inner: str) -> str:
    return (f'<!doctype html><html lang="ja"><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>'
            f'<div class="pat"></div><img class="rib r1" src="{STATIC}/ribbon-white.png"><img class="rib r2" src="{STATIC}/ribbon-white.png">'
            f'<div class="frame"></div>{inner}</body></html>')


def default_page(cfg: dict) -> str:
    s = cfg["site"]
    return page(f'<div class="in"><img class="tiara" src="{STATIC}/tiara2.svg" style="width:190px">'
                f'<div class="brand" style="font-size:150px;margin-top:6px">QUEEEN</div>'
                f'<div class="mag" style="font-size:52px;margin-top:4px">magazine</div>'
                f'<div style="font-size:28px;letter-spacing:.3em;margin-top:28px">{html.escape(s["subtitle"])}</div></div>')


def post_page(cfg: dict, meta: dict) -> str:
    title = meta["title"]
    fs = 62 if len(title) <= 22 else 54 if len(title) <= 32 else 46
    cat = cfg["categories"][meta["category"]]["en"]
    return page(f'<div class="in" style="padding-bottom:40px"><img class="tiara" src="{STATIC}/tiara2.svg" style="width:110px">'
                f'<div class="cat">{html.escape(cat)}</div>'
                f'<div class="title" style="--fs:{fs}px">{html.escape(title)}</div></div>'
                f'<div class="foot"><img src="{STATIC}/tiara2.svg">QUEEEN MAGAZINE</div>')


def main() -> None:
    redo = "--all" in sys.argv
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    jobs = []
    if redo or not (OUT / "default.jpg").exists():
        (tmp / "default.html").write_text(default_page(cfg), encoding="utf-8")
        jobs.append({"html": str(tmp / "default.html"), "out": str(OUT / "default.jpg")})
    for p in sorted((ROOT / "content" / "posts").glob("*.md")):
        out = OUT / f"{p.stem}.jpg"
        if out.exists() and not redo:
            continue
        meta = yaml.safe_load(p.read_text(encoding="utf-8").split("---", 2)[1])
        (tmp / f"{p.stem}.html").write_text(post_page(cfg, meta), encoding="utf-8")
        jobs.append({"html": str(tmp / f"{p.stem}.html"), "out": str(out)})
    if not jobs:
        print("新しく作る画像はありません")
        return
    (tmp / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
    subprocess.run(["node", str(ROOT / "scripts" / "ogp_render.js"), str(tmp / "jobs.json")], check=True)
    print(f"OGP画像を {len(jobs)} 枚作りました")


if __name__ == "__main__":
    main()
