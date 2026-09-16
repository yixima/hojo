# workflow/ について（2026-09-16）

**このディレクトリの巡回スクリプトは、`bin/` に置き換わった。**

枝 `znmhfx` が 8/19〜9/15 に作ったものだが、同じ期間に `uzj3te` 側が `bin/` 配下へ
より良いものを作っており、そちらが正である。経緯と対応表は
`docs/handover_znmhfx/README.md` を見ること。

例外は1つ。**`workflow/awards_pportal.py` は `bin/` に該当物が無い。**
調達ポータルの落札実績オープンデータ（国の調達・約11.6万行）から過年度の
落札金額を引く。[5]金額の第1手段として使う。

`ARCHITECTURE.md` `case-list-schema.md` `check_recall.py` `check_links.py`
`fetch_chancenavi.py` も `bin/` に該当物が無いため有効。
