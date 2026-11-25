"""以前のサイト（QUEEEN MEDIA / WordPress）の記事を、このサイトに取り込むスクリプト。

GitHub Actions（import-queeen-media.yml）から1回だけ動かします。
- 記事本文は Markdown に変換して content/posts/ に保存
- 画像はこのリポジトリの static/imported/ にダウンロード（元サイトが無くなっても表示されるように）
"""
from __future__ import annotations

import hashlib
import html
import io
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from bs4 import BeautifulSoup
from markdownify import markdownify
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
IMG_DIR = ROOT / "static" / "imported"
BASE = "https://www.queeen-media.com"
UA = {"User-Agent": "Mozilla/5.0 (site migration)"}

# 元サイトのカテゴリ → このサイトのカテゴリ（上から順に当てはまるものを使う）
CAT_RULES = [
    (("CONTEST", "コンテスト", "インタビュー", "銚子電鉄", "鬼怒川", "AREA", "アンバサダー"), "queen"),
    (("HEALTH", "FOOD", "健康"), "wellness"),
    (("BEAUTY", "美容"), "beauty"),
    (("FASHION",), "fashion"),
    (("生き方", "キャリア", "CAREER"), "career"),
]


def pick_category(names: list[str], title: str) -> str:
    text = " ".join(names) + " " + title
    for keys, cat in CAT_RULES:
        if any(k in text for k in keys):
            return cat
    return "lifestyle"


def save_image(url: str, post_id: int) -> str | None:
    """画像をダウンロードして縮小保存。サイト内のパス（static/imported/...）を返す"""
    if not url or "wp-content/uploads" not in url:
        return None
    url = re.sub(r"-\d+x\d+(?=\.\w+$)", "", url.split("?")[0])  # サムネイルではなく元画像
    name = hashlib.md5(url.encode()).hexdigest()[:10] + ".jpg"
    dest = IMG_DIR / str(post_id) / name
    if not dest.exists():
        try:
            r = requests.get(url, headers=UA, timeout=60)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content))
            im = im.convert("RGB")
            im.thumbnail((1600, 1600))
            dest.parent.mkdir(parents=True, exist_ok=True)
            im.save(dest, "JPEG", quality=82, optimize=True)
        except Exception as e:  # noqa: BLE001
            print("  画像を取れませんでした:", url, e)
            return None
    return f"static/imported/{post_id}/{name}"


def convert(content_html: str, post_id: int) -> str:
    soup = BeautifulSoup(content_html, "html.parser")
    for t in soup(["script", "style", "iframe", "noscript", "form"]):
        t.decompose()
    for img in soup.find_all("img"):
        src = img.get("data-src") or img.get("src") or ""
        local = save_image(src, post_id)
        if local:
            img["src"] = "../" + local
            for a in ("srcset", "sizes", "data-src", "width", "height", "class", "style"):
                img.attrs.pop(a, None)
        else:
            img.decompose()
    # 画像を包んでいるリンク（元サイトの画像ページへのリンク）は外す
    for a in soup.find_all("a"):
        if a.find("img") or "wp-content/uploads" in (a.get("href") or ""):
            a.unwrap()
    md = markdownify(str(soup), heading_style="ATX", bullets="-", strip=["span", "div", "figure"])
    md = re.sub(r"^#{1,2} ", "## ", md, flags=re.M)        # 見出しのレベルをそろえる
    md = re.sub(r"^#{4,6} ", "### ", md, flags=re.M)
    md = re.sub(r"[ \t]+\n", "\n", md.replace(" ", " "))
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def main() -> None:
    posts, page = [], 1
    while True:
        r = requests.get(f"{BASE}/wp-json/wp/v2/posts", params={"per_page": 50, "page": page, "_embed": "wp:featuredmedia,wp:term"},
                         headers=UA, timeout=60)
        if r.status_code == 400:
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        posts += batch
        page += 1
        if page > int(r.headers.get("X-WP-TotalPages", 1)):
            break
    print(f"{len(posts)} 本の記事を取り込みます")
    for p in posts:
        pid = p["id"]
        title = html.unescape(BeautifulSoup(p["title"]["rendered"], "html.parser").get_text()).strip()
        terms = [t["name"] for t in (p.get("_embedded", {}).get("wp:term") or [[]])[0]]
        excerpt = BeautifulSoup(p["excerpt"]["rendered"], "html.parser").get_text(" ").strip()
        excerpt = re.sub(r"\s+", " ", re.sub(r"\[[…\.]+\]|\[&hellip;\]", "", excerpt)).strip()[:110]
        feat = ((p.get("_embedded", {}).get("wp:featuredmedia") or [{}])[0] or {}).get("source_url", "")
        body = convert(p["content"]["rendered"], pid)
        image = save_image(feat, pid)
        if not image:  # アイキャッチがなければ本文の最初の画像を使う
            m = re.search(r"\(\.\./(static/imported/[^)\s]+)\)", body)
            image = m.group(1) if m else None
        front = {
            "title": title,
            "description": excerpt or title,
            "date": p["date"][:10],
            "category": pick_category(terms, title),
            "keyword": (terms[0] if terms else "QUEEEN MEDIA")[:12],
        }
        if image:
            front["image"] = image
            front["image_credit"] = "QUEEEN MEDIA"
        front["sources"] = []
        front["origin"] = {"site": "QUEEEN MEDIA", "url": p["link"], "categories": terms}
        path = POSTS / f"{p['date'][:10]}-queeen-media-{pid}.md"
        path.write_text("---\n" + yaml.safe_dump(front, allow_unicode=True, sort_keys=False) + "---\n\n" + body + "\n",
                        encoding="utf-8")
        print(" -", path.name, front["category"], title)


if __name__ == "__main__":
    main()
