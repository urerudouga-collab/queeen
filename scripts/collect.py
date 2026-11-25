"""話題を集めるスクリプト。

config.yaml のキーワードで Google ニュースを検索し、最近の見出しを data/candidates.json に保存します。
本文はコピーせず、見出し・配信元・リンクだけを集めます。

使い方:  python scripts/collect.py
"""
from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "candidates.json"
JST = timezone(timedelta(hours=9))
MAX_AGE_DAYS = 10
PER_KEYWORD = 8


def used_urls() -> set[str]:
    """これまでの記事で参考にしたURL（同じ話題を繰り返さないため）"""
    urls = set()
    for p in (ROOT / "content" / "posts").glob("*.md"):
        front = p.read_text(encoding="utf-8").split("---", 2)[1]
        for s in (yaml.safe_load(front) or {}).get("sources", []) or []:
            urls.add(s.get("url"))
    return urls


def fetch(keyword: str) -> list[dict]:
    q = urllib.parse.quote(f"{keyword} when:{MAX_AGE_DAYS}d")
    feed = feedparser.parse(f"https://news.google.com/rss/search?q={q}&hl=ja&gl=JP&ceid=JP:ja")
    items = []
    for e in feed.entries[:PER_KEYWORD]:
        site = e.get("source", {}).get("title", "")
        title = e.title
        if site and title.endswith(f" - {site}"):
            title = title[: -len(site) - 3]
        items.append({
            "title": title,
            "site": site,
            "url": e.link,
            "published": e.get("published", ""),
            "keyword": keyword,
        })
    return items


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    seen = used_urls()
    result = {"collected_at": datetime.now(JST).isoformat(), "categories": {}}
    for key, cat in cfg["categories"].items():
        items, titles = [], set()
        for kw in cat["keywords"]:
            for it in fetch(kw):
                if it["url"] in seen or it["title"] in titles:
                    continue
                titles.add(it["title"])
                items.append(it)
        result["categories"][key] = items
        print(f"{cat['name']}: {len(items)}件")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
