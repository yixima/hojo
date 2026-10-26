# -*- coding: utf-8 -*-
"""**掃引でS/Aと判定したのに、台帳へ入れていない見出しを全部出す。**

    python3 bin/sa_backlog.py              # チャネル別の件数と、上位の見出し
    python3 bin/sa_backlog.py --channel expo2027
    python3 bin/sa_backlog.py --since 2026-10-01

■ なぜ要るのか（2026-10-26 に判明した穴）

日次の巡回は「**本日はじめて見た見出し**」だけを判定して報告する。
ところが台帳へ入れるかどうかは人の判断で、入れなかったものは
**翌日からは「はじめて見た見出し」ではなくなり、二度と報告に出てこない。**

実測：園芸博協会（当方の最重点チャネル）の見出しのうち、
**S/Aと判定されながら台帳に無いものが13件**たまっていた。その中に
「国際出展タイプ１ 展示施工及び運営業務委託」（展示施工と運営＝当社の中核）、
「賓客接遇業務委託」、「屋内出展施設におけるパーテーション設置業務」があった。
いずれも観測はしている。**見えていたのに、拾わなかった。**

**1日だけを見る検出器は、見送った日の分を翌日から見えなくする。**
この道具は、その溜まりを毎回ぜんぶ出す。件数が減らなければ、仕事が進んでいない。
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import os
import re
import sys
import unicodedata
from collections import Counter

# **終わった告知を未処理と同じ山に積むと、件数が意味を失う。**
# 「入札結果」「決定」「契約結果」は台帳行にはならない。**捨てずに別勘定で出す。**
RESULT = re.compile(r'入札結果|落札者|落札結果|契約結果|結果公表|結果について|'
                    r'選定結果|決定|中止|取り消し|取消|参考資料|'
                    # 「質問への回答」「質問に対する回答」「…に係る質問について」。**書き方が揺れる**
                    r'質問[^、。]{0,8}回答|質問について')

# **過年度の案件は取りこぼしではない。「来年ここに出る」という予測の素である。**
# 2026-10-27 実測：和歌山県の17件のうち大半が 2020〜2025 年度の終わった公告だった。
# 同じ山に積むと件数が嘘になり、**本当に拾い損ねた今年の案件が埋もれる。**
# ここに分けたものは `workflow/calendar.yaml` へ移して watch_from で先回りする。
PAST = re.compile(r'令和[1-7]年度|平成|20(1[0-9]|2[0-5])(年度?|\b)')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'bin'))
with contextlib.redirect_stdout(io.StringIO()):
    import rank  # noqa: E402  （読み込むだけで分母の集計を標準出力へ出すため黙らせる）

LOG = os.path.join(ROOT, 'data', 'sweep_log.csv')
LEDGER = os.path.join(ROOT, 'data', 'ledger.csv')
CH = os.path.join(ROOT, 'data', 'channels.csv')


def norm(s: str) -> str:
    """突き合わせ用。記号と空白を落とす。**ここを雑にすると同じ案件を二重に数える。**

    **全角と半角を先に揃える（2026-10-27 に判明した取りこぼし）。**
    チャンスナビの見出しは「令和８年度」（全角8）で、台帳は「令和8年度」（半角8）だった。
    同じ案件なのに前方18文字が一致せず、**台帳に入れた案件が「未処理」の山に残り続けた。**
    記号だけ落として数字の幅を揃えないと、溜まりの件数が嘘になる。

    **大文字・小文字も揃える（同日に判明）。**和歌山県の見出しは
    「海外見本市(ambiente 2027 JAPAN STYLE)」で、台帳は「（Ambiente 2027 JAPAN STYLE）」だった。
    **同じ案件が、Aとaの1文字で未処理の山に残っていた。**
    """
    s = unicodedata.normalize('NFKC', s or '').casefold()
    return re.sub(r'[\s　・,，、。．\.\-−ー―~〜/／()（）【】「」\[\]]', '', s)


def ledger_names() -> list[str]:
    with io.open(LEDGER, encoding='utf-8-sig') as f:
        return [norm(r['案件名']) for r in csv.DictReader(f)]


def channel_names() -> dict[str, str]:
    out = {}
    with io.open(CH, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            out[r['チャネルID']] = r['名称']
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--channel')
    ap.add_argument('--since', help='この日付以降に初観測したものだけ（YYYY-MM-DD）')
    ap.add_argument('--limit', type=int, default=40)
    ap.add_argument('--done', action='store_true',
                    help='終わった告知のほうを出す（過去の発注者と相場を読む）')
    ap.add_argument('--past', action='store_true',
                    help='過年度の公告のほうを出す（calendar.yaml へ移す候補）')
    args = ap.parse_args()

    led = ledger_names()
    chname = channel_names()

    first: dict[str, tuple[str, str, str]] = {}
    with io.open(LOG, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            k = (r.get('見出し') or '').strip()
            if not k:
                continue
            t = (r.get('観測日時') or '')[:16]
            if k not in first or t < first[k][0]:
                first[k] = (t, r.get('リンク') or '', r.get('チャネルID') or '')

    rows: list = []
    done: list = []   # 結果公表・質問回答。別勘定
    past: list = []   # 過年度。calendar.yaml 行き
    for k, (t, link, ch) in first.items():
        n = rank.clean(k)
        if not rank.CONTRACT.search(n):
            continue
        if rank.NOISE.search(n) and not rank.NOISE_UNEI.search(n):
            continue
        g, why = rank.grade(n)
        if g not in ('S', 'A'):
            continue
        # **台帳との突き合わせは前方18文字の包含で見る。**
        # 件名は「【入札結果】」「【更新】」等が前後に付くため完全一致では拾えない。
        kk = norm(n)
        if any(kk[:18] and kk[:18] in x for x in led) or any(x[:18] and x[:18] in kk for x in led):
            continue
        if args.channel and ch != args.channel:
            continue
        if args.since and t[:10] < args.since:
            continue
        bucket = done if RESULT.search(k) else (past if PAST.search(k) else rows)
        bucket.append((g, t, ch, k, link, why))

    if args.done:
        rows = done
    elif args.past:
        rows = past
    rows.sort(key=lambda r: (r[0] != 'S', r[1]), reverse=False)
    print('**S/Aと判定したのに台帳に無い見出し %d件**' % len(rows))
    print('（この数が減らないかぎり、見えていたのに拾っていないものが残っている）')
    print('ほかに**終わった告知**（入札結果・決定・質問回答）が %d件。'
          '台帳行にはならないが、**過去の発注者と相場を読むために残す**'
          '（--done で出す）' % len(done))
    print('ほかに**過年度の公告**が %d件。取りこぼしではない。'
          '**`workflow/calendar.yaml` へ移して watch_from で先回りする素である**'
          '（--past で出す）\n' % len(past))
    c = Counter(r[2] for r in rows)
    for ch, n in c.most_common(15):
        print('  %4d件  %-16s %s' % (n, ch, chname.get(ch, '')[:40]))
    print()
    for g, t, ch, k, link, why in rows[:args.limit]:
        print('  [%s] 初観測 %s  %s' % (g, t, k[:84]))
        print('        %s / %s' % (why[:28], (link or '（リンクなし）')[:88]))
    if len(rows) > args.limit:
        print('  …ほか %d件（--limit で増やす）' % (len(rows) - args.limit))
    print('\n**台帳は書き換えていない。**一次資料を開き、締切種別と締切確認日を埋めてから入れること。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
