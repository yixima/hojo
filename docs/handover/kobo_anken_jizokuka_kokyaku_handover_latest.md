# 引き継ぎファイル（kobo_anken_jizokuka_kokyaku_handover_latest）

- **案件名（枝名）**：`kobo_anken_jizokuka_kokyaku` ＝ 小規模事業者持続化補助金について、**当社の顧客向けに申請補助（申請の案内・支援）を行う企画**を立てる作業
  （生島様が 2026-09-04 に `kobo_anken_jizokuka` から改名を指示。訂正名をそのまま使用）
- **このセッションの範囲**：顧客向けの申請補助案内の**企画**。**当社自身の持続化補助金＜共同・協業型＞第3回への申請は別セッションで行う**（生島様 2026-09-04）。本ファイルでは扱わない
- **分岐元**：`kobo_anken_handover_latest.md`（Drive `claude_handover/kobo_anken/`・v3・2026-09-03 15:42 JST）
- **姉妹枝**：`kobo_anken_omatsuri`（おまつり歳時記）。自社申請の枝は本日時点で未作成（別セッションが枝名を決める）
- **保存先（固定）**
  - Google Drive `claude_handover/kobo_anken/kobo_anken_jizokuka_kokyaku_handover_latest.md`（固定名のみ。履歴版はリポジトリ `docs/handover/` に置く＝CLAUDE.md「応答遅延の防止」1）
  - GitHub `yixima/hojo`／ブランチ **`claude/kobo-anken-sustainability-subsidies-b9o870`**／`docs/handover/`
- **作成**：2026-09-04 18:01 JST／**更新 2026-09-07 21:27 Mon JST**／版 **v2**
- **準拠**：汎用マニュアル v41 コアカード §5.5〜§5.6。配布元から curl で取得して適用（リポジトリ内の `docs/manual/` は v17 のまま）
- **環境**：`[Code]`／`/home/user/hojo`

> **更新のしかた**：Drive の `update_file` は本文を差し替えられない。同じ名前で新規作成し、旧版をゴミ箱へ移し、削除した版を §6 に1行追記する。IDは毎回変わるのでタイトルで探す。
> **Drive への保存は1本あたり数分かかる**（実測：18KB のファイルで約9分）。遅くてもエラーではない。

---

## 0. 受領確認ブロック（件数は手で数えた。`tools/make_handover.py` はこのリポジトリに無い）

```handover-manifest
{
  "manifest_version": 1,
  "generated_at": "2026-09-07 21:27 Mon JST",
  "source": "manual",
  "cwd": "/home/user/hojo",
  "branch": "claude/kobo-anken-sustainability-subsidies-b9o870",
  "case": "kobo_anken",
  "lane": "jizokuka_kokyaku",
  "parent": "kobo_anken_handover_latest.md",
  "counts": {
    "依頼の原文": 7,
    "確定した決定": 5,
    "却下した案": 3,
    "作成・追加したファイル": 19,
    "このセッションのコミット": 9,
    "記録された失敗": 1,
    "ゴミ箱へ移したDriveファイル": 3,
    "未完了": 5,
    "生島様への未回答質問": 1（提案Bの採否）
  },
  "chapters": ["1. 依頼の原文","2. 確定した事実と決定","3. 却下した案","4. 発行したすべてのファイル","5. セッション中の調整・変更の経緯","6. 失敗と、そこから得た改善","7. 未完了のタスク","8. 次に最初に行うこと","9. 前提条件・数値前提","10. 使用したコマンド・手順"]
}
```

---

## 1. 依頼の原文（要約せずそのまま）

### 1-1. 1通目（生島様・2026-09-04）
> kobo anken
> の続きです。ここでは持続か補助金についてのセッションを行います。

### 1-2. 枝名の承認（同日）
> kobo_anken_jizokuka
>
> でOKです。

### 1-3. 枝名の訂正と、このセッションの目的（同日・こちらが Drive 保存中に届いた）
> kobo_anken_jizokuka_kokyaku
>
> に変えてください。
> 別セッションで自社の申請をやりますが、こちらでは顧客向けの申請補助案内をする企画についてのセッションをします。

### 1-4. 同時に届いた指摘（同日）
> 反応が遅いですが、何か問題ですか？

### 1-5. 報告書の依頼（生島様・2026-09-04）
> マニュアルセッションにも報告書を渡すので、失敗の経緯や原因、改善策を報告書としてMDで提供してください。

### 1-6. Drive の可視範囲についての質問（生島様・2026-09-04）
> Drive内の、私のPCと同期しているフォルダの中のファイルは全て見れますか？
> パソコン　のなかの　マイiMac
> desu

### 1-7. 本セッションの中心の依頼（生島様・2026-09-07）
> PDFの内容は、前回のどう補助金用に用意したものですが、今回仕様が変わっているので、それに当てはまるか、調整する必要があるのか、どのように調整すれば良いかを検証と提案して欲しいです。

### 1-8. 分岐元にある、持続化補助金についての生島様の原文（分岐元 §3-2）
> これは検討中。なんらかの企画を考えて申請したい。
（2026-08-31。**これは自社申請についての発言。本セッションの対象外**）

---

## 2. 確定した事実と決定（理由つき）

### 2-1. 決定①：枝名 `kobo_anken_jizokuka_kokyaku`
- 生島様の訂正名をそのまま採用（使えない文字なし・語の追加なし）。
- 理由：自社申請（別セッション）と顧客向け企画（本セッション）を同じ枝にすると、後から保存したほうが先を消す（v41 §5.6）。

### 2-2. 決定②：本セッションの対象は「顧客向けの申請補助案内の企画」であり、自社申請ではない
- 生島様 2026-09-04（§1-3）。
- したがって分岐元 §7-2 A の「未回答4点」（GビズID・参画者数・様式4の自治体・展示会）は**自社申請の論点であり、本セッションでは伺わない**。別セッションへ申し送る（§7 の 4）。

### 2-3. 決定③：作業ブランチは `claude/kobo-anken-sustainability-subsidies-b9o870`。親枝 `claude/public-bid-search-workflow-uzj3te`（bb6598f）から分岐
- 理由：台帳・判定基準・企画案が親枝にある。空の枝で始めない（分岐元 §2-17）。

### 2-4. 決定④：顧客向け案内の対象は＜一般型 通常枠＞第20回（資料から確定・2026-09-04）
- Drive「マイ iMac／営業／持続化補助金」の `補助金申請サポートのご案内.pdf`（2026-03-24）が＜一般型 通常枠＞第19回向けの案内だった。生島様 2026-09-07 の依頼（§1-7）で、これを第20回に合わせて検証・調整することが本セッションの中心作業と確定。

### 2-5. 決定⑤：検証は第19回・第20回の公募要領を機械差分して行った（2026-09-07）
- 第19回第6版（42頁）と第20回第8版（44頁）の本文を差分抽出（1,016行）。**「変わった」と書いたものは差分に現れたものだけ**。結果は `docs/jizokuka_kokyaku/kensho_teian_ip20_20260907.md`。
- 主な変更：受付 11-05〜12-15 17:00／様式4 12-04／ウェブ費上限30万／広報費上限30万新設／賃金引上げ特例が給与総額＋3.0%へ／1件50万超で2者見積／実施期間〜2028-03-31／売上増加見込みの記載義務／第三者支援の金額申告。

### 2-6. 一次資料で確認した事実（2026-09-04 16:28〜16:29 JST 取得。顧客向け案内の前提として使う）

| 事実 | ラベル | 出典 |
|---|---|---|
| ＜共同・協業型＞第3回：公募要領 第6版（令和8年8月4日）・47頁。締切 **2026-09-30（水）17:00**・Jグランツ電子申請のみ・GビズIDプライム必須 | 【確認済】 | https://r6.kyodokyogyohojokin.info/doc/r6_koubover6_kk3.pdf |
| 事務局サイト冒頭に「このWebサイトは、**商工会議所**の管轄地域で事業を営んでいる小規模事業者等が対象。**商工会**の管轄地域の方は別リンク」と明記。**顧客の所在地で窓口が分かれる** | 【確認済】 | https://r6.kyodokyogyohojokin.info/ |
| GビズIDのオンライン申請不具合（2026-08-28付）は本日も未解消。**書類申請の審査期間は最大1か月**（2026-07-09告知）。有効期限は発行から2年3か月。9/12（土）9:00〜14:30 全停止 | 【確認済】 | https://gbiz-id.go.jp/top/ |
| 台帳の残日数：26日（2026-09-04 16:29 JST 時点） | 【確認済】 | `bin/days_left.py` |

**未確認（本セッションで最初に確かめること）**
- 持続化補助金には＜一般型＞（小規模事業者が自分で申請する型）と＜共同・協業型＞（地域振興等機関が申請し、参画事業者を支援する型）がある。**「顧客向けの申請補助案内」がどちらを指すかは未確認**（§7 の 1・唯一の質問）。
- ＜一般型＞の現行公募回・締切・様式は**まだ取得していない**。【不明】

---

## 3. 却下した案と理由

| 却下した案 | 理由 |
|---|---|
| 枝名 `kobo_anken_jizokuka`（当初承認） | 生島様が自社申請と顧客向け企画を分けるため改名を指示（§1-3） |
| 枝名 `kobo_anken_jizokuka_r8_3`／`kobo_anken_hojokin` | 初回提案の代替案。生島様が選ばなかった |
| 分岐元 §7-2 A の「未回答4点」を本セッションで伺う | 自社申請の論点。本セッションの対象外と確定（§2-2） |

---

## 4. 発行したすべてのファイル（説明つき）

### 4-1. この引き継ぎ
| ファイル | 置き場所 | 何のために |
|---|---|---|
| `kobo_anken_jizokuka_kokyaku_handover_latest.md` | Drive `claude_handover/kobo_anken/`＋`docs/handover/` | 本ファイル（固定名） |
| `kobo_anken_jizokuka_kokyaku_handover_20260904_v1.md` | 同上 | 履歴版 |

### 4-2. 一次資料（`docs/jizokuka/`・2026-09-04 取得・＜共同・協業型＞第3回。ファイル名は配布元のまま）
| ファイル | 中身 | 頁 |
|---|---|---|
| `r6_koubover6_kk3.pdf` | 公募要領 第6版。**顧客が参画事業者になる場合の要件（従業員数・法人格・資本関係）は P.5〜7** | 47 |
| `r6_qa_kk3.pdf` | 申請時によくあるご質問（第3回） | 5 |
| `r6_jtebiki_kk3.pdf` | Jグランツ操作マニュアル。**顧客向け案内の素材になる** | 23 |
| `r6_kitei_260814.kk.pdf` | 交付規程（令和8年8月14日改定） | 40 |
| `r6_y12_kk3.xlsx`／`r6_y21_kk3.docx`／`r6_y22_kk3.xlsx`／`r6_y330_kk3.xlsx`／`r6_y4_kk3.docx` | 様式1-1/1-2、2-1、2-2、3、4 | — |

### 4-2b. 一般型の一次資料（`docs/jizokuka_ippan/`・2026-09-04〜07 取得）
| ファイル | 中身 | 頁 |
|---|---|---|
| `r6_koubover8_ip20.pdf` | **第20回 公募要領 第8版（2026-07-21）。検証の基準** | 44 |
| `r6_koubover6_ip19.pdf` | 第19回 公募要領 第6版（2026-03-06）。差分の比較元 | 42 |
| `r6_qa_ip19.pdf`／`r6_guidebook_ip19.pdf` | 第19回 FAQ・ガイドブック（第20回版は未公開） | — |

### 4-2c. 顧客向け企画の成果物（`docs/jizokuka_kokyaku/`）
| ファイル | 何のために |
|---|---|
| `drive_hojokin_support_annai_20260324.md` | Drive の案内PDF（3月版）から抽出した本文。原本は `.key` |
| `drive_kaigai_hanbai_package_20260324.md` | 同・販売促進パッケージ |
| **`kensho_teian_ip20_20260907.md`** | **検証と調整提案（§0結論／§1 13項目の突合／§2試算／§3新条項／§4提案A〜D／§6修正後の案内文全文／§7事務局確認事項）。生島様に送付済み** |

### 4-2d. 報告書（`docs/`）
| ファイル | 何のために |
|---|---|
| `report_hannou_chien_20260904.md` | 応答遅延の原因と改善（本セッション用） |
| `report_hannou_chien_manual_20260904.md` | 同・マニュアルセッション宛（条項の追記提案5件）。生島様に送付済み |

### 4-3. 親枝から引き継いだ中核ファイル
`CLAUDE.md`／`bin/today.sh`／`bin/days_left.py`／`data/ledger.csv`（2行目が＜共同・協業型＞）／`workflow/jizokuka_kyodo_r8_3.md`（**自社申請の企画案281行。別セッションの材料**）／`profile/company-profile.yaml`／`workflow/eligibility.md`

---

## 5. セッション中の調整・変更の経緯

| いつ | 何を変えたか | 変える前 |
|---|---|---|
| 2026-09-04 17:40 | 枝名 `kobo_anken_jizokuka` で引き継ぎを初版保存（リポジトリ＋Drive 2本） | 無し |
| 2026-09-04 18:01 | **枝名を `kobo_anken_jizokuka_kokyaku` に改名し、目的を「顧客向けの申請補助案内の企画」に書き換えた。** 旧名の Drive 2本はゴミ箱へ（§6） | 自社申請の作業を前提にしていた。未回答4点を伺う設計だった |
| 2026-09-04 | GビズID書類申請の所要を「最大1か月」に改めた | 分岐元・企画案は「数週間」 |
| 2026-09-04 | 適用するマニュアルを配布元の v41 にした（CLAUDE.md は v17 参照のまま・未修正） | v17 |

---

## 6. 失敗と、そこから得た改善

### 6-1. 反応が遅く、生島様に「何か問題ですか？」と問われた（2026-09-04）
- **何が起きたか**：Drive への引き継ぎ保存（18,792 バイト×2本）に、1本目 約1分、**2本目 約9分**かかった（作成時刻 08:50:30Z と 08:59:33Z）。その間、画面には何も出ていなかった。
- **原因**：Drive コネクタの `create_file` は本文を呼び出しに同梱するため、1本ずつしか送れず、応答も遅い。**エラーではない。**
- **改善**：①保存前に「Drive 保存には数分かかる」と一言出してから始める ②履歴版は節目ごとにまとめて作り、固定名の更新のたびには作らない ③本文を必要最小限に保つ。

### 6-2. 破壊的操作の監査記録（Drive でゴミ箱へ移した版）
- 2026-09-04 削除：`kobo_anken_jizokuka_handover_latest.md`（Drive ID `1w6IYjB_zoR8aymH1eHCAVsZP_3GKfpGP`・18,792 バイト・作成 2026-09-04T08:50:30Z）— 改名のため
- 2026-09-04 削除：`kobo_anken_jizokuka_handover_20260904_v1.md`（Drive ID `1C1d5u_JGaM2Ok9R_u0yH_euJsbFmTDYU`・18,792 バイト・作成 2026-09-04T08:59:33Z）— 改名のため
- 内容は GitHub の履歴（コミット 96912c4）に残っている。
- 2026-09-07 削除：`kobo_anken_jizokuka_kokyaku_handover_latest.md` v1（Drive ID `1cQyKl0M7xD4DN9wh9yqesWaTZxKhIG-8`・15,575 バイト・作成 2026-09-04T09:09:51Z）— v2 への更新のため

---

## 7. 未完了のタスク

| # | タスク | 状態 |
|---|---|---|
| 1 | **唯一の質問：提案B（海外展示会出展をツール制作とセットで1つの補助事業にする）を採るか** | **未回答**（2026-09-07 に質問） |
| 2 | 提案A〜Dの採否に応じて案内文（検証報告 §6）を確定する。Keynote は生島様側で更新（当社は .key を編集できない） | 未着手 |
| 3 | 事務局への確認メール文案（検証報告 §7 の1・2：広報費＋ウェブ費のみの可否／別契約の50万判定） | 未着手 |
| 4 | 顧客候補の洗い出し（Drive「営業／顧客向け資料等」「リスト」） | 未着手 |
| 5 | 別セッション（自社申請）への申し送り：分岐元 §7-2 A の未回答4点＋GビズID書類申請「最大1か月」 | 未着手 |

## 8. 次に最初に行うこと

```
1. §10-1 を実行する
2. §7 の 1（提案B）の回答を会話記録で確認する。未回答ならそれだけを一つ質問する
3. 回答に応じて docs/jizokuka_kokyaku/kensho_teian_ip20_20260907.md §6 の案内文を確定版にする
4. §7 の 3（事務局確認メール文案）を書く。宛先は商工会議所地区事務局（要領 P.1）
```

## 9. 前提条件・数値前提

- ＜一般型 通常枠＞第20回：受付 2026-11-05（木）〜**12-15（火）17:00**／様式4発行締切 12-04（金）／採択発表 2027年3月頃／実施期間 交付決定日〜2028-03-31／実績報告 2028-04-10／見積提出期限 2028-02-29
- 経費上限：広報費30万（税込）・ウェブ費30万（税込）、いずれも単独申請不可。1件50万超は2者見積
- ＜共同・協業型＞第3回の締切 2026-09-30（水）17:00（自社申請・別セッション）
- 事務局（共同・協業型）：株式会社日本経営データ・センター 03-6634-8730／kkr6@kyodokyogyohojokin.info
- 当社：一般社団法人ジャパンプロモーション（渋谷区神宮前6-18-10 海老名ビル4F／代表理事 生島儀尊様）
- **注意（公募要領の対象外条項）**：申請書の作成を他者が代行したと判断された場合は不採択。顧客向けの「申請補助」は**代行ではなく案内・助言**の形に留める必要がある。【確認済・分岐元 `workflow/jizokuka_kyodo_r8_3.md` §7】。＜一般型＞に同種条項があるかは未確認【不明】
- 環境：`[Code]`／`/home/user/hojo`／ブランチ `claude/kobo-anken-sustainability-subsidies-b9o870`／コネクタ Gmail・Drive・Calendar・GitHub／公的サイトは curl

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

### 10-2. 受領照合（Drive 版とリポジトリ版）
```bash
# search_files: title = 'kobo_anken_jizokuka_kokyaku_handover_latest.md' → download_file_content → base64 復号
cmp <復号したファイル> docs/handover/kobo_anken_jizokuka_kokyaku_handover_latest.md && echo IDENTICAL
```

### 10-3. 一次資料の再取得
```bash
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
curl -sSL -A "$UA" --max-time 90 --compressed -o /tmp/k.pdf https://r6.kyodokyogyohojokin.info/doc/r6_koubover6_kk3.pdf
sha256sum /tmp/k.pdf docs/jizokuka/r6_koubover6_kk3.pdf   # 一致すれば未変更
```

### 10-4. PDF を読む
```bash
pip install --quiet cffi pypdf
python3 -c "
from pypdf import PdfReader
r = PdfReader('docs/jizokuka/r6_koubover6_kk3.pdf')
print('\n'.join((p.extract_text() or '') for p in r.pages[4:7]))   # P.5-7 参画事業者の要件
"
```

### 10-5. コミット・プッシュ／Drive 保存
```bash
git add -A && git commit -q -m "<日本語で>" && git push -u origin claude/kobo-anken-sustainability-subsidies-b9o870
```
Drive：`./bin/today.sh` → フォルダ `1K7jXA20Gp2d9addg8oRnvIxcbEQLx7lY` 内をタイトルで検索 → 同名で `create_file`（`text/markdown`・変換無効・**textContent**）→ `download_file_content` で取り戻し復号 → リポジトリ版と `cmp` → 旧版を `trash_file` → §6-2 に1行追記。固定名1本だけ。**数分かかる。始める前に一言出す。**

---

## 検算
何の案件か §2-2／なぜこの枝か §2-1／資料 §4／次の1行目 §8／未回答 §7／コマンド §10。**答えは「はい」。ただし §7 の 1 は生島様しか答えられない。**
