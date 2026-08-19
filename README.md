# 公募案件（補助金・企画競争）探索ワークフロー

一般社団法人ジャパンプロモーションが申請・提案可能な公募案件を週次で探し出し、
Gmail とGoogle Drive に届けるための仕組み。

## 構成

| ファイル | 役割 |
|---|---|
| `docs/handoff.md` | 引き継ぎ書。決定済み要件、制約、経緯 |
| `profile/company-profile.yaml` | 会社プロファイル。適合判定の土台 |
| `workflow/runbook.md` | **週次実行手順。定期実行はこれを読んで動く** |
| `workflow/sources.yaml` | 巡回対象の情報源と、必要なネットワーク許可ドメイン |
| `workflow/keywords.yaml` | 検索キーワード辞書 |
| `workflow/eligibility.md` | 適合判定ロジック（足切り・応募形態・スコアリング） |
| `workflow/report-template.md` | レポートの形式 |
| `data/ledger.csv` | 報告済み案件の台帳。重複防止に使う |

## 動かし方

```
リポジトリ yixima/hojo の workflow/runbook.md を読んで、週次巡回を実行してください
```

## 設定が必要なもの

クラウド環境のネットワークアクセスを `Custom` にし、
`workflow/sources.yaml` の `network_allowlist` の7行を許可ドメインに登録すること。
未設定だと公的機関のサイトが全て遮断され、公募要領を読めない。
