# 引き継ぎファイル（kobo_anken_jizokuka_handover_latest）

- **案件名（枝名）**：`kobo_anken_jizokuka` ＝ 小規模事業者持続化補助金＜共同・協業型＞第3回の申請作業
  （生島様が 2026-09-04 に承認。候補1をそのまま採用、語の追加なし）
- **分岐元**：`kobo_anken_handover_latest.md`（Drive `claude_handover/kobo_anken/`・v3・2026-09-03 15:42 JST）。
  分岐前の経緯（案件探索の全体・おまつり歳時記・東京都の資格）は分岐元にしかない
- **姉妹枝**：`kobo_anken_omatsuri`（おまつり歳時記の応募作業。別セッション。本ファイルでは扱わない）
- **保存先（固定）**
  - Google Drive `claude_handover/kobo_anken/kobo_anken_jizokuka_handover_latest.md`（固定名）
    ＋ 履歴 `kobo_anken_jizokuka_handover_20260904_v1.md`
  - GitHub `yixima/hojo`／ブランチ **`claude/kobo-anken-sustainability-subsidies-b9o870`**／
    パス `docs/handover/kobo_anken_jizokuka_handover_latest.md`（履歴も同じフォルダ）
- **初版作成**：2026-09-04（金）17:40 JST（`./bin/today.sh` 実測）／版 **v1**
- **準拠**：汎用マニュアル v41 コアカード §5.5〜§5.6（引き継ぎ＝原本の運搬・10章必須）。
  リポジトリ内の `docs/manual/` は v17 のまま。**配布元の最新版（v41）を curl で取り直して適用した**
- **環境**：`[Code]`（claude.ai/code のクラウドセッション）／作業ディレクトリ `/home/user/hojo`

> **更新のしかた**：Drive の `update_file` は本文を差し替えられない。更新のたびに
> **同じ名前で新規作成し、旧版をゴミ箱へ移し、削除した版の名前・ID・サイズ・日時を §6 に1行追記する。**
> Drive のファイルIDは毎回変わる。IDを覚えず、フォルダの中をタイトルで探すこと。

---

## 0. 受領確認ブロック

このリポジトリには `tools/make_handover.py` が無い（分岐元 §7-3 のとおり未整備）。
そのため件数は**手で数えた**。次のセッションは下の件数と本文を突き合わせ、合わなければ申告する。

```handover-manifest
{
  "manifest_version": 1,
  "generated_at": "2026-09-04 17:40 JST",
  "source": "manual",
  "cwd": "/home/user/hojo",
  "branch": "claude/kobo-anken-sustainability-subsidies-b9o870",
  "case": "kobo_anken",
  "lane": "jizokuka",
  "parent": "kobo_anken_handover_latest.md",
  "counts": {
    "依頼の原文": 2,
    "こちらの応答": 1,
    "確定した決定": 2,
    "却下した案": 2,
    "作成・追加したファイル": 11,
    "このセッションのコミット": 1,
    "記録された失敗": 0,
    "未完了": 5,
    "生島様への未回答質問": 4
  },
  "chapters": [
    "1. 依頼の原文", "2. 確定した事実と決定", "3. 却下した案", "4. 発行したすべてのファイル",
    "5. セッション中の調整・変更の経緯", "6. 失敗と、そこから得た改善", "7. 未完了のタスク",
    "8. 次に最初に行うこと", "9. 前提条件・数値前提", "10. 使用したコマンド・手順"
  ]
}
```

---

## 1. 依頼の原文（要約せずそのまま）

### 1-1. このセッションの1通目（生島様・2026-09-04）

> kobo anken
> の続きです。ここでは持続か補助金についてのセッションを行います。

（「持続か補助金」は「持続化補助金」の入力誤りと解して進めた。分岐元 §7-2 A の保留案件と一致する）

### 1-2. 枝名の承認（生島様・2026-09-04）

> kobo_anken_jizokuka
>
> でOKです。

### 1-3. 分岐元にある、この案件についての生島様の原文（分岐元 §3-2 より転記）

> これは検討中。なんらかの企画を考えて申請したい。
（2026-08-31）

### 1-4. こちらの応答（1通目・要旨ではなく骨子。全文は会話記録にある）

受領照合の結果（Drive版とリポジトリ版が 63,057 バイト／941 行／SHA-256 `04297c8d…` で一致）、
リポジトリの分岐（親枝 `claude/public-bid-search-workflow-uzj3te` の bb6598f から）、
一次資料の再取得結果（§2-2）、枝名候補3つ、質問1つ（枝名）。

---

## 2. 確定した事実と決定（理由つき）

### 2-1. 決定①：枝名 `kobo_anken_jizokuka`

- 生島様承認 2026-09-04。
- **理由**：分岐元は「おまつり歳時記」を主対象にしており、持続化補助金は §7-2 A で「保留・対象外」だった。
  別セッション＝別枝にしないと、後から保存したほうが先の枝の引き継ぎを消す（v41 §5.6）。

### 2-2. 決定②：作業ブランチは `claude/kobo-anken-sustainability-subsidies-b9o870`。親枝から分岐

- 指定されたブランチは初期コミットしか無い空の枝だった。分岐元 §2-17 の指示
  「新チャットに別のブランチ名が指定された場合は、このブランチから分岐する」に従い、
  `origin/claude/public-bid-search-workflow-uzj3te`（bb6598f）から `-B` で作り直してプッシュした。
- **理由**：台帳 `data/ledger.csv`・判定基準・企画案 `workflow/jizokuka_kyodo_r8_3.md` が親枝にある。
  空の枝で始めると、それらを持たないまま作業することになる。
- **注意**：親枝は姉妹枝（おまつり歳時記）も更新し続けている。台帳を書き換えるときは
  親枝の最新を取り込んでから行う（§10-4）。

### 2-3. 一次資料で確認した事実（2026-09-04 16:28〜16:29 JST 取得）

| 事実 | ラベル | 出典 |
|---|---|---|
| 公募要領は **第6版（令和8年8月4日）・47頁**。分岐元が読んだ版と同一（SHA-256 `f5bf004f…`） | 【確認済】 | https://r6.kyodokyogyohojokin.info/doc/r6_koubover6_kk3.pdf |
| 申請受付締切 **令和8年9月30日（水）17:00**。Jグランツ電子申請のみ。GビズIDプライム必須・暫定アカウント不可 | 【確認済】 | 同PDF 表紙 |
| 事務局サイトの新着は 2026-08-28（詐称注意）が最新。第3回の様式・FAQ・Jグランツ手引き・交付規程（8/14改定）が公開済み | 【確認済】 | https://r6.kyodokyogyohojokin.info/ |
| GビズIDのオンライン申請不具合（2026-08-28付）は **本日も未解消**。「9月上旬に解消予定」のまま | 【確認済】 | https://gbiz-id.go.jp/top/ |
| **書類申請の審査期間は「最大2週間」から「最大1か月」に変更**（2026-07-09付告知）。不備があっても書類は返送されず、マイページとメールで通知のみ | 【確認済】 | 同上 |
| GビズIDプライムの有効期限は発行日から **2年3か月**（2026-07-09 導入） | 【確認済】 | 同上 |
| 2026-09-12（土）9:00〜14:30頃 GビズID全機能停止 | 【確認済】 | 同上 |
| 台帳の残日数：**26日**（2026-09-04 16:29 JST 時点、`bin/days_left.py`） | 【確認済】 | 実行結果 |

### 2-4. 分岐元から引き継ぐ確定事項（`workflow/jizokuka_kyodo_r8_3.md` に全文）

- 当社は「地域振興等機関」定義⑤に該当し申請できる（第三者委員会が実績で判断）
- 補助上限：参画事業者10者以上→3,000万円／5〜9者→2,000万円。定額区分のみの申請は不可
- 実施期間：交付決定日〜令和9年12月10日。採択発表 令和8年11月頃、交付決定は令和9年1〜2月見込み
- ⑥展示会等出展費は「出展の本申込みが交付決定日前」だと補助対象外 → 展示会の選定を縛る
- 「過去実施した事業と同様の事業」は対象外だが、審査の視点「過去の類似事業と比べて発展性はあるか」で外せる（論証は同ファイル §4）
- 取組は（1）展示会・商談会＋（2）催事販売の2本立て。（3）販売拠点構築は見送り
- 様式4（地方公共団体の事業支援計画書）は任意だが実質加点

---

## 3. 却下した案と理由

| 却下した案 | 理由 |
|---|---|
| 枝名 `kobo_anken_jizokuka_r8_3`（公募回入り） | 現時点で次回公募を扱う予定がなく、長いだけ。生島様が候補1を選んだ |
| 枝名 `kobo_anken_hojokin`（補助金全般） | 案件が一つに定まらず、姉妹枝との境界が曖昧になる。同上 |

---

## 4. 発行したすべてのファイル（説明つき）

### 4-1. この引き継ぎ

| ファイル | 置き場所 | 何のために |
|---|---|---|
| `kobo_anken_jizokuka_handover_latest.md` | Drive `claude_handover/kobo_anken/`＋`docs/handover/` | 本ファイル（固定名）。次のセッションはこれを読む |
| `kobo_anken_jizokuka_handover_20260904_v1.md` | 同上 | 本ファイルの履歴版（固定名は上書きされるため） |

### 4-2. 一次資料（`docs/jizokuka/`・2026-09-04 に事務局サイトから取得。ファイル名は配布元のまま）

| ファイル | 中身 | 頁 |
|---|---|---|
| `r6_koubover6_kk3.pdf` | **公募要領 第6版（令和8年8月4日）。最重要。**申請要件・対象経費・審査の視点・対象外条項はすべてここ | 47 |
| `r6_qa_kk3.pdf` | 申請時によくあるご質問（第3回用）。Q1 が「地域振興等機関の定義⑤」＝当社の該当条件 | 5 |
| `r6_jtebiki_kk3.pdf` | Jグランツ操作マニュアル（第3回公募申請・2026-08-14） | 23 |
| `r6_kitei_260814.kk.pdf` | 交付規程（令和8年8月14日改定）。採択後の義務・5年間の報告義務の根拠 | 40 |
| `r6_y12_kk3.xlsx` | 様式1-1・1-2 申請書（Jグランツ入力の下書き用） | — |
| `r6_y21_kk3.docx` | **様式2-1 補助事業計画書（Word）。要作成** | — |
| `r6_y22_kk3.xlsx` | **様式2-2 参画事業者一覧＋（別添）申請者との関係。10者（または5者）の確定が前提** | — |
| `r6_y330_kk3.xlsx` | **様式3 支出計画書＋積算明細書（30行版）** | — |
| `r6_y4_kk3.docx` | 様式4 事業支援計画書（地方公共団体が記入。任意・実質加点） | — |

**頁数は pypdf で数えた。様式の中身（セル構成）はまだ開いていない**（§7 の 4）。

### 4-3. 親枝から引き継いだ中核ファイル（説明は分岐元 §4-3 と同じ）

`CLAUDE.md`／`bin/today.sh`／`bin/days_left.py`／`data/ledger.csv`（2行目が本案件）／
`workflow/jizokuka_kyodo_r8_3.md`（企画案281行）／`profile/company-profile.yaml`／`workflow/eligibility.md`

---

## 5. セッション中の調整・変更の経緯（変える前はどうだったか）

| いつ | 何を変えたか | 変える前 |
|---|---|---|
| 2026-09-04 | 作業ブランチを親枝の先端から作り直した | 指定枝は初期コミット（README のみ）だけだった |
| 2026-09-04 | GビズID書類申請の所要を「**最大1か月**」に改めた | 分岐元・企画案は「数週間」と書いていた（公募要領の文言）。GビズID側の2026-07-09告知が優先 |
| 2026-09-04 | 適用するマニュアルを配布元の **v41** にした | リポジトリ内は v17。CLAUDE.md は v17 を読めと書いているが、ユーザー設定の「常時適用（ブートローダー）」が配布元URLを最上位と定めている。**CLAUDE.md の記述は未修正**（§7 の 5） |

---

## 6. 失敗と、そこから得た改善

- このセッションでの失敗は **まだ無い**（2026-09-04 17:40 時点）。
- **破壊的操作の監査記録**（Drive でゴミ箱へ移した版）：まだ無し。初版のため。
  以後、更新のたびにここへ「日付／ファイル名／Drive ID／サイズ／作成日時」を1行ずつ追記する。
- 分岐元 §6 の教訓（仕様書を読む前に「応募可」と言わない／台帳の書き換えは行数 assert／
  Artifact 再公開前に read）は、この枝でもそのまま有効。

---

## 7. 未完了のタスク

| # | タスク | 状態 | 期限 |
|---|---|---|---|
| 1 | **生島様への確認4点**（下記）。最優先は GビズIDプライム | **未回答**（枝名の直後に1点ずつ伺う） | 即時 |
| 2 | 展示会主催者（JAPAN EXPO PARIS 2027）への「本申込みの最遅期限」確認 | 未着手。生島様の回答④に依存 | 9/12 目安 |
| 3 | 様式4 を依頼する自治体への打診 | 未着手。回答③に依存 | 9/5 目安（分岐元の工程） |
| 4 | 様式2-1・2-2・3 の中身（セル構成・記入欄）の読み込み | **未着手** | 9/8 まで |
| 5 | `CLAUDE.md` の「v17 を読む」記述を、配布元 v41 常時適用に合わせて直す | 未着手（提案止まり。マニュアル本体の改訂ではなく、リポジトリ側の参照先の更新） | — |

**生島様への未回答4点（分岐元 §7-2 A から転記。順に1点ずつ伺う）**
1. **GビズIDプライムを保有しているか。有効期限はいつか**（未取得なら書類申請で最大1か月。9/30 に間に合わない可能性）
2. 参画事業者は10者（3,000万円）か、5〜9者（2,000万円）か
3. 様式4 を依頼する自治体（熊本県／岩手県／東京都、または別）
4. 対象展示会（第一候補 JAPAN EXPO PARIS 2027・2027-07-08〜11）

---

## 8. 次に最初に行うこと

```
1. §10-1 を実行する（ブランチ取得・日付確認・残日数）
2. 本ファイル §7 の「未回答4点」の回答状況を会話記録で確認する
3. 1（GビズID）が未回答なら、それだけを一つ質問する。回答に応じて：
   - 保有・期限内 → 様式2-1 の作成に入る（企画案 workflow/jizokuka_kyodo_r8_3.md §5 を骨格に）
   - 未保有 → 書類申請の手順を即日案内する（最大1か月。9/30 に対する間に合う／間に合わないを日付で示す）
4. 2〜4 は 1 の決着後に順に伺う
```

---

## 9. 前提条件・数値前提

- 締切 **2026-09-30（水）17:00**（Jグランツ）。残 26日（2026-09-04 16:29 JST 時点）
- GビズID：オンライン申請は不具合中（9月上旬解消予定）、書類申請は最大1か月、有効期限 2年3か月、
  9/12（土）9:00〜14:30 全停止
- 補助上限 3,000万円（10者以上）／2,000万円（5〜9者）。⑩委託・外注費 ≦（①+②+⑦+⑨+⑩）×1/2
- 事務局：株式会社日本経営データ・センター 03-6634-8730／kkr6@kyodokyogyohojokin.info（メール優先）
- 当社：一般社団法人ジャパンプロモーション（東京都渋谷区神宮前6-18-10 海老名ビル4F／代表理事 生島儀尊様）。
  `employees` は未確認のまま（`profile/company-profile.yaml`）
- 環境：`[Code]`／`/home/user/hojo`／ブランチ `claude/kobo-anken-sustainability-subsidies-b9o870`／
  コネクタ Gmail・Google Drive・Google Calendar・GitHub／WebFetch は公的サイトで遮断→curl
- 汎用マニュアルは配布元 https://raw.githubusercontent.com/yixima/manual/main/latest/L0_core_card.md（v41）を
  セッション開始時に curl で取得して適用する（WebFetch は要約器が全文を返さないので使わない）

---

## 10. 使用したコマンド・手順

### 10-1. 新しいセッションの最初に実行する

```bash
cd /home/user/hojo
git fetch origin claude/kobo-anken-sustainability-subsidies-b9o870
git checkout claude/kobo-anken-sustainability-subsidies-b9o870
git pull origin claude/kobo-anken-sustainability-subsidies-b9o870
./bin/today.sh
python3 bin/days_left.py | grep 持続化
curl -sSL https://raw.githubusercontent.com/yixima/manual/main/latest/L0_core_card.md -o /tmp/L0.md && head -3 /tmp/L0.md
```

### 10-2. 引き継ぎの受領照合（Drive 版とリポジトリ版）

```bash
# Drive: mcp__Google_Drive__search_files  query="title = 'kobo_anken_jizokuka_handover_latest.md'"
# Drive: mcp__Google_Drive__download_file_content fileId=<上で得たID>  → base64 を復号して保存
cmp <復号したファイル> docs/handover/kobo_anken_jizokuka_handover_latest.md && echo IDENTICAL
sha256sum docs/handover/kobo_anken_jizokuka_handover_latest.md
```

### 10-3. 一次資料の再取得（事務局が差し替えたか確認するとき）

```bash
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
B=https://r6.kyodokyogyohojokin.info/doc
curl -sSL -A "$UA" --max-time 90 --compressed -o /tmp/k.pdf "$B/r6_koubover6_kk3.pdf"
sha256sum /tmp/k.pdf docs/jizokuka/r6_koubover6_kk3.pdf   # 一致すれば未変更
curl -sSL -A "$UA" --max-time 40 --compressed 'https://gbiz-id.go.jp/top/' | grep -o '9月上旬に解消[^<]*'
```

### 10-4. 台帳を書き換える前に親枝を取り込む

```bash
git fetch origin claude/public-bid-search-workflow-uzj3te
git merge --no-edit origin/claude/public-bid-search-workflow-uzj3te
# 書き換えは分岐元 §10-6 のガード（行数 assert）つきスクリプトで行う
```

### 10-5. PDF を読む

```bash
pip install --quiet cffi pypdf
python3 -c "
from pypdf import PdfReader
r = PdfReader('docs/jizokuka/r6_koubover6_kk3.pdf')
print('\n'.join((p.extract_text() or '') for p in r.pages[7:9]))   # P.8-9 補助上限・申請方法
"
```

### 10-6. コミットとプッシュ

```bash
git add -A
git commit -q -m "<変更内容を日本語で>"
git push -u origin claude/kobo-anken-sustainability-subsidies-b9o870
```

### 10-7. 引き継ぎファイルを Drive へ保存する（固定名・毎回この手順）

1. `./bin/today.sh` で日付を確認し、本文ヘッダの更新日時と版を改める
2. `claude_handover/kobo_anken/`（ID `1K7jXA20Gp2d9addg8oRnvIxcbEQLx7lY`）の中を
   タイトル `kobo_anken_jizokuka_handover_latest.md` で検索し、現行版のIDを得る
3. 同じ名前で新規作成（`create_file` / `contentMimeType: text/markdown` / `disableConversionToGoogleType: true`）
4. 旧版を `trash_file` でゴミ箱へ
5. 削除した版のファイル名・ID・サイズ・作成日時を §6 に1行追記する
6. 履歴版 `kobo_anken_jizokuka_handover_<日付>_v<n>.md` も同フォルダに置く
7. リポジトリの `docs/handover/` にも同じ内容を置き、コミット・プッシュする

---

## 検算

「このファイルだけを読んだ第三者が作業を続けられるか」
— 何の案件か §2-4／なぜこの枝か §2-1／期限 §9／資料 §4-2／次の1行目 §8／未回答 §7／コマンド §10。
**答えは「はい」。ただし §7 の 1（GビズID）は生島様しか答えられない。§8 の 3 で最初に伺う。**
