"""記事ファイル（content/posts/*.md）からサイト（_site/）を作るスクリプト。

使い方:  python scripts/build.py
"""
from __future__ import annotations

import datetime as dt
import html
import shutil
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "content" / "posts"
OUT = ROOT / "_site"
WEEKDAYS = "月火水木金土日"


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def parse_post(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    meta = yaml.safe_load(front)
    meta["slug"] = path.stem
    meta["body_html"] = markdown.markdown(body.strip(), extensions=["extra", "sane_lists"])
    if isinstance(meta["date"], str):
        meta["date"] = dt.date.fromisoformat(meta["date"])
    meta.setdefault("sources", [])
    return meta


def load_posts() -> list[dict]:
    posts = [parse_post(p) for p in POSTS_DIR.glob("*.md")]
    posts = [p for p in posts if not p.get("draft")]
    return sorted(posts, key=lambda p: (p["date"], p["slug"]), reverse=True)


def jdate(d: dt.date) -> str:
    return f"{d.year}.{d.month:02d}.{d.day:02d}（{WEEKDAYS[d.weekday()]}）"


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- 部品

def eyecatch(post: dict, cfg: dict, prefix: str, size: str = "") -> str:
    cat = cfg["categories"][post["category"]]
    return (
        f'<div class="eye eye-{post["category"]} {size}">'
        f'<img class="eye-logo" src="{prefix}static/logo.png" alt="" aria-hidden="true">'
        f'<span class="eye-en">{esc(cat["en"])}</span>'
        f'<span class="eye-word">{esc(post.get("keyword", ""))}</span>'
        f"</div>"
    )


def card(post: dict, cfg: dict, prefix: str) -> str:
    cat = cfg["categories"][post["category"]]
    return f"""
<a class="card" href="{prefix}posts/{post['slug']}.html">
  {eyecatch(post, cfg, prefix)}
  <div class="card-body">
    <span class="cat">{esc(cat['name'])}</span>
    <h3>{esc(post['title'])}</h3>
    <p>{esc(post['description'])}</p>
    <time>{jdate(post['date'])}</time>
  </div>
</a>"""


def layout(cfg: dict, prefix: str, title: str, body: str, description: str = "", active: str = "") -> str:
    site = cfg["site"]
    on = ' class="on"'
    nav = "".join(
        f'<a href="{prefix}category/{key}.html"{on if key == active else ""}>{esc(c["name"])}</a>'
        for key, c in cfg["categories"].items()
    )
    full_title = f"{title} | {site['title']}" if title != site["title"] else site["title"]
    contest = (
        f'<a class="contest" href="{esc(site["contest_url"])}">ミセスクイーンコンテスト公式サイト</a>'
        if site.get("contest_url") else ""
    )
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description or site['description'])}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description or site['description'])}">
<link rel="icon" href="{prefix}static/logo.png">
<link rel="alternate" type="application/rss+xml" href="{prefix}feed.xml" title="{esc(site['title'])}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Shippori+Mincho:wght@500;700&family=Zen+Kaku+Gothic+New:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}static/style.css">
</head>
<body>
<header class="site-header">
  <a class="brand" href="{prefix}index.html">
    <img src="{prefix}static/logo.png" alt="QUEEEN">
    <span><b>{esc(site['title'])}</b><small>{esc(site['subtitle'])}</small></span>
  </a>
  <nav class="nav">{nav}</nav>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <img src="{prefix}static/logo.png" alt="">
  <p class="f-title">{esc(site['title'])}</p>
  <p>{esc(site['description'])}</p>
  <p class="f-links"><a href="{prefix}about.html">このサイトについて</a>{contest}</p>
  <p class="copy">© {dt.date.today().year} Mrs. QUEEEN</p>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------- ページ

def page_index(cfg: dict, posts: list[dict]) -> str:
    if not posts:
        return layout(cfg, "", cfg["site"]["title"], "<p class='empty'>記事は準備中です。</p>")
    top, rest = posts[0], posts[1:]
    cat = cfg["categories"][top["category"]]
    hero = f"""
<section class="hero">
  <a href="posts/{top['slug']}.html" class="hero-link">
    {eyecatch(top, cfg, "", "big")}
    <div class="hero-text">
      <span class="label">NEW</span><span class="cat">{esc(cat['name'])}</span>
      <h1>{esc(top['title'])}</h1>
      <p>{esc(top['description'])}</p>
      <time>{jdate(top['date'])}</time>
    </div>
  </a>
</section>"""
    grid = "".join(card(p, cfg, "") for p in rest[:24])
    return layout(cfg, "", cfg["site"]["title"], hero + f'<h2 class="sec">LATEST<small>新着記事</small></h2><section class="grid">{grid}</section>')


def page_category(cfg: dict, key: str, posts: list[dict]) -> str:
    cat = cfg["categories"][key]
    items = [p for p in posts if p["category"] == key]
    grid = "".join(card(p, cfg, "../") for p in items) or "<p class='empty'>このカテゴリの記事は準備中です。</p>"
    body = f'<h1 class="sec page">{esc(cat["en"])}<small>{esc(cat["name"])}</small></h1><section class="grid">{grid}</section>'
    return layout(cfg, "../", cat["name"], body, active=key)


def page_post(cfg: dict, post: dict, posts: list[dict]) -> str:
    cat = cfg["categories"][post["category"]]
    sources = ""
    if post["sources"]:
        lis = "".join(
            f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["title"])}</a>'
            f'{"（" + esc(s["site"]) + "）" if s.get("site") else ""}</li>'
            for s in post["sources"]
        )
        sources = f'<aside class="sources"><h2>参考にした情報</h2><ul>{lis}</ul></aside>'
    note = ""
    if post["category"] in ("wellness", "beauty"):
        note = ('<p class="note">※この記事は一般的な情報をまとめたもので、効果を保証するものではありません。'
                '体調や肌に不安がある場合は、医師や専門家にご相談ください。</p>')
    related = [p for p in posts if p["category"] == post["category"] and p["slug"] != post["slug"]][:3]
    if len(related) < 3:
        related += [p for p in posts if p["slug"] != post["slug"] and p not in related][: 3 - len(related)]
    rel = "".join(card(p, cfg, "../") for p in related)
    body = f"""
<article class="post">
  {eyecatch(post, cfg, "../", "big")}
  <header class="post-head">
    <a class="cat" href="../category/{post['category']}.html">{esc(cat['name'])}</a>
    <h1>{esc(post['title'])}</h1>
    <p class="lead">{esc(post['description'])}</p>
    <time>{jdate(post['date'])}</time>
  </header>
  <div class="post-body">{post['body_html']}</div>
  {note}
  {sources}
</article>
<h2 class="sec">MORE<small>こちらもおすすめ</small></h2>
<section class="grid">{rel}</section>"""
    return layout(cfg, "../", post["title"], body, post["description"], active=post["category"])


def page_about(cfg: dict) -> str:
    body = f"""
<article class="post about">
  <header class="post-head"><h1>このサイトについて</h1></header>
  <div class="post-body">
  <p>{esc(cfg['site']['title'])}は、ミセスクイーンコンテストを運営するミセスクイーンが届けるWebマガジンです。
  美容・ファッション・健康・ライフスタイル・自己実現など、毎日を自分らしく輝かせたいミセスのためのヒントをお届けします。</p>
  <h2>記事づくりについて</h2>
  <p>記事は、公開されているニュースや情報をもとに、AIの力を借りて編集部の視点でまとめ直したオリジナル記事です。
  参考にした情報は、各記事の最後にリンクで紹介しています。内容の誤りなどにお気づきの際はお知らせください。</p>
  </div>
</article>"""
    return layout(cfg, "", "このサイトについて", body)


def feed(cfg: dict, posts: list[dict]) -> str:
    site = cfg["site"]
    items = "".join(
        f"<item><title>{esc(p['title'])}</title><link>{site['url']}/posts/{p['slug']}.html</link>"
        f"<description>{esc(p['description'])}</description>"
        f"<pubDate>{dt.datetime.combine(p['date'], dt.time(7)).strftime('%a, %d %b %Y %H:%M:%S +0900')}</pubDate></item>"
        for p in posts[:20]
    )
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{esc(site["title"])}</title>'
            f'<link>{site["url"]}</link><description>{esc(site["description"])}</description>{items}</channel></rss>')


def sitemap(cfg: dict, posts: list[dict]) -> str:
    base = cfg["site"]["url"]
    urls = [f"{base}/"] + [f"{base}/category/{k}.html" for k in cfg["categories"]] + [f"{base}/posts/{p['slug']}.html" for p in posts]
    body = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'


def build_private() -> None:
    """非公開モード：準備中の画面だけを出す"""
    OUT.mkdir(parents=True)
    (OUT / "index.html").write_text(
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex, nofollow"><title>準備中</title></head>'
        '<body style="margin:0;display:grid;place-items:center;min-height:100vh;font-family:sans-serif;'
        'background:#fffafc;color:#7a6a71"><p>ただいま準備中です。</p></body></html>', encoding="utf-8")
    (OUT / "404.html").write_text((OUT / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print("private mode: placeholder only")


def main() -> None:
    cfg = load_config()
    posts = load_posts()
    if OUT.exists():
        shutil.rmtree(OUT)
    if not cfg["site"].get("public", True):
        build_private()
        return
    (OUT / "posts").mkdir(parents=True)
    (OUT / "category").mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")
    (OUT / "index.html").write_text(page_index(cfg, posts), encoding="utf-8")
    (OUT / "about.html").write_text(page_about(cfg), encoding="utf-8")
    for key in cfg["categories"]:
        (OUT / "category" / f"{key}.html").write_text(page_category(cfg, key, posts), encoding="utf-8")
    for p in posts:
        (OUT / "posts" / f"{p['slug']}.html").write_text(page_post(cfg, p, posts), encoding="utf-8")
    (OUT / "feed.xml").write_text(feed(cfg, posts), encoding="utf-8")
    (OUT / "sitemap.xml").write_text(sitemap(cfg, posts), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"built {len(posts)} posts -> {OUT}")


if __name__ == "__main__":
    main()
