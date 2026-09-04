# 引き継ぎファイル（kobo_anken_jizokuka_kokyaku_handover_latest）

- **案件名（枝名）**：`kobo_anken_jizokuka_kokyaku` ＝ 小規模事業者持続化補助金について、**当社の顧客向けに申請補助（申請の案内・支援）を行う企画**を立てる作業
  （生島様が 2026-09-04 に `kobo_anken_jizokuka` から改名を指示。訂正名をそのまま使用）
- **このセッションの範囲**：顧客向けの申請補助案内の**企画**。**当社自身の持続化補助金＜共同・協業型＞第3回への申請は別セッションで行う**（生島様 2026-09-04）。本ファイルでは扱わない
- **分岐元**：`kobo_anken_handover_latest.md`（Drive `claude_handover/kobo_anken/`・v3・2026-09-03 15:42 JST）
- **姉妹枝**：`kobo_anken_omatsuri`（おまつり歳時記）。自社申請の枝は本日時点で未作成（別セッションが枝名を決める）
- **保存先（固定）**
  - Google Drive `claude_handover/kobo_anken/kobo_anken_jizokuka_kokyaku_handover_latest.md`（固定名）＋履歴 `..._20260904_v1.md`
  - GitHub `yixima/hojo`／ブランチ **`claude/kobo-anken-sustainability-subsidies-b9o870`**／`docs/handover/`
- **作成**：2026-09-04（金）18:08 JST（`./bin/today.sh` 実測）／版 **v1（改名後の初版）**
- **準拠**：汎用マニュアル v41 コアカード §5.5〜§5.6。配布元から curl で取得して適用（リポジトリ内の `docs/manual/` は v17 のまま）
- **環境**：`[Code]`／`/home/user/hojo`

> **更新のしかた**：Drive の `update_file` は本文を差し替えられない。同じ名前で新規作成し、旧版をゴミ箱へ移し、削除した版を §6 に1行追記する。IDは毎回変わるのでタイトルで探す。
> **Drive への保存は1本あたり数分かかる**（実測：18KB のファイルで約9分）。遅くてもエラーではない。

---

## 0. 受領確認ブロック（件数は手で数えた。`tools/make_handover.py` はこのリポジトリに無い）

```handover-manifest
{
  "manifest_version": 1,
  "generated_at": "2026-09-04 18:08 JST",
  "source": "manual",
  "cwd": "/home/user/hojo",
  "branch": "claude/kobo-anken-sustainability-subsidies-b9o870",
  "case": "kobo_anken",
  "lane": "jizokuka_kokyaku",
  "parent": "kobo_anken_handover_latest.md",
  "counts": {
    "依頼の原文": 4,
    "確定した決定": 3,
    "却下した案": 3,
    "作成・追加したファイル": 11,
    "このセッションのコミット": 2,
    "記録された失敗": 1,
    "ゴミ箱へ移したDriveファイル": 2,
    "未完了": 4,
    "生島様への未回答質問": 1
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

### 1-5. 分岐元にある、持続化補助金についての生島様の原文（分岐元 §3-2）
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

### 2-4. 一次資料で確認した事実（2026-09-04 16:28〜16:29 JST 取得。顧客向け案内の前提として使う）

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

**＜一般型＞の資料は未取得。**

### 4-3. 親枝から引き継いだ中核ファイル
`CLAUDE.md`／`bin/today.sh`／`bin/days_left.py`／`data/ledger.csv`（2行目が＜共同・協業型＞）／`workflow/jizokuka_kyodo_r8_3.md`（**自社申請の企画案281行。別セッションの材料**）／`profile/company-profile.yaml`／`workflow/eligibility.md`

---

## 5. セッション中の調整・変更の経緯

| いつ | 何を変えたか | 変える前 |
|---|---|---|
| 2026-09-04 17:40 | 枝名 `kobo_anken_jizokuka` で引き継ぎを初版保存（リポジトリ＋Drive 2本） | 無し |
| 2026-09-04 18:08 | **枝名を `kobo_anken_jizokuka_kokyaku` に改名し、目的を「顧客向けの申請補助案内の企画」に書き換えた。** 旧名の Drive 2本はゴミ箱へ（§6） | 自社申請の作業を前提にしていた。未回答4点を伺う設計だった |
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

---

## 7. 未完了のタスク

| # | タスク | 状態 |
|---|---|---|
| 1 | **唯一の質問：顧客向けの申請補助案内は、＜一般型＞（顧客自身が申請）と＜共同・協業型＞（当社が申請し顧客が参画事業者）のどちらを想定するか** | **未回答** |
| 2 | 1 の回答に応じて一次資料を取得（＜一般型＞なら現行公募回の要領・締切・様式。商工会議所地区／商工会地区の2窓口） | 未着手 |
| 3 | 顧客向け申請補助案内の企画書（対象顧客・提供内容・当社の役割・報酬または無償・対象外条項との整合）を作る | 未着手 |
| 4 | **別セッション（自社申請）への申し送り**：分岐元 §7-2 A の未回答4点（GビズID・参画者数・様式4の自治体・展示会）と、GビズID書類申請「最大1か月」の新事実 | 未着手（自社申請の枝名が決まったら、その引き継ぎに転記） |

---

## 8. 次に最初に行うこと

```
1. §10-1 を実行する
2. §7 の 1 が未回答なら、それだけを一つ質問する
3. 回答が＜一般型＞ → 商工会議所地区の公式サイトから現行公募要領を curl で取得し docs/jizokuka_ippan/ に置く
   回答が＜共同・協業型＞ → docs/jizokuka/r6_koubover6_kk3.pdf P.5〜7（参画事業者の要件）を読み、顧客向けの要件チェック表を作る
4. 企画書の骨子を workflow/jizokuka_kokyaku_plan.md に書く
```

---

## 9. 前提条件・数値前提

- ＜共同・協業型＞第3回の締切 2026-09-30（水）17:00。残 26日（2026-09-04 16:29 JST 時点）
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
Drive：`./bin/today.sh` → フォルダ `1K7jXA20Gp2d9addg8oRnvIxcbEQLx7lY` 内をタイトルで検索 → 同名で `create_file`（`text/markdown`・変換無効・base64）→ 旧版を `trash_file` → §6-2 に1行追記。**1本あたり数分かかる。**

---

## 検算
何の案件か §2-2／なぜこの枝か §2-1／資料 §4／次の1行目 §8／未回答 §7／コマンド §10。**答えは「はい」。ただし §7 の 1 は生島様しか答えられない。**
