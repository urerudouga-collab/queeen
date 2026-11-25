"""集めた話題から、AI（Claude）が記事を1本書くスクリプト。

流れ:
  1. カテゴリを順番に選ぶ（最近書いていないカテゴリを優先）
  2. 集めた見出しの中から、読者に響く話題をAIが1つ選ぶ
  3. AIがWeb検索で事実を調べ、メモを作る
  4. メモをもとに、編集方針どおりのオリジナル記事を書く
  5. 別の目でチェック（NG表現・言い過ぎ・誤情報のおそれ）
  6. content/posts/ に保存

使い方:  ANTHROPIC_API_KEY=... python scripts/write_article.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
JST = timezone(timedelta(hours=9))
BETAS = ["server-side-fallback-2026-07-01"]

client = anthropic.Anthropic()


class TopicChoice(BaseModel):
    candidate_index: int = Field(description="選んだ見出しの番号")
    angle: str = Field(description="ミセス世代向けに、どんな切り口で書くか（1〜2文）")
    search_queries: list[str] = Field(description="事実を調べるための日本語の検索語（2〜3個）")


class Source(BaseModel):
    title: str
    site: str
    url: str


class Article(BaseModel):
    title: str = Field(description="記事タイトル（全角20〜40字）")
    description: str = Field(description="記事の要約（全角60〜110字）")
    keyword: str = Field(description="アイキャッチに大きく表示する短い言葉（全角6〜12字）")
    slug: str = Field(description="URL用の英小文字とハイフンの短い名前（例: winter-skin-care）")
    body_markdown: str = Field(description="本文（Markdown。最初の見出しは ## から）")
    sources: list[Source] = Field(description="実際に参考にした情報源。調査メモにあるURLだけを使う")


class Review(BaseModel):
    ok: bool = Field(description="そのまま公開してよければ true")
    issues: list[str] = Field(description="問題点（なければ空）")


def ask(model_cls, system: str, user: str, cfg: dict):
    resp = client.beta.messages.parse(
        model=cfg["ai"]["model"],
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": cfg["ai"]["effort"]},
        output_format=model_cls,
        betas=BETAS,
        fallbacks="default",
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise RuntimeError(f"AIが回答しませんでした（stop_reason={resp.stop_reason}）")
    return resp.parsed_output


def research(queries: list[str], headline: dict, angle: str, cfg: dict) -> tuple[str, set[str]]:
    """Web検索で事実を集めてメモにする。検索結果に出てきたURLの一覧も返す。"""
    messages = [{
        "role": "user",
        "content": (
            f"次の話題について、記事を書くための事実を調べてください。\n"
            f"話題の見出し: {headline['title']}（{headline['site']}）\n切り口: {angle}\n"
            f"検索語の例: {', '.join(queries)}\n\n"
            "信頼できる情報源（公的機関、大手メディア、専門家の監修があるサイトなど）を優先し、"
            "記事に使える事実を箇条書きでまとめてください。各事実の後ろに、根拠となったページのタイトルとURLを書いてください。"
            "推測や、確認できなかったことは書かないでください。"
        ),
    }]
    urls: set[str] = set()
    for _ in range(4):  # pause_turn の続きに対応
        resp = client.beta.messages.create(
            model=cfg["ai"]["model"],
            max_tokens=16000,
            messages=messages,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 6,
                    "user_location": {"type": "approximate", "country": "JP"}}],
            output_config={"effort": cfg["ai"]["effort"]},
            betas=BETAS,
            fallbacks="default",
        )
        for block in resp.content:
            if block.type == "web_search_tool_result" and isinstance(block.content, list):
                urls.update(r.url for r in block.content)
        if resp.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": resp.content})
    if resp.stop_reason == "refusal":
        raise RuntimeError("調査中にAIが回答しませんでした")
    notes = "\n".join(b.text for b in resp.content if b.type == "text")
    return notes, urls


def recent_posts(n: int = 30) -> list[dict]:
    items = []
    for p in sorted(POSTS.glob("*.md"), reverse=True)[:n]:
        meta = yaml.safe_load(p.read_text(encoding="utf-8").split("---", 2)[1])
        items.append({"title": meta["title"], "category": meta["category"]})
    return items


def category_order(cfg: dict, recent: list[dict]) -> list[str]:
    """最近書いていないカテゴリから順に並べる"""
    last_seen = {key: 10_000 for key in cfg["categories"]}
    for i, p in enumerate(recent):
        last_seen[p["category"]] = min(last_seen.get(p["category"], 10_000), i)
    return sorted(cfg["categories"], key=lambda k: -last_seen[k])


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    guide = (ROOT / "scripts" / "editorial_guide.md").read_text(encoding="utf-8")
    cands = json.loads((ROOT / "data" / "candidates.json").read_text(encoding="utf-8"))["categories"]
    recent = recent_posts()
    recent_titles = "\n".join(f"- {p['title']}" for p in recent) or "（まだありません）"
    today = datetime.now(JST).date()

    category = next((k for k in category_order(cfg, recent) if cands.get(k)), None)
    if category is None:
        sys.exit("話題が1件も集まりませんでした")
    items = cands[category][:40]
    cat_name = cfg["categories"][category]["name"]

    # 2. 話題を選ぶ
    listing = "\n".join(f"{i}. {it['title']}（{it['site']}）" for i, it in enumerate(items))
    choice = ask(TopicChoice, guide, (
        f"今日は {today.isoformat()}、カテゴリは「{cat_name}」です。\n次の見出しから、読者がいちばん読みたくなりそうな話題を1つ選んでください。"
        f"季節に合うもの、暮らしに役立つものを優先し、ブランドにそぐわない話題や、最近の記事と似た話題は避けてください。\n\n"
        f"## 見出し\n{listing}\n\n## 最近の記事\n{recent_titles}"
    ), cfg)
    headline = items[max(0, min(choice.candidate_index, len(items) - 1))]
    print("話題:", headline["title"], "/", choice.angle)

    # 3. 調べる
    notes, found_urls = research(choice.search_queries, headline, choice.angle, cfg)

    # 4. 書く
    article = ask(Article, guide, (
        f"今日は {today.isoformat()}。カテゴリ「{cat_name}」の記事を書いてください。\n切り口: {choice.angle}\n\n"
        f"## 調査メモ（これに書かれた事実と一般的な知識だけを使うこと）\n{notes}\n\n## 最近の記事（重複を避ける）\n{recent_titles}"
    ), cfg)

    # 出典は、検索で実際に出てきたURLだけを残す（AIがURLを作ってしまうのを防ぐ）
    sources = [s.model_dump() for s in article.sources if s.url in found_urls or s.url in notes][:5]

    # 5. チェック
    review = ask(Review, guide, (
        "次の記事が、編集方針を守っているか厳しくチェックしてください。"
        "特に、調査メモにない数字や事実の創作、効果の断定、他メディアの文章の流用、不適切な話題がないかを確認してください。\n\n"
        f"## 調査メモ\n{notes}\n\n## 記事\n# {article.title}\n{article.body_markdown}"
    ), cfg)

    # 6. 保存
    slug = re.sub(r"[^a-z0-9-]", "", article.slug.lower()).strip("-")[:50] or "article"
    path = POSTS / f"{today.isoformat()}-{slug}.md"
    front = {
        "title": article.title,
        "description": article.description,
        "date": today.isoformat(),
        "category": category,
        "keyword": article.keyword,
        "sources": sources,
    }
    path.write_text("---\n" + yaml.safe_dump(front, allow_unicode=True, sort_keys=False) + "---\n\n"
                    + article.body_markdown.strip() + "\n", encoding="utf-8")
    print("保存:", path.name, "/ チェック:", "OK" if review.ok else review.issues)

    needs_review = cfg.get("mode", "review") != "auto" or not review.ok
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"needs_review={'true' if needs_review else 'false'}\n")
            f.write(f"title={article.title}\n")
            f.write(f"file={path.relative_to(ROOT)}\n")
    review_note = ROOT / "data" / "review.md"
    review_note.write_text(
        f"## {article.title}\n\n{article.description}\n\n**AIチェック:** "
        + ("問題なし" if review.ok else "要確認\n" + "\n".join(f"- {i}" for i in review.issues))
        + f"\n\n**話題のきっかけ:** [{headline['title']}]({headline['url']})（{headline['site']}）\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
