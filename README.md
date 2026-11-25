# QUEEEN MAGAZINE

ミセスクイーンが届ける、自動更新のWebマガジンです。

## しくみ
1. 決まった時間（初期設定：月・水・金の朝7時ごろ）に、Claudeのスケジュールタスクが起動します（Claudeのプラン内で動くので追加料金なし）
2. Claudeが `AUTOPOST.md` の手順どおりに、話題を探し、事実を調べ、オリジナル記事を書いてチェックします
3. 「確認モード」なら確認待ち（Pull request）として届き、Merge を押すと公開。「自動モード」ならそのまま公開します

※ `scripts/collect.py` と `scripts/write_article.py` は、将来Claude APIの鍵（有料）で動かしたくなった場合の予備です。

## よく使う操作
| やりたいこと | 方法 |
|---|---|
| 今すぐ1本書かせる | Claudeに「記事を1本書いて」と頼む |
| 確認待ちの記事を公開する | Pull requests → 記事を開く →「Merge pull request」 |
| 記事を公開しない | Pull requests → 記事を開く →「Close pull request」 |
| 確認なしの自動公開に切り替える | `config.yaml` の `mode: review` を `mode: auto` に |
| テーマやキーワードを変える | `config.yaml` の `categories` |
| 投稿の曜日・時間を変える | Claudeに頼む（スケジュールタスクの設定） |
| 書き方のルールを変える | `scripts/editorial_guide.md` |
| 記事づくりの手順を変える | `AUTOPOST.md` |

## ファイルの場所
- `content/posts/` … 記事（1記事＝1ファイル）
- `static/` … ロゴとデザイン
- `scripts/` … 自動化のプログラム
