# -*- coding: utf-8 -*-
"""公開済みの公募ボード（HTML）と `data/ledger.csv` を突き合わせ、**台帳に無い案件を報告する**。

なぜ要るか
----------
**週次巡回の Routine は別セッションで動き、リポジトリへの push が拒否されることがある。**
2026-09-07、巡回は新規4件を見つけて Artifact を公開したが push できず、
台帳268行／公開版272行で食い違った。**Artifact の公開は成功しているので、
公開版のHTMLから案件名を回収すれば、取りこぼしを検出できる。**

このスクリプトは**報告するだけで、台帳を書き換えない。**
`bin/audit_gates.py` と同じ方針である。回収は一次資料を読んで手で行う。

使い方
------
    # Artifact の publish が拒否されたとき、保存された全文のパスが示される
    python3 bin/recover_from_board.py <保存されたボードHTML>
"""
import csv
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def names_in_board(path):
    """カードの見出しと一覧表の案件名を集める。"""
    h = Path(path).read_text(encoding='utf-8', errors='replace')
    out = set()
    for m in re.finditer(r'<div class="ctitle"><h3>(.*?)</h3>', h, re.S):
        out.add(html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip())
    # 一覧表は「日付セル → 案件名セル」の並び。日付セルには span が入ることがある
    for m in re.finditer(
            r'<td class="d">[^<]*(?:<span[^>]*>[^<]*</span>)?</td>\s*<td>(.*?)</td>', h, re.S):
        out.add(html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip())
    return {x for x in out if x}


def norm(s):
    """比較用に正規化する。**空白と & の表記ゆれで取りこぼさないため。**"""
    return re.sub(r'\s|&amp;|＆|&', '', s)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    board = names_in_board(sys.argv[1])
    rows = list(csv.DictReader(open(ROOT / 'data' / 'ledger.csv', encoding='utf-8')))
    led = {norm(r['案件名'].strip()) for r in rows}
    missing = sorted(n for n in board if norm(n) not in led)
    extra = len(rows) - len(board)

    print('公開版の案件名 %d件 / 台帳 %d行' % (len(board), len(rows)))
    if missing:
        print('\n**台帳に無いもの %d件。一次資料を読んで手で追記すること。**' % len(missing))
        for n in missing:
            print('  -', n)
        print('\n追記のときは `締切種別` と `締切確認日` を必ず埋める。')
        print('**一次資料を自分で見ていない行は、その旨を状態欄に明記する。**')
    else:
        print('\n台帳に無いものはない。')
    print('\n（台帳にあって公開版に出ていない行が %d件ある。'
          '対象外29件などは画面に出さない設計なので、これは異常ではない）' % extra)
    sys.exit(1 if missing else 0)


if __name__ == '__main__':
    main()
