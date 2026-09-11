# 引き継ぎファイル（kobo_anken_jizokuka_kokyaku_handover_latest）

- **案件名（枝名）**：`kobo_anken_jizokuka_kokyaku` ＝ 小規模事業者持続化補助金について、当社の顧客向けに申請補助（案内・支援）を行う企画
- **範囲**：顧客向け案内の企画のみ。自社の＜共同・協業型＞申請は別セッション（生島様 2026-09-04）
- **分岐元**：`kobo_anken_handover_latest.md`（Drive `claude_handover/kobo_anken/`・v3・2026-09-03）／姉妹枝 `kobo_anken_omatsuri`
- **保存先**：Drive `claude_handover/kobo_anken/kobo_anken_jizokuka_kokyaku_handover_latest.md`（固定名1本のみ）／GitHub `yixima/hojo` ブランチ `claude/kobo-anken-sustainability-subsidies-b9o870` の `docs/handover/`（履歴版もここ）
- **更新**：2026-09-11 19:52 Fri JST／版 **v3**（v1 2026-09-04 18:01、v2 2026-09-07 21:27）
- **準拠**：汎用マニュアル **v59**（2026-09-11 発行。配布元から curl で取得。⑨に ⑨-1・⑨-2 を追加）／環境 `[Code]` `/home/user/hojo`
- **現在の状態：生島様の指示で待機中**（2026-09-11 15:5x「先ほどの問題はこのセッションではありませんでした。一旦待機してください」）

> 更新のしかた：Drive は同名で新規作成→旧版をゴミ箱→§6 に記録。1本数分かかる。始める前に一言出す。

## 0. 受領確認（件数は手で数えた）
```handover-manifest
{"manifest_version":1,"generated_at":"2026-09-11 19:52 Fri JST","source":"manual","cwd":"/home/user/hojo","branch":"claude/kobo-anken-sustainability-subsidies-b9o870","case":"kobo_anken","lane":"jizokuka_kokyaku","parent":"kobo_anken_handover_latest.md",
 "counts":{"依頼の原文":9,"確定した決定":6,"却下した案":3,"主な成果物":6,"このセッションのコミット":16,"記録された失敗":2,"ゴミ箱へ移したDriveファイル":4,"未完了":6,"生島様への未回答質問":1},
 "chapters":["1. 依頼の原文","2. 確定した事実と決定","3. 却下した案","4. 発行したすべてのファイル","5. 調整・変更の経緯","6. 失敗と改善","7. 未完了","8. 次に最初に行うこと","9. 前提条件（⑨-1 してはいけないこと／⑨-2 起点となる日付）","10. コマンド"]}
```

## 1. 依頼の原文（そのまま）
1. 2026-09-04「kobo anken の続きです。ここでは持続か補助金についてのセッションを行います。」
2. 同「kobo_anken_jizokuka でOKです。」→ 同「kobo_anken_jizokuka_kokyaku に変えてください。別セッションで自社の申請をやりますが、こちらでは顧客向けの申請補助案内をする企画についてのセッションをします。」
3. 同「反応が遅いですが、何か問題ですか？」「反応が遅い。改善してください。なぜこんなに時間がかかったのか、あらゆる専門的見地から最新の叡智を集結して検証し、報告書の提出と改善を行なってください」「マニュアルセッションにも報告書を渡すので、失敗の経緯や原因、改善策を報告書としてMDで提供してください。」
4. 同「Drive内の、私のPCと同期しているフォルダの中のファイルは全て見れますか？」「パソコン　のなかの　マイiMac desu」
5. 2026-09-07「PDFの内容は、前回のどう補助金用に用意したものですが、今回仕様が変わっているので、それに当てはまるか、調整する必要があるのか、どのように調整すれば良いかを検証と提案して欲しいです。」「MDを右側のウインドウにも表示できる状態で提出してください。」「右がｗなおウインドウに表示されません。」
6. 2026-09-11「今が何日か把握してますか？ 定期巡回と報告が何日も止まっていました。すぐにやってください。更新版のボードも表示 …原因と、検証の上に導き出した完璧なる改善方法を、簡潔に要点にまとめてチャット欄に報告してください。また、マニュアルセクションへの完璧なる報告書も提出してください。」
7. 2026-09-11「先ほどの問題はこのセッションではありませんでした。一旦待機してください。」

## 2. 確定した事実と決定（理由つき）
1. **枝名 `kobo_anken_jizokuka_kokyaku`**（生島様の訂正名をそのまま）。自社申請と分けないと後の保存が先の枝を消すため。
2. **対象は＜一般型 通常枠＞第20回**。Drive「マイ iMac／営業／持続化補助金」の `補助金申請サポートのご案内.pdf`（2026-03-24・第19回向け）を第20回に合わせて検証・調整する（依頼5）。
3. **検証は第19回第6版と第20回第8版の公募要領を機械差分（1,016行）で行い、変更点だけを「変わった」と書いた**。結果 `docs/jizokuka_kokyaku/kensho_teian_ip20_20260907.md`（Artifact https://claude.ai/code/artifact/cb874ccb-1291-4bf7-8351-b9d8b1cae5c8 ）。要修正5点＝締切日程／ウェブ費上限30万／広報費上限30万新設／賃金引上げ特例が給与総額＋3.0%／「毎年2回募集」。提案A（カタログとストアを別契約・各50万以下）B（海外出展をセットで1事業に）C（2027年の時間軸）D（第三者支援を様式2に申告）。
4. **応答遅延の原因と改善**（依頼3）：Drive 保存1本1〜9分＋同文書の多重生成が主因。改善6項目を `CLAUDE.md` に固定。報告 `docs/report_hannou_chien_20260904.md`／マニュアル宛 `docs/report_hannou_chien_manual_20260904.md`（Artifact https://claude.ai/code/artifact/0b6941cf-a28d-451b-812d-40676bc70ad1 ）。
5. **2026-09-11 の巡回停止（依頼6）は本セッションの担当ではないと生島様が訂正（依頼7）。** ただし訂正前に実施した手動巡回の成果はコミット済み（§4）。調査で判明した事実：週次 Routine（`trig_01NgT5dQwMBGg8APfz8YSG9K`・日曜23:00 UTC）は 9/7 に実行済みで次回 9/14。毎朝のボード更新は Routine ではなく前セッションの send_later 連鎖で、9/9 を最後に自然終了。週次 Routine の実行セッションはリポジトリ・Gmail・Drive が未添付（`session_request.config.sources`／`mcp_connections` が空）で、【公募レポート】メールは 8/28 が最後。公式文書：Routine の緑表示は「基盤エラー無し」の意味で、作業の成功を意味しない（https://code.claude.com/docs/en/routines ）。
6. **待機中**。再開の可否と担当セッションの指定を待つ。

## 3. 却下した案
| 案 | 理由 |
|---|---|
| 枝名 `kobo_anken_jizokuka`（当初承認） | 生島様が自社申請と分けるため改名 |
| 分岐元の未回答4点（GビズID等）を本セッションで伺う | 自社申請の論点。対象外 |
| 巡回停止の原因報告書・Routine 修正をこのセッションで続行 | 生島様「このセッションではない」「待機」（依頼7） |

## 4. 発行したすべてのファイル（主なもの）
| ファイル | 何のために |
|---|---|
| `docs/jizokuka_kokyaku/kensho_teian_ip20_20260907.md` | **主成果物。**3月版案内×第20回要領の検証と提案、§6 に修正後の案内文全文、§7 に事務局確認事項 |
| `docs/jizokuka_kokyaku/drive_hojokin_support_annai_20260324.md`／`drive_kaigai_hanbai_package_20260324.md` | Drive の案内PDF 2本の抽出本文（原本は .key） |
| `docs/jizokuka_ippan/r6_koubover8_ip20.pdf`（第20回要領第8版・44頁）／`r6_koubover6_ip19.pdf`／`r6_qa_ip19.pdf`／`r6_guidebook_ip19.pdf` | 一次資料 |
| `docs/jizokuka/`（＜共同・協業型＞第3回の要領・様式・FAQ・手引き・交付規程） | 別セッション（自社申請）の材料 |
| `docs/report_hannou_chien_20260904.md`／`docs/report_hannou_chien_manual_20260904.md` | 応答遅延の報告（本セッション用／マニュアル宛） |
| `tools/md2artifact.py`／`reports/artifacts/*.html` | MD 報告書を右ペイン表示用 HTML に変換する道具（2026-09-07） |
| `bin/heartbeat_check.py` | ボード・台帳の停止時間を機械判定（2026-09-11。巡回停止調査の副産物） |
| `reports/kobo_report_20260911.md` | 9/11 手動巡回のレポート。**未送信** |
| `data/ledger.csv`（277行）／`reports/dashboard.html`（09.11 15:42 版） | 東京都の受付中5件を追記、締切超過63件更新。**公開版 Artifact は 9/8 版のまま（再公開は拒否され未了）** |

## 5. 調整・変更の経緯
| いつ | 変えたこと | 変える前 |
|---|---|---|
| 09-04 18:01 | 枝名を `_kokyaku` に改名、目的を顧客向け企画に | 自社申請前提 |
| 09-04 18:12 | `CLAUDE.md` に「応答遅延の防止」6項目 | 無し |
| 09-07 | 検証報告 v1 完成・送付。Artifact 2本公開 | — |
| 09-11 | 親枝（`public-bid-search-workflow-uzj3te` 63dd0fe）を取り込み、手動巡回を実施 | 親枝は 9/4 時点 |
| 09-11 19:50 | マニュアルを v41→**v59** に切替（管理セッションの通知）。⑨に ⑨-1・⑨-2 を追加 | v41 |

## 6. 失敗と改善
- **6-1（09-04）応答が約25分無言**：Drive 保存の遅さ＋多重生成。改善は CLAUDE.md「応答遅延の防止」。
- **6-2（09-11）担当外の作業に着手**：巡回停止の依頼をこのセッション宛と受け取り、手動巡回・調査を進めた。生島様の訂正で停止。**再発防止：複数枝が並走しているとき、依頼がどの枝宛かを最初の1行で確認してから重い作業に入る**（v59 §5.6「引き継ぎが受け口に無くても発動」の趣旨）。成果は無駄にはならないが、他枝の作業と衝突しうる（台帳・ボードは親枝と共有）。
- **Drive ゴミ箱の記録**：09-04 `kobo_anken_jizokuka_handover_latest.md`（`1w6IYjB_zoR8aymH1eHCAVsZP_3GKfpGP`・18,792B）／同 `_20260904_v1.md`（`1C1d5u_JGaM2Ok9R_u0yH_euJsbFmTDYU`・18,792B）／09-07 `_kokyaku_handover_latest.md` v1（`1cQyKl0M7xD4DN9wh9yqesWaTZxKhIG-8`・15,575B）／**09-11 同 v2（`1k9fSPbKaYYMOB_US9xQHJh9zYXEdHyKM`・19,101B・作成 2026-09-07T12:30:12Z）— v3 への更新のため**

## 7. 未完了
| # | タスク | 状態 |
|---|---|---|
| 1 | **唯一の質問：提案B（海外展示会出展をツール制作とセットで1事業に）を採るか** | 未回答（09-07 に質問） |
| 2 | 案内文（検証報告 §6）の確定。Keynote は生島様側で更新 | 未着手 |
| 3 | 事務局確認メール文案（広報費＋ウェブ費のみの可否／別契約の50万判定） | 未着手 |
| 4 | 顧客候補の洗い出し（Drive「営業／顧客向け資料等」「リスト」） | 未着手 |
| 5 | 別セッション（自社申請）への申し送り：分岐元 §7-2 A の4点＋GビズID書類申請「最大1か月」 | 未着手 |
| 6 | **他枝へ渡すもの**：公開版ボードの再公開（拒否のまま）／`reports/kobo_report_20260911.md` の送信／巡回停止の原因報告書と Routine 修正（§2-5 の事実を材料に） | 生島様の指定待ち |

## 8. 次に最初に行うこと
```
1. §10-1 を実行する
2. 生島様の「再開してよい／どの枝が巡回停止を扱うか」の指示を確認する。無ければ待機のまま、§7 の 1 だけを一つ質問する
3. 再開なら §7 の 1 の回答に応じて検証報告 §6 の案内文を確定版にする
```

## 9. 前提条件
### ⑨-1 してはいけないこと（根拠条項つき・＜一般型 通常枠＞第20回 公募要領 第8版）
- **申請書を事業者に代わって作成しない／「事業者自らが検討した記載」が無い計画にしない**（P.1 注意事項：自ら検討していない場合は評価に関わらず不採択・交付決定取消）
- **第三者支援（行政書士）を受けたことと報酬額を様式2に書かずに申請しない**（P.1：相手方および着手金・成功報酬など名目を問わない金額の記載が無いと虚偽報告として不採択・取消）
- **GビズIDプライムのID・パスワードを支援者に開示しない**（P.1：利用規約第11条違反）
- **ウェブサイト関連費のみ・広報費のみで申請しない／各区分の補助金申請額を30万円（税込）超にしない**（7. ③・②）
- **出展料等の請求書発行日・支払日を交付決定日より前にしない**（7. ④。申込みは可）
- **1件50万円（税込）超の発注を2者見積なしで行わない**（8. 見積）
- **国の助成を受ける出展を対象経費にしない／補助事業期間（〜2028-03-31）外の展示会を計上しない**（7. ④）
- 顧客向け案内で「毎年2回募集」「1/4・最大50万」など第19回の数値をそのまま使わない（第20回で変更。検証報告 §1）
### ⑨-2 起点となる日付（根拠：第20回 公募要領 第8版 P.3・P.22・P.24）
| 日付 | 内容 |
|---|---|
| 2026-11-05（木） | 申請受付開始 |
| 2026-12-04（金） | 事業支援計画書（様式4）発行の受付締切（商工会議所・商工会。締切後はいかなる理由でも発行不可） |
| **2026-12-15（火）17:00** | 申請受付締切（要領 P.12 は「木」と誤記。2026-12-15 は火曜） |
| 2027年3月頃 | 採択発表。交付決定はその1〜2か月後 |
| 2028-02-29 | 見積書等の提出期限（未提出は採択取消） |
| **2028-03-31（金）** | 補助事業実施期限（実績報告 2028-04-10） |
### その他
- 当社：一般社団法人ジャパンプロモーション（渋谷区神宮前6-18-10 海老名ビル4F／代表理事 生島儀尊様）。案内の3月版は行政書士法人GOAL との提携（着手金5万＋採択額15%）
- 環境：`[Code]`／`/home/user/hojo`／コネクタ Gmail・Drive・Calendar・GitHub／公的サイトは curl／マニュアルは配布元 v59 を curl で取得

## 10. コマンド
```bash
cd /home/user/hojo && git fetch origin claude/kobo-anken-sustainability-subsidies-b9o870 && git checkout claude/kobo-anken-sustainability-subsidies-b9o870 && git pull origin claude/kobo-anken-sustainability-subsidies-b9o870
./bin/today.sh; python3 bin/days_left.py | grep 持続化; python3 bin/heartbeat_check.py
curl -sSL "https://raw.githubusercontent.com/yixima/manual/main/latest/L0_core_card.md?t=$(date -u +%s)" -o /tmp/L0.md && head -3 /tmp/L0.md
# Drive 受領照合: search_files title='kobo_anken_jizokuka_kokyaku_handover_latest.md' → download → 復号 → cmp docs/handover/kobo_anken_jizokuka_kokyaku_handover_latest.md
# 一次資料再取得: curl -sSL -A 'Mozilla/5.0' -o /tmp/k.pdf https://r6.jizokukahojokin.info/doc/r6_koubover8_ip20.pdf; sha256sum /tmp/k.pdf docs/jizokuka_ippan/r6_koubover8_ip20.pdf
# コミット: git add -A && git commit -q -m "<日本語>" && git push -u origin claude/kobo-anken-sustainability-subsidies-b9o870
```
検算：何の案件か §2-2／なぜ §2-1／禁止と日付 §9／次 §8／未回答 §7／コマンド §10 → **はい。**
