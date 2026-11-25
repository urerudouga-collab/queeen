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

def photo_url(post: dict, prefix: str) -> str:
    img = post.get("image") or ""
    if img and not img.startswith("http"):
        img = prefix + img  # リポジトリ内の写真（例: static/photos/xxx.jpg）
    return img


def visual(post: dict, cfg: dict, prefix: str, cls: str = "") -> str:
    """記事の画像。写真があれば写真、なければブランドカラーのデザイン画像"""
    cat = cfg["categories"][post["category"]]
    img = photo_url(post, prefix)
    if img:
        return (f'<div class="vis {cls}"><img src="{esc(img)}" alt="" loading="lazy"></div>')
    return (
        f'<div class="vis vis-fallback fb-{post["category"]} {cls}">'
        f'<span class="fb-en">{esc(cat["en"])}</span>'
        f'<span class="fb-word">{esc(post.get("keyword", ""))}</span></div>'
    )


def meta(post: dict, cfg: dict) -> str:
    cat = cfg["categories"][post["category"]]
    return (f'<p class="meta"><span class="cat">{esc(cat["en"])}</span>'
            f'<time>{post["date"].strftime("%Y.%m.%d")}</time></p>')


def card(post: dict, cfg: dict, prefix: str, cls: str = "") -> str:
    return f"""
<a class="card {cls}" href="{prefix}posts/{post['slug']}.html">
  {visual(post, cfg, prefix)}
  {meta(post, cfg)}
  <h3>{esc(post['title'])}</h3>
</a>"""


def layout(cfg: dict, prefix: str, title: str, body: str, description: str = "", active: str = "", og_image: str = "") -> str:
    site = cfg["site"]
    on = ' class="on"'
    nav = "".join(
        f'<a href="{prefix}category/{key}.html"{on if key == active else ""}>{esc(c["name"])}</a>'
        for key, c in cfg["categories"].items()
    )
    full_title = f"{title} | {site['title']}" if title != site["title"] else site["title"]
    contest = (
        f'<a href="{esc(site["contest_url"])}">ミセスクイーンコンテスト</a>'
        if site.get("contest_url") else ""
    )
    foot_cats = "".join(f'<a href="{prefix}category/{k}.html">{esc(c["en"])}</a>' for k, c in cfg["categories"].items())
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
{'' if site.get('public', True) is True else '<meta name="robots" content="noindex, nofollow">'}
<meta name="description" content="{esc(description or site['description'])}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description or site['description'])}">
{f'<meta property="og:image" content="{esc(og_image)}">' if og_image else ''}
<meta name="theme-color" content="#fbf7f4">
<link rel="icon" href="{prefix}static/logo.png">
<link rel="alternate" type="application/rss+xml" href="{prefix}feed.xml" title="{esc(site['title'])}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Shippori+Mincho:wght@500;600;700&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}static/style.css">
</head>
<body>
<div class="ticker"><div class="ticker-in"><span>{esc(site['subtitle'])}</span><span>NEW STORIES EVERY MON · WED · FRI</span><span>{esc(site['subtitle'])}</span><span>NEW STORIES EVERY MON · WED · FRI</span><span>{esc(site['subtitle'])}</span><span>NEW STORIES EVERY MON · WED · FRI</span></div></div>
<header class="site-header">
  <div class="bar">
    <a class="brand" href="{prefix}index.html" aria-label="{esc(site['title'])}">
      <img src="{prefix}static/logo.png" alt="">
      <span class="wordmark">QUEEEN<i>magazine</i></span>
    </a>
    <a class="about-link" href="{prefix}about.html">ABOUT</a>
  </div>
  <nav class="nav">{nav}</nav>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <div class="f-inner">
    <p class="f-mark">QUEEEN<i>magazine</i></p>
    <p class="f-desc">{esc(site['description'])}</p>
    <nav class="f-cats">{foot_cats}</nav>
    <p class="f-links"><a href="{prefix}about.html">このサイトについて</a>{contest}</p>
    <p class="copy">© {dt.date.today().year} Mrs. QUEEEN</p>
  </div>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------- ページ

def page_index(cfg: dict, posts: list[dict]) -> str:
    if not posts:
        return layout(cfg, "", cfg["site"]["title"], "<p class='empty'>記事は準備中です。</p>")
    top = posts[0]
    pickup, rest = posts[1:3], posts[3:]
    hero = f"""
<section class="hero">
  <a href="posts/{top['slug']}.html">
    {visual(top, cfg, "", "hero-vis")}
    <div class="hero-text">
      <span class="badge">NEW</span>
      {meta(top, cfg)}
      <h1>{esc(top['title'])}</h1>
      <p>{esc(top['description'])}</p>
      <span class="more">READ STORY <b>→</b></span>
    </div>
  </a>
</section>"""
    picks = "".join(card(p, cfg, "", "wide") for p in pickup)
    cats = "".join(
        f'<a class="cat-tile" href="category/{k}.html"><span class="ct-en">{esc(c["en"])}</span>'
        f'<span class="ct-ja">{esc(c["name"])}</span>'
        f'<span class="ct-n">{sum(1 for p in posts if p["category"] == k):02d}</span></a>'
        for k, c in cfg["categories"].items()
    )
    grid = "".join(card(p, cfg, "") for p in rest[:24])
    body = (hero
            + f'<section class="sec"><h2 class="sec-title"><span>Pick Up</span><small>注目の記事</small></h2><div class="picks">{picks}</div></section>'
            + f'<section class="sec"><h2 class="sec-title"><span>Categories</span><small>カテゴリから探す</small></h2><div class="cats">{cats}</div></section>'
            + (f'<section class="sec"><h2 class="sec-title"><span>Latest</span><small>新着記事</small></h2><div class="grid">{grid}</div></section>' if rest else ""))
    return layout(cfg, "", cfg["site"]["title"], body, og_image=photo_url(top, ""))


def page_category(cfg: dict, key: str, posts: list[dict]) -> str:
    cat = cfg["categories"][key]
    items = [p for p in posts if p["category"] == key]
    grid = "".join(card(p, cfg, "../") for p in items) or "<p class='empty'>このカテゴリの記事は準備中です。</p>"
    body = (f'<header class="page-head"><p class="ph-en">{esc(cat["en"])}</p><h1>{esc(cat["name"])}</h1>'
            f'<p class="ph-n">{len(items)} STORIES</p></header><div class="grid">{grid}</div>')
    return layout(cfg, "../", cat["name"], body, active=key)


def page_post(cfg: dict, post: dict, posts: list[dict]) -> str:
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
    credit = f'<p class="credit">Photo: {esc(post["image_credit"])}</p>' if post.get("image_credit") else ""
    related = [p for p in posts if p["category"] == post["category"] and p["slug"] != post["slug"]][:3]
    if len(related) < 3:
        related += [p for p in posts if p["slug"] != post["slug"] and p not in related][: 3 - len(related)]
    rel = "".join(card(p, cfg, "../") for p in related)
    cat = cfg["categories"][post["category"]]
    body = f"""
<article class="post">
  <header class="post-head">
    <p class="meta"><a class="cat" href="../category/{post['category']}.html">{esc(cat['en'])}</a><time>{post['date'].strftime('%Y.%m.%d')}</time></p>
    <h1>{esc(post['title'])}</h1>
    <p class="lead">{esc(post['description'])}</p>
  </header>
  {visual(post, cfg, "../", "post-vis")}
  {credit}
  <div class="post-body">{post['body_html']}</div>
  {note}
  {sources}
  <p class="back"><a href="../index.html">← TOP</a><a href="../category/{post['category']}.html">{esc(cat['name'])}の記事一覧 →</a></p>
</article>
<section class="sec"><h2 class="sec-title"><span>More Stories</span><small>こちらもおすすめ</small></h2><div class="grid">{rel}</div></section>"""
    return layout(cfg, "../", post["title"], body, post["description"], active=post["category"], og_image=photo_url(post, ""))


def page_about(cfg: dict) -> str:
    body = f"""
<article class="post about">
  <header class="post-head"><p class="meta"><span class="cat">ABOUT</span></p><h1>このサイトについて</h1></header>
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
    global OUT
    cfg = load_config()
    posts = load_posts()
    root = OUT
    if root.exists():
        shutil.rmtree(root)
    mode = cfg["site"].get("public", True)
    if mode is not True:
        build_private()
        if mode != "limited":
            return
        OUT = root / cfg["site"]["preview_key"]   # 限定公開：秘密のURLの下にサイト全体を置く
        cfg["site"]["url"] = cfg["site"]["url"].rstrip("/") + "/" + cfg["site"]["preview_key"]
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
    (root / ".nojekyll").write_text("")
    print(f"built {len(posts)} posts -> {OUT}")


if __name__ == "__main__":
    main()
