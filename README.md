# QUEEEN MAGAZINE

ミセスクイーンが届ける、自動更新のWebマガジンです。

## しくみ
1. 決まった時間（初期設定：月・水・金の朝7時）に、GitHubが自動で動きます
2. 美容・ファッションなど6つのテーマで、最近のニュースの見出しを集めます
3. AI（Claude）が話題を1つ選び、Web検索で事実を調べ、オリジナル記事を書きます
4. AIが別の目で記事をチェックします
5. 「確認モード」なら確認待ちとして届き、OKを押すと公開。「自動モード」ならそのまま公開します

## よく使う操作
| やりたいこと | 方法 |
|---|---|
| 今すぐ1本書かせる | Actions →「自動で記事を書く」→「Run workflow」 |
| 確認待ちの記事を公開する | Pull requests → 記事を開く →「Merge pull request」 |
| 記事を公開しない | Pull requests → 記事を開く →「Close pull request」 |
| 確認なしの自動公開に切り替える | `config.yaml` の `mode: review` を `mode: auto` に |
| テーマやキーワードを変える | `config.yaml` の `categories` |
| 投稿の曜日・時間を変える | `.github/workflows/auto-post.yml` の `cron` |
| 書き方のルールを変える | `scripts/editorial_guide.md` |

## ファイルの場所
- `content/posts/` … 記事（1記事＝1ファイル）
- `static/` … ロゴとデザイン
- `scripts/` … 自動化のプログラム
